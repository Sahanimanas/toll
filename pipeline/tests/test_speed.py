from anpr_pipeline.track import Track


def _track_with_history(history):
    track = Track(track_id="t1", bbox=(0, 0, 10, 10), label="car", confidence=0.9)
    track.history = history
    return track


def test_speed_basic():
    from anpr_pipeline.speed import estimate_speed_kmh

    # 100 px over 1 s at 0.1 m/px = 10 m/s = 36 km/h
    track = _track_with_history([(0.0, 0.0, 0.0), (1.0, 100.0, 0.0)])
    assert estimate_speed_kmh(track, meters_per_pixel=0.1) == 36.0


def test_speed_requires_calibration():
    from anpr_pipeline.speed import estimate_speed_kmh

    track = _track_with_history([(0.0, 0.0, 0.0), (1.0, 100.0, 0.0)])
    assert estimate_speed_kmh(track, meters_per_pixel=None) is None


def test_speed_rejects_short_window():
    from anpr_pipeline.speed import estimate_speed_kmh

    track = _track_with_history([(0.0, 0.0, 0.0), (0.05, 100.0, 0.0)])
    assert estimate_speed_kmh(track, meters_per_pixel=0.1) is None


def test_speed_rejects_implausible():
    from anpr_pipeline.speed import estimate_speed_kmh

    track = _track_with_history([(0.0, 0.0, 0.0), (1.0, 10000.0, 0.0)])
    assert estimate_speed_kmh(track, meters_per_pixel=0.5) is None
