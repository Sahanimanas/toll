"""VideoSource live-edge behavior: network streams must decode the newest
frame (grab-drain), file sources must read sequentially."""

import time

import numpy as np
import pytest

from anpr_pipeline import capture


class FakeCapture:
    """Mimics cv2.VideoCapture: grab() advances, retrieve() decodes latest."""

    def __init__(self, source):
        self.source = source
        self.position = -1
        self.frames = 100
        self.grab_delay = 0.001

    def isOpened(self):
        return True

    def set(self, *_):
        return True

    def grab(self):
        time.sleep(self.grab_delay)
        if self.position + 1 >= self.frames:
            return False
        self.position += 1
        return True

    def retrieve(self):
        return True, np.full((4, 4, 3), self.position % 256, dtype=np.uint8)

    def read(self):
        if not self.grab():
            return False, None
        return self.retrieve()

    def release(self):
        pass


@pytest.fixture(autouse=True)
def fake_cv2(monkeypatch):
    monkeypatch.setattr(capture.cv2, "VideoCapture", FakeCapture)


def test_live_stream_reads_newest_frame():
    src = capture.VideoSource("rtsp://example/stream")
    assert src.is_live_stream
    first = src.read()
    time.sleep(0.05)  # grabber advances ~dozens of frames meanwhile
    second = src.read()
    src.release()
    # The second read must have skipped ahead, not returned frame #2.
    assert int(second[0, 0, 0]) - int(first[0, 0, 0]) > 5


def test_file_source_reads_sequentially():
    src = capture.VideoSource("clip.avi")
    assert not src.is_live_stream
    a = src.read()
    b = src.read()
    src.release()
    assert int(b[0, 0, 0]) - int(a[0, 0, 0]) == 1
