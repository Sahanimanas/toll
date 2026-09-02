"""Draw detection boxes onto a frame and encode it for the live view.

The pipeline annotates the exact frame it ran detection on and ships that
finished JPEG to the backend. Because the box is baked into the frame it was
detected on, the live view never shows a box on the wrong frame and the
backend needs no second camera connection to draw overlays itself.
"""

import cv2
import numpy as np

_VEHICLE_COLOR = (80, 200, 120)  # BGR green
_PLATE_COLOR = (0, 215, 255)  # BGR amber


def annotate_frame(frame: np.ndarray, boxes: list[dict]) -> np.ndarray:
    """Return a copy of `frame` with vehicle/plate boxes and labels drawn.

    `boxes` entries carry x1..y2, a "kind" of "vehicle" or "plate", and an
    optional "label" (plate text or vehicle type)."""
    annotated = frame.copy()
    scale = max(frame.shape[1] / 1280.0, 0.6)
    thickness = max(int(scale * 2), 1)
    for box in boxes:
        try:
            x1, y1, x2, y2 = int(box["x1"]), int(box["y1"]), int(box["x2"]), int(box["y2"])
        except (KeyError, TypeError, ValueError):
            continue
        is_plate = box.get("kind") == "plate"
        color = _PLATE_COLOR if is_plate else _VEHICLE_COLOR
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 3 if is_plate else 2)
        label = box.get("label") or ""
        if label:
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
            ty = max(y1 - 8, th + 4)
            cv2.rectangle(
                annotated, (x1 - 2, ty - th - 4), (x1 + tw + 2, ty + 4), (0, 0, 0), cv2.FILLED
            )
            cv2.putText(
                annotated, label, (x1, ty), cv2.FONT_HERSHEY_SIMPLEX, scale, color,
                thickness, cv2.LINE_AA,
            )
    return annotated


def encode_stream_jpeg(
    frame: np.ndarray, max_width: int = 960, quality: int = 75
) -> bytes | None:
    """Downscale (if wider than max_width) and JPEG-encode a frame for the
    live view. Returns None if encoding fails."""
    height, width = frame.shape[:2]
    if width > max_width:
        new_h = max(int(height * (max_width / width)), 1)
        frame = cv2.resize(frame, (max_width, new_h), interpolation=cv2.INTER_AREA)
    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return buffer.tobytes() if ok else None
