from anpr_pipeline.detect import Detection
from anpr_pipeline.track import IouTracker, iou


def test_iou_overlap():
    assert iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0
    assert iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0
    assert 0.0 < iou((0, 0, 10, 10), (5, 5, 15, 15)) < 1.0


def test_tracker_maintains_identity():
    tracker = IouTracker()
    first = tracker.update([Detection(100, 100, 200, 200, 0.9, "car")], timestamp=0.0)
    assert len(first) == 1
    track_id = first[0].track_id

    # Same vehicle moved slightly: identity must be preserved.
    second = tracker.update([Detection(110, 105, 210, 205, 0.9, "car")], timestamp=0.1)
    assert len(second) == 1
    assert second[0].track_id == track_id
    assert len(second[0].history) == 2


def test_tracker_creates_new_track_for_distant_detection():
    tracker = IouTracker()
    tracker.update([Detection(0, 0, 50, 50, 0.9, "car")], timestamp=0.0)
    tracks = tracker.update(
        [Detection(0, 0, 50, 50, 0.9, "car"), Detection(400, 400, 500, 500, 0.8, "truck")],
        timestamp=0.1,
    )
    assert len(tracks) == 2
    assert len({t.track_id for t in tracks}) == 2


def test_tracker_expires_missed_tracks():
    tracker = IouTracker(max_misses=2)
    tracker.update([Detection(0, 0, 50, 50, 0.9, "car")], timestamp=0.0)
    for i in range(4):
        tracker.update([], timestamp=0.1 * (i + 1))
    assert tracker.tracks == []
