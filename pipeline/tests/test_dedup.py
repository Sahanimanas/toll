from anpr_pipeline.dedup import MemoryDuplicateFilter


def test_first_sighting_is_not_duplicate():
    dedup = MemoryDuplicateFilter(ttl_seconds=30)
    assert dedup.is_duplicate(1, "MH12AB1234", now=100.0) is False


def test_repeat_within_ttl_is_duplicate():
    dedup = MemoryDuplicateFilter(ttl_seconds=30)
    dedup.is_duplicate(1, "MH12AB1234", now=100.0)
    assert dedup.is_duplicate(1, "MH12AB1234", now=110.0) is True


def test_repeat_after_ttl_is_new():
    dedup = MemoryDuplicateFilter(ttl_seconds=30)
    dedup.is_duplicate(1, "MH12AB1234", now=100.0)
    assert dedup.is_duplicate(1, "MH12AB1234", now=140.0) is False


def test_scoped_per_camera():
    dedup = MemoryDuplicateFilter(ttl_seconds=30)
    dedup.is_duplicate(1, "MH12AB1234", now=100.0)
    assert dedup.is_duplicate(2, "MH12AB1234", now=101.0) is False
