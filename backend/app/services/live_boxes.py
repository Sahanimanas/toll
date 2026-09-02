"""In-memory store of the pipeline's latest detection boxes per camera.

Purely ephemeral live-view garnish: the pipeline POSTs its current vehicle
and plate boxes every processed frame, the MJPEG restream draws whatever is
fresh. Nothing is persisted — recognitions (the durable record) flow through
the normal ingest path.
"""

import threading
import time

# Boxes older than this are considered gone from view.
LIVE_BOX_TTL_SECONDS = 3.0

_lock = threading.Lock()
_boxes: dict[int, tuple[float, list[dict]]] = {}


def set_boxes(camera_id: int, boxes: list[dict]) -> None:
    with _lock:
        _boxes[camera_id] = (time.monotonic(), boxes)


def get_boxes(camera_id: int) -> list[dict]:
    with _lock:
        entry = _boxes.get(camera_id)
    if entry is None or time.monotonic() - entry[0] > LIVE_BOX_TTL_SECONDS:
        return []
    return entry[1]
