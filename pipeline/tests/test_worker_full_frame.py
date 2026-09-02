"""Full-frame plate fallback: when no vehicle is detected, the worker should
still find and publish a plate (subject to the same gates)."""

import numpy as np
import pytest

from anpr_pipeline.config import PipelineConfig
from anpr_pipeline.detect import Detection
from anpr_pipeline.track import Track
from anpr_pipeline.worker import CameraWorker

CAMERA = {"id": 1, "name": "test-cam", "rtsp_url": "test://none", "config": {}}


class NoVehicles:
    def detect(self, frame):
        return []


class FixedPlate:
    def detect(self, frame):
        return Detection(10, 20, 200, 80, 0.8, "plate")


class NoPlate:
    def detect(self, frame):
        return None


class FakeOcr:
    def __init__(self, text="MH12AB1234", conf=0.9):
        self.text, self.conf = text, conf

    def read(self, plate):
        return self.text, self.conf


class FakeDedup:
    def __init__(self, duplicate=False):
        self.duplicate = duplicate

    def is_duplicate(self, camera_id, plate_text):
        return self.duplicate


class CapturingPublisher:
    def __init__(self):
        self.published = []
        self.live_boxes = []
        self.live_frames = []

    def publish(self, payload, frame=None, plate=None):
        self.published.append(payload)

    def push_live_boxes(self, camera_id, boxes):
        self.live_boxes.append((camera_id, boxes))

    def push_live_frame(self, camera_id, jpeg_bytes):
        self.live_frames.append((camera_id, jpeg_bytes))


def make_worker(plate_detector, ocr, dedup=None, **config_overrides):
    config = PipelineConfig()
    for key, value in config_overrides.items():
        setattr(config, key, value)
    publisher = CapturingPublisher()
    worker = CameraWorker(
        CAMERA, config, NoVehicles(), plate_detector, ocr, dedup or FakeDedup(), publisher
    )
    return worker, publisher


FRAME = np.full((360, 640, 3), 128, dtype=np.uint8)


def test_full_frame_plate_published_when_no_vehicle():
    worker, publisher = make_worker(FixedPlate(), FakeOcr())
    worker.process_frame(FRAME, 0.0)
    assert len(publisher.published) == 1
    payload = publisher.published[0]
    assert payload["plate_text"] == "MH12AB1234"
    assert payload["vehicle_type"] == "unknown"
    assert payload["bbox"]["plate"] == {"x1": 10, "y1": 20, "x2": 200, "y2": 80}


def test_full_frame_fallback_disabled_by_config():
    worker, publisher = make_worker(FixedPlate(), FakeOcr(), full_frame_plates=False)
    worker.process_frame(FRAME, 0.0)
    assert publisher.published == []


def test_full_frame_respects_confidence_gate():
    worker, publisher = make_worker(FixedPlate(), FakeOcr(conf=0.3))
    worker.process_frame(FRAME, 0.0)
    assert publisher.published == []


def test_full_frame_rejects_invalid_plate_text():
    worker, publisher = make_worker(FixedPlate(), FakeOcr(text="KERALA"))
    worker.process_frame(FRAME, 0.0)
    assert publisher.published == []


def test_full_frame_deduplicated():
    worker, publisher = make_worker(FixedPlate(), FakeOcr(), dedup=FakeDedup(duplicate=True))
    worker.process_frame(FRAME, 0.0)
    assert publisher.published == []


def test_full_frame_no_plate_found_is_quiet():
    worker, publisher = make_worker(NoPlate(), FakeOcr())
    worker.process_frame(FRAME, 0.0)
    assert publisher.published == []


def test_process_fps_defaults_to_config_cap():
    worker, _ = make_worker(NoPlate(), FakeOcr())  # config default 15 fps
    assert worker._process_interval == pytest.approx(1.0 / 15.0)


def test_process_fps_per_camera_override():
    camera = {**CAMERA, "config": {"process_fps": 5}}
    config = PipelineConfig()
    worker = CameraWorker(
        camera, config, NoVehicles(), NoPlate(), FakeOcr(), FakeDedup(), CapturingPublisher()
    )
    assert worker._process_interval == pytest.approx(1.0 / 5.0)


def test_process_fps_garbage_falls_back_to_default():
    camera = {**CAMERA, "config": {"process_fps": "fast"}}
    config = PipelineConfig()
    worker = CameraWorker(
        camera, config, NoVehicles(), NoPlate(), FakeOcr(), FakeDedup(), CapturingPublisher()
    )
    assert worker._process_interval == pytest.approx(1.0 / config.max_process_fps)


def test_live_boxes_pushed_for_plate_detection():
    worker, publisher = make_worker(FixedPlate(), FakeOcr())
    worker.process_frame(FRAME, 0.0)
    assert len(publisher.live_boxes) == 1
    camera_id, boxes = publisher.live_boxes[0]
    assert camera_id == CAMERA["id"]
    # A grammar-valid read labels the live plate box with its text.
    assert {
        "x1": 10, "y1": 20, "x2": 200, "y2": 80, "kind": "plate",
        "label": "MH12AB1234",
    } in boxes
    # Detection publishes boxes for the read loop to draw; it does not ship
    # frames itself (that would pin the live view to the detector's fps).
    assert publisher.live_frames == []
    assert worker._overlay_boxes == boxes


def test_stream_frame_ships_annotated_frame_with_latest_boxes():
    """The read loop streams every frame, independently of detection."""
    worker, publisher = make_worker(FixedPlate(), FakeOcr())
    worker.process_frame(FRAME, 0.0)          # detector produces boxes
    publisher.live_frames.clear()

    worker._stream_frame(FRAME)               # read loop ships a frame
    assert len(publisher.live_frames) == 1
    camera_id, jpeg = publisher.live_frames[0]
    assert camera_id == CAMERA["id"]
    assert jpeg[:2] == b"\xff\xd8"            # JPEG magic

    # Frames keep flowing even before/without any detection.
    fresh, fresh_pub = make_worker(NoPlate(), FakeOcr())
    fresh._stream_frame(FRAME)
    assert len(fresh_pub.live_frames) == 1


def test_new_track_is_eligible_for_recognition_immediately():
    """A never-attempted track must not wait out the retry interval."""
    worker, _ = make_worker(FixedPlate(), FakeOcr())
    track = Track(track_id="t1", bbox=(0, 0, 300, 200), label="car", confidence=0.9)
    assert worker._recognition_candidates([track], 0.0) == [track]
    # ...and is then throttled until the retry interval elapses.
    assert worker._recognition_candidates([track], 0.0) == []
    assert worker._recognition_candidates(
        [track], worker.config.plate_retry_seconds
    ) == [track]


def test_recognition_attempts_capped_per_frame_largest_first():
    """Reading every unpublished track each frame is what makes a busy scene
    crawl; only the biggest few (nearest, most readable) run per frame."""
    worker, _ = make_worker(FixedPlate(), FakeOcr())
    small = Track(track_id="s", bbox=(0, 0, 50, 50), label="car", confidence=0.9)
    big = Track(track_id="b", bbox=(0, 0, 400, 300), label="car", confidence=0.9)
    mid = Track(track_id="m", bbox=(0, 0, 200, 150), label="car", confidence=0.9)
    worker.config.max_plate_attempts_per_frame = 2
    chosen = worker._recognition_candidates([small, big, mid], 0.0)
    assert chosen == [big, mid]


def test_published_track_is_not_retried():
    worker, _ = make_worker(FixedPlate(), FakeOcr())
    track = Track(track_id="t1", bbox=(0, 0, 300, 200), label="car", confidence=0.9)
    track.plate_published = True
    assert worker._recognition_candidates([track], 100.0) == []


def test_no_live_boxes_pushed_when_nothing_detected():
    worker, publisher = make_worker(NoPlate(), FakeOcr())
    worker.process_frame(FRAME, 0.0)
    assert publisher.live_boxes == []


def test_consensus_publishes_repeated_medium_confidence_read():
    # 0.5 is under the 0.60 gate but over the 0.45 consensus floor: the
    # first read is held back, the second identical read publishes.
    worker, publisher = make_worker(FixedPlate(), FakeOcr(conf=0.5))
    worker.process_frame(FRAME, 0.0)
    assert publisher.published == []
    worker.process_frame(FRAME, 1.0)
    assert len(publisher.published) == 1
    assert publisher.published[0]["plate_text"] == "MH12AB1234"


def test_consensus_requires_identical_text():
    worker, publisher = make_worker(FixedPlate(), FakeOcr(conf=0.5))
    worker.process_frame(FRAME, 0.0)
    worker.ocr = FakeOcr(text="KA19P8488", conf=0.5)  # different read
    worker.process_frame(FRAME, 1.0)
    assert publisher.published == []


class TopStripPlate:
    def detect(self, frame):
        # Centered at y=12 in a 360px frame: inside the 8% OSD mask strip.
        return Detection(400, 2, 620, 22, 0.9, "plate")


def test_osd_top_strip_detections_ignored():
    worker, publisher = make_worker(TopStripPlate(), FakeOcr())
    worker.process_frame(FRAME, 0.0)
    assert publisher.published == []
    assert publisher.live_boxes == []


def test_junk_confidence_never_reaches_consensus():
    worker, publisher = make_worker(FixedPlate(), FakeOcr(conf=0.3))
    for i in range(5):
        worker.process_frame(FRAME, float(i))
    assert publisher.published == []
