"""Lightweight IOU tracker.

Associates detections across frames by intersection-over-union. Sufficient for
per-vehicle deduplication and speed estimation on a single camera; swappable
for ByteTrack/SORT later behind the same interface.
"""

import itertools
import uuid
from dataclasses import dataclass, field


def iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    return inter / float(area_a + area_b - inter)


@dataclass
class Track:
    track_id: str
    bbox: tuple[int, int, int, int]
    label: str
    confidence: float
    # (timestamp, center_x, center_y) history for speed estimation.
    history: list[tuple[float, float, float]] = field(default_factory=list)
    misses: int = 0
    plate_published: bool = False
    best_plate: tuple[str, float] | None = None
    # Monotonic time of the last plate-read attempt, so a track that never
    # yields a valid plate is retried periodically rather than every frame.
    # -inf, not 0: a brand-new track has never been attempted and must be
    # eligible immediately, whatever the clock reads.
    last_attempt_at: float = float("-inf")
    # Last plate box as fractions of the vehicle bbox (x1, y1, x2, y2). Stored
    # relative so it stays glued to the vehicle as it moves: once a track has
    # published we stop re-detecting its plate, but the live view must keep
    # showing which plate was read on which vehicle.
    plate_rel: tuple[float, float, float, float] | None = None

    @property
    def center(self) -> tuple[float, float]:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


class IouTracker:
    def __init__(self, iou_threshold: float = 0.3, max_misses: int = 10):
        self.iou_threshold = iou_threshold
        self.max_misses = max_misses
        self.tracks: list[Track] = []

    def update(self, detections, timestamp: float) -> list[Track]:
        """Match detections to tracks greedily by IOU; returns live tracks."""
        unmatched = list(detections)
        for track in self.tracks:
            best, best_iou = None, self.iou_threshold
            for det in unmatched:
                score = iou(track.bbox, det.bbox)
                if score > best_iou:
                    best, best_iou = det, score
            if best is not None:
                unmatched.remove(best)
                track.bbox = best.bbox
                track.label = best.label
                track.confidence = best.confidence
                track.misses = 0
                cx, cy = track.center
                track.history.append((timestamp, cx, cy))
            else:
                track.misses += 1

        for det in unmatched:
            track = Track(
                track_id=uuid.uuid4().hex[:12],
                bbox=det.bbox,
                label=det.label,
                confidence=det.confidence,
            )
            cx, cy = track.center
            track.history.append((timestamp, cx, cy))
            self.tracks.append(track)

        self.tracks = [t for t in self.tracks if t.misses <= self.max_misses]
        return [t for t in self.tracks if t.misses == 0]
