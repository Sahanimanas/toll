"""ANPR-facing compat endpoints: SSE live stream, FASTag lookup, recent
transactions/camera-logs, and a legacy /api/anpr/detect ingest bridge.

These mirror the original Node routes (unauthenticated reads + SSE, shared-key
ingest) so the frontend and any legacy worker keep working unchanged. The
primary ingest path is now the ANPR platform's /api/v1/ingest/recognitions,
which feeds toll transactions via app.toll.service.on_recognition.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import models as core_models
from app.db.session import get_db
from app.toll import models
from app.toll.service import deduct_toll, find_fastag, format_plate, push_notif
from app.toll.sse import broadcast, event_stream

router = APIRouter(tags=["toll-anpr"])


@router.get("/api/anpr/stream")
def anpr_stream():
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive",
                 "X-Accel-Buffering": "no"},
    )


@router.get("/api/fastag/{plate}")
def fastag_lookup(plate: str, db: Session = Depends(get_db)):
    f = find_fastag(db, plate)
    if f is None:
        raise HTTPException(404, "no fastag")
    return {"tag": f.tag_id, "plate": f.plate, "bank": f.bank,
            "balance": f.balance, "status": f.status}


@router.get("/api/anpr/transactions")
def anpr_transactions(limit: int = 50, db: Session = Depends(get_db)):
    limit = min(max(limit, 1), 500)
    rows = db.scalars(
        select(models.TollTransaction).order_by(models.TollTransaction.ts.desc()).limit(limit)
    ).all()
    items = [{"id": t.id, "date": t.date, "time": t.time, "lane": t.lane,
              "reg": t.reg, "cls": t.cls, "tag": t.tag, "speed": t.speed,
              "amount": t.amount, "mode": t.mode, "status": t.status,
              "plate_image": t.plate_image, "confidence": t.confidence} for t in rows]
    return {"total": len(items), "items": items}


@router.get("/api/anpr/camera-logs")
def anpr_camera_logs(db: Session = Depends(get_db)):
    rows = db.scalars(
        select(core_models.Recognition).order_by(core_models.Recognition.id.desc()).limit(200)
    ).all()
    items = [{"id": r.id, "camera_id": r.camera_id, "event": "detect",
              "detail": r.plate_text, "ts": r.captured_at.isoformat() if r.captured_at else ""}
             for r in rows]
    return {"total": len(items), "items": items}


def _worker_auth(x_ingest_key: str | None, x_api_key: str | None):
    key = get_settings().ingest_api_key
    if (x_ingest_key or x_api_key) != key:
        raise HTTPException(401, "bad ingest key")


@router.post("/api/anpr/detect")
async def anpr_detect(
    db: Session = Depends(get_db),
    plate: str = Form(...),
    cls: str = Form("Car / Jeep"),
    lane: str = Form("Lane 1"),
    camera_id: str | None = Form(None),
    speed: str | None = Form(None),
    confidence: str | None = Form(None),
    plate_image: UploadFile | None = File(None),
    x_ingest_key: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
):
    """Legacy shared-key ingest bridge (old worker.py contract)."""
    _worker_auth(x_ingest_key, x_api_key)
    conf = float(confidence) if confidence else None
    spd = int(float(speed)) if speed else 0

    broadcast("detect", {"plate": format_plate(plate), "lane": lane,
                         "camera_id": int(camera_id) if camera_id else None,
                         "ts": int(datetime.now(timezone.utc).timestamp() * 1000),
                         "confidence": conf})
    txn = deduct_toll(db, plate=plate, cls=cls, lane=lane, speed=spd, confidence=conf)
    broadcast("transaction", txn)
    if spd > 60:
        push_notif(db, "warn", "Speed Threshold Exceeded",
                   f"Vehicle {txn['reg']} on {lane} clocked {spd} km/h (limit 60).")
    return {"ok": True, "txn": txn}
