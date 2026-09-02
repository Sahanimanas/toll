"""In-memory store of the pipeline's latest annotated live-view frame.

The pipeline draws detection boxes onto the exact frame it processed,
downscales and JPEG-encodes it, and POSTs it here. The dashboard reads the
newest frame (snapshot or MJPEG restream) without the backend ever opening a
second connection to the camera or re-drawing overlays on a frame it decoded
itself — which is what made boxes lag behind the video.

Purely ephemeral: nothing is persisted (recognitions are the durable record),
and a frame older than the TTL is treated as "no live frame" so the view falls
back to the direct RTSP restream when the pipeline is not feeding this camera.
"""

import threading
import time

# Frames older than this are considered stale (pipeline stopped/not running).
LIVE_FRAME_TTL_SECONDS = 5.0

_lock = threading.Lock()
_frames: dict[int, tuple[float, bytes]] = {}


def set_frame(camera_id: int, jpeg_bytes: bytes) -> None:
    with _lock:
        _frames[camera_id] = (time.monotonic(), jpeg_bytes)


def get_frame(camera_id: int) -> bytes | None:
    with _lock:
        entry = _frames.get(camera_id)
    if entry is None or time.monotonic() - entry[0] > LIVE_FRAME_TTL_SECONDS:
        return None
    return entry[1]


def has_fresh_frame(camera_id: int) -> bool:
    return get_frame(camera_id) is not None
