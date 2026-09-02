"""Overlay drawing + stream encoding. Skipped where OpenCV isn't installed."""

import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")

from anpr_pipeline.overlay import annotate_frame, encode_stream_jpeg


def _blank(w=1280, h=720):
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_annotate_does_not_mutate_source():
    frame = _blank()
    boxes = [{"x1": 10, "y1": 10, "x2": 200, "y2": 120, "kind": "vehicle", "label": "car"}]
    annotated = annotate_frame(frame, boxes)
    assert annotated is not frame
    assert not np.array_equal(annotated, frame)  # something was drawn
    assert frame.sum() == 0  # original untouched


def test_annotate_tolerates_bad_boxes():
    frame = _blank()
    boxes = [{"x1": 1}, {"kind": "plate"}, {"x1": "a", "y1": 1, "x2": 2, "y2": 3}]
    # Malformed boxes are skipped, not raised on.
    annotate_frame(frame, boxes)


def test_encode_downscales_wide_frames():
    jpeg = encode_stream_jpeg(_blank(3840, 2160), max_width=960, quality=75)
    assert jpeg is not None and jpeg[:2] == b"\xff\xd8"  # JPEG SOI marker
    decoded = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[1] == 960
    assert decoded.shape[0] == 540  # aspect preserved


def test_encode_leaves_small_frames_unscaled():
    jpeg = encode_stream_jpeg(_blank(640, 360), max_width=960)
    decoded = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    assert decoded.shape[1] == 640
