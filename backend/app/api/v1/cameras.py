import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app import schemas
from app.core.security import (
    ROLE_ADMIN,
    ROLE_OPERATOR,
    get_current_user,
    get_current_user_or_query_token,
    require_roles,
)
from app.db import models
from app.db.session import SessionLocal, get_db
from app.services.audit import audit
from app.services.live_boxes import get_boxes
from app.services.live_frames import get_frame, has_fresh_frame
from app.services.stream import (
    BOUNDARY,
    MjpegStream,
    PipelineFrameStream,
    StreamLimitExceeded,
    StreamUnavailable,
    probe_stream,
)

router = APIRouter(prefix="/cameras", tags=["cameras"])

# Recognition boxes stay on the live view this long after capture.
OVERLAY_WINDOW_SECONDS = 6.0
_OVERLAY_REFRESH_SECONDS = 1.0


def _live_fps(camera: models.Camera) -> int | None:
    """Per-camera live-view fps cap from cameras.config['live_fps'], clamped."""
    try:
        raw_fps = (camera.config or {}).get("live_fps")
        if raw_fps:
            return min(max(int(raw_fps), 1), 30)
    except (TypeError, ValueError):
        pass
    return None


def _box(data: dict | None) -> tuple[int, int, int, int] | None:
    if not data:
        return None
    try:
        return (int(data["x1"]), int(data["y1"]), int(data["x2"]), int(data["y2"]))
    except (KeyError, TypeError, ValueError):
        return None


def recent_recognition_overlays(camera_id: int):
    """Overlay provider for MjpegStream, combining two sources:

    - live detection boxes the pipeline pushes every processed frame
      (in-memory, no label unless the pipeline set one) — read every call;
    - recognitions from the last few seconds (with plate text), DB-refreshed
      at most once per second (the stream calls this per frame).
    """
    cache = {"at": 0.0, "overlays": []}

    def provider() -> list[dict]:
        now = time.monotonic()
        if now - cache["at"] >= _OVERLAY_REFRESH_SECONDS:
            cache["at"] = now
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=OVERLAY_WINDOW_SECONDS)
            overlays = []
            with SessionLocal() as db:
                rows = db.scalars(
                    select(models.Recognition)
                    .where(models.Recognition.camera_id == camera_id)
                    .where(models.Recognition.captured_at >= cutoff)
                    .order_by(models.Recognition.captured_at.desc())
                    .limit(5)
                ).all()
            for row in rows:
                bbox = row.bbox or {}
                vehicle, plate = _box(bbox), _box(bbox.get("plate"))
                if vehicle or plate:
                    overlays.append(
                        {"vehicle": vehicle, "plate": plate, "label": row.plate_text}
                    )
            cache["overlays"] = overlays

        live = []
        for item in get_boxes(camera_id):
            box = _box(item)
            if box is None:
                continue
            key = "plate" if item.get("kind") == "plate" else "vehicle"
            live.append({key: box, "label": item.get("label", "")})
        return live + cache["overlays"]

    return provider


@router.get(
    "",
    response_model=schemas.Page[schemas.CameraOut],
    dependencies=[Depends(get_current_user)],
)
def list_cameras(
    page: int = 1,
    page_size: int = 100,
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    page, page_size = max(page, 1), min(max(page_size, 1), 500)
    query = select(models.Camera)
    if active_only:
        query = query.where(models.Camera.is_active.is_(True))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(models.Camera.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return schemas.Page(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/{camera_id}",
    response_model=schemas.CameraOut,
    dependencies=[Depends(get_current_user)],
)
def get_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.get(models.Camera, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    return camera


@router.get(
    "/{camera_id}/stream",
    dependencies=[Depends(get_current_user_or_query_token)],
)
def stream_camera(camera_id: int, db: Session = Depends(get_db)):
    """Live MJPEG restream of the camera feed (renders in an <img> tag).

    Accepts `?token=` auth because image tags cannot send headers. Read-only,
    so no audit entry. 502 = camera unreachable, 503 = viewer slots full.
    """
    camera = db.get(models.Camera, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    fps = _live_fps(camera)
    try:
        if has_fresh_frame(camera_id):
            # Pipeline is feeding pre-annotated frames: serve those (no second
            # camera connection, no 4K decode, boxes already on the right frame).
            stream = PipelineFrameStream(camera_id, fps=fps)
        else:
            # No pipeline frames (dev, or pipeline not covering this camera):
            # fall back to a direct RTSP restream with server-drawn overlays.
            stream = MjpegStream(
                camera.rtsp_url,
                overlay_provider=recent_recognition_overlays(camera_id),
                fps=fps,
            )
    except StreamLimitExceeded:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Too many live viewers")
    except StreamUnavailable:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Camera stream unreachable")
    except ImportError:  # OpenCV missing in this deployment
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED, "Live view requires opencv-python-headless"
        )
    return StreamingResponse(
        stream,
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
        headers={"Cache-Control": "no-store"},
        background=BackgroundTask(stream.close),
    )


@router.get(
    "/{camera_id}/snapshot",
    dependencies=[Depends(get_current_user_or_query_token)],
)
def snapshot_camera(camera_id: int, db: Session = Depends(get_db)):
    """Single latest annotated JPEG frame for the camera.

    Backs the dashboard's canvas live view: each poll returns the newest frame
    (never a buffered/stale one), so the view stays real-time. 503 when the
    pipeline is not currently feeding frames for this camera.
    """
    camera = db.get(models.Camera, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    jpeg = get_frame(camera_id)
    if jpeg is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "No live frame available — pipeline not running for this camera",
        )
    return Response(
        content=jpeg, media_type="image/jpeg", headers={"Cache-Control": "no-store"}
    )


@router.post(
    "/test",
    response_model=schemas.StreamTestResult,
    dependencies=[Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR))],
)
def test_stream(body: schemas.StreamTestRequest):
    """Probe a stream URL (RTSP/HTTP(S)/file/device) without saving anything.

    Read-only connectivity check for the camera form, so no audit entry.
    Always 200 with ok=false on unreachable sources; 501 without OpenCV.
    """
    try:
        return probe_stream(body.stream_url)
    except ImportError:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED, "Stream testing requires opencv-python-headless"
        )


@router.post("", response_model=schemas.CameraOut, status_code=201)
def create_camera(
    body: schemas.CameraCreate,
    db: Session = Depends(get_db),
    actor=Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
):
    if db.scalar(select(models.Camera).where(models.Camera.name == body.name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Camera name already exists")
    camera = models.Camera(**body.model_dump())
    db.add(camera)
    db.commit()
    db.refresh(camera)
    audit(db, actor.id, "camera.create", f"cameras/{camera.id}", {"name": camera.name})
    return camera


@router.patch("/{camera_id}", response_model=schemas.CameraOut)
def update_camera(
    camera_id: int,
    body: schemas.CameraUpdate,
    db: Session = Depends(get_db),
    actor=Depends(require_roles(ROLE_ADMIN, ROLE_OPERATOR)),
):
    camera = db.get(models.Camera, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(camera, key, value)
    db.commit()
    db.refresh(camera)
    audit(db, actor.id, "camera.update", f"cameras/{camera.id}", data)
    return camera


@router.delete("/{camera_id}", status_code=204)
def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    actor=Depends(require_roles(ROLE_ADMIN)),
):
    camera = db.get(models.Camera, camera_id)
    if camera is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    camera.is_active = False
    db.commit()
    audit(db, actor.id, "camera.deactivate", f"cameras/{camera_id}", {})
