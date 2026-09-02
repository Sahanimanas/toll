import json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import schemas
from app.core.config import get_settings
from app.core.security import require_ingest_key
from app.db import models
from app.db.session import get_db
from app.services.alert_engine import evaluate_alerts
from app.services.evidence import save_evidence
from app.services.live_boxes import set_boxes
from app.services.live_frames import set_frame

logger = logging.getLogger(__name__)

# Guardrail: annotated live frames are downscaled JPEGs (~<200 KB); reject
# anything implausibly large so a misconfigured client can't exhaust memory.
_MAX_LIVE_FRAME_BYTES = 3 * 1024 * 1024

router = APIRouter(
    prefix="/ingest", tags=["ingest"], dependencies=[Depends(require_ingest_key)]
)


@router.get("/cameras", response_model=list[schemas.CameraOut])
def list_active_cameras(db: Session = Depends(get_db)):
    """Camera list for pipeline workers (ingest-key auth, not user JWT)."""
    from sqlalchemy import select

    return db.scalars(
        select(models.Camera).where(models.Camera.is_active.is_(True))
    ).all()


@router.post("/detections", status_code=204)
def ingest_live_detections(body: schemas.LiveDetectionsIn):
    """Current-frame detection boxes for the live-view overlay.

    Ephemeral (in-memory, ~3s TTL) — drawn on the MJPEG restream so operators
    see detection activity even when no plate read passes the publish gates.
    """
    set_boxes(body.camera_id, [box.model_dump() for box in body.boxes])


@router.post("/frame", status_code=204)
async def ingest_live_frame(
    camera_id: int = Form(...),
    frame: UploadFile = File(...),
):
    """Latest annotated live-view frame from the pipeline (boxes baked in).

    Ephemeral (in-memory, short TTL). Served to the dashboard by the camera
    snapshot/stream endpoints so the backend never opens its own camera
    connection while the pipeline is running.
    """
    data = await frame.read()
    if not data:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Empty frame")
    if len(data) > _MAX_LIVE_FRAME_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Frame too large")
    set_frame(camera_id, data)


@router.post("/recognitions", response_model=schemas.RecognitionOut, status_code=201)
async def ingest_recognition(
    payload: str = Form(..., description="RecognitionIngest as JSON"),
    frame: UploadFile | None = File(default=None),
    plate: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    try:
        data = schemas.RecognitionIngest.model_validate(json.loads(payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    camera = db.get(models.Camera, data.camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown camera_id")

    evidence_path = ""
    plate_image_path = ""
    plate_bytes: bytes | None = None
    if frame is not None:
        evidence_path = save_evidence(await frame.read(), suffix="frame")
    if plate is not None:
        plate_bytes = await plate.read()
        plate_image_path = save_evidence(plate_bytes, suffix="plate")

    rec = models.Recognition(
        camera_id=data.camera_id,
        plate_text=data.plate_text.upper().strip(),
        plate_confidence=data.plate_confidence,
        ocr_raw=data.ocr_raw,
        vehicle_type=data.vehicle_type,
        vehicle_confidence=data.vehicle_confidence,
        speed_kmh=data.speed_kmh,
        direction=data.direction,
        track_id=data.track_id,
        bbox=data.bbox,
        evidence_path=evidence_path,
        plate_image_path=plate_image_path,
        captured_at=data.captured_at,
    )
    db.add(rec)
    db.flush()

    alerts = evaluate_alerts(db, rec, camera)
    db.commit()
    db.refresh(rec)
    if alerts:
        logger.info(
            "recognition %s (%s) raised %d alert(s)", rec.id, rec.plate_text, len(alerts)
        )

    # Toll bridge: convert this recognition into a toll transaction (rate
    # lookup + FASTag deduction) and push it to the live feed. Best-effort —
    # never breaks recognition ingest.
    if get_settings().toll_enabled:
        from app.toll.service import on_recognition

        on_recognition(db, rec, camera, plate_bytes)

    out = schemas.RecognitionOut.model_validate(rec)
    out.has_evidence = bool(rec.evidence_path)
    return out
