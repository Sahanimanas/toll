"""Compat camera endpoints (/api/cameras) for the toll frontend's Live page.

Projects the ANPR platform's Camera rows into the toll tile shape, and serves
the live ANNOTATED video: the pipeline bakes vehicle/plate boxes + the plate
text onto the exact frame it ran detection on and pushes it here, so the tile
shows real recognitions drawn on the video. When the pipeline isn't feeding a
camera we fall back to decoding the source directly and drawing overlays from
recent recognitions server-side.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask

from app.api.v1.cameras import recent_recognition_overlays
from app.db import models as core_models
from app.db.session import get_db
from app.services.live_frames import get_frame, has_fresh_frame
from app.services.stream import (
    BOUNDARY,
    MjpegStream,
    PipelineFrameStream,
    StreamLimitExceeded,
    StreamUnavailable,
)
from app.toll.api.deps import auth_required
from app.toll.service import format_plate

router = APIRouter(dependencies=[Depends(auth_required)])
# Media endpoints are unauthenticated: an <img> tag cannot send an
# Authorization header. Same trust boundary as the original Node /storage
# and /videos static routes.
media_router = APIRouter(tags=["toll-camera-media"])

_UPTIME = {"pct": 100, "segments": [{"status": "live", "ms": 24 * 60 * 60 * 1000}]}


def _last_read(db: Session, camera_id: int) -> tuple[str, str]:
    """(plate, HH:MM:SS) of the newest recognition on this camera."""
    rec = db.scalar(
        select(core_models.Recognition)
        .where(core_models.Recognition.camera_id == camera_id)
        .order_by(core_models.Recognition.captured_at.desc())
        .limit(1)
    )
    if rec is None:
        return "—", ""
    return format_plate(rec.plate_text), rec.captured_at.strftime("%H:%M:%S")


def _cam_out(c: core_models.Camera, db: Session) -> dict:
    cfg = c.config or {}
    # Prefer the annotated MJPEG restream so detection boxes show on the tile.
    # The .mjpg suffix makes the frontend render it in an <img> (its existing
    # media-type sniffing). Without a live pipeline frame, fall back to the
    # browser-playable source (e.g. the demo mp4) so the tile still shows video.
    if c.rtsp_url and has_fresh_frame(c.id):
        url = f"/api/cameras/{c.id}/live.mjpg"
    elif cfg.get("browser_url"):
        url = cfg["browser_url"]
    elif c.rtsp_url:
        url = f"/api/cameras/{c.id}/live.mjpg"
    else:
        url = ""
    plate, plate_at = _last_read(db, c.id)
    return {
        "id": c.id, "name": c.name, "lane": c.lane or cfg.get("lane") or "—",
        "res": cfg.get("res", "1080P"), "status": "live" if c.is_active else "offline",
        "fps": cfg.get("fps", 25), "plate": plate, "plateAt": plate_at, "url": url,
        "type": cfg.get("type", "ANPR"), "uptime": _UPTIME,
        "annotated": bool(c.rtsp_url and has_fresh_frame(c.id)),
    }


@router.get("/api/cameras")
def list_cameras(db: Session = Depends(get_db)):
    cams = db.scalars(select(core_models.Camera).order_by(core_models.Camera.id)).all()
    return [_cam_out(c, db) for c in cams]


@router.get("/api/cameras/{cid}/uptime")
def camera_uptime(cid: int, db: Session = Depends(get_db)):
    if db.get(core_models.Camera, cid) is None:
        raise HTTPException(404, "not found")
    return _UPTIME


@router.post("/api/cameras")
async def create_camera(request: Request, db: Session = Depends(get_db)):
    b = await request.json()
    name, lane = b.get("name"), b.get("lane")
    if not name or not lane:
        raise HTTPException(400, "name and lane required")
    url = b.get("url") or ""
    is_browser_playable = bool(url) and not url.lower().startswith("rtsp://")
    cam = core_models.Camera(
        name=str(name), lane=str(lane), rtsp_url=url, location=str(lane),
        config={"res": b.get("res", "1080P"), "fps": int(b.get("fps") or 25),
                "type": b.get("type", "ANPR"),
                **({"browser_url": url} if is_browser_playable else {})},
        is_active=True,
    )
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return _cam_out(cam, db)


@router.delete("/api/cameras/{cid}")
def delete_camera(cid: int, db: Session = Depends(get_db)):
    cam = db.get(core_models.Camera, cid)
    if cam is None:
        raise HTTPException(404, "not found")
    db.delete(cam)
    db.commit()
    return {"ok": True}


# ---------- live annotated media (unauthenticated: <img> can't send headers) ----------

def _live_fps(camera: core_models.Camera) -> int | None:
    try:
        raw = (camera.config or {}).get("live_fps")
        if raw:
            return min(max(int(raw), 1), 30)
    except (TypeError, ValueError):
        pass
    return None


@media_router.get("/api/cameras/{cid}/live.mjpg")
def camera_live_mjpg(cid: int, db: Session = Depends(get_db)):
    """MJPEG restream with detection boxes + plate text drawn on the frames.

    Uses the pipeline's pre-annotated frames when it is feeding this camera
    (boxes are baked onto the exact detected frame, so they never lag); else
    decodes the source and draws overlays from the last few recognitions.
    """
    camera = db.get(core_models.Camera, cid)
    if camera is None:
        raise HTTPException(404, "Camera not found")
    fps = _live_fps(camera)
    try:
        if has_fresh_frame(cid):
            stream = PipelineFrameStream(cid, fps=fps)
        else:
            stream = MjpegStream(
                camera.rtsp_url,
                overlay_provider=recent_recognition_overlays(cid),
                fps=fps,
            )
    except StreamLimitExceeded:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Too many live viewers")
    except StreamUnavailable:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Camera stream unreachable")
    except ImportError:
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED, "Live view requires opencv-python-headless"
        )
    return StreamingResponse(
        stream,
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
        headers={"Cache-Control": "no-store"},
        background=BackgroundTask(stream.close),
    )


@media_router.get("/api/cameras/{cid}/snapshot.jpg")
def camera_snapshot(cid: int, db: Session = Depends(get_db)):
    """Newest annotated JPEG for this camera (503 when the pipeline isn't feeding)."""
    if db.get(core_models.Camera, cid) is None:
        raise HTTPException(404, "Camera not found")
    jpeg = get_frame(cid)
    if jpeg is None:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "No live frame — pipeline not running for this camera",
        )
    return Response(content=jpeg, media_type="image/jpeg",
                    headers={"Cache-Control": "no-store"})
