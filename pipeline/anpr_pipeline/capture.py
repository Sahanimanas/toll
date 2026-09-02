"""RTSP/device frame capture with automatic reconnection.

Uses TCP transport for RTSP to avoid UDP packet loss artifacts that destroy
OCR quality. Network streams are kept at the live edge by a grabber thread:
it consumes frames (without decoding) as fast as the camera sends them, so a
slow consumer always decodes the newest frame instead of falling minutes
behind the buffered stream. File and device sources read sequentially.
"""

import logging
import os
import threading
import time

import cv2

logger = logging.getLogger(__name__)


class VideoSource:
    def __init__(self, source: str, reconnect_delay: float = 3.0):
        self.source: str | int = int(source) if str(source).isdigit() else source
        self.reconnect_delay = reconnect_delay
        # Live-edge semantics only make sense for endless network streams;
        # files are paced against a wall clock instead (see _read_file_realtime).
        self.is_live_stream = isinstance(self.source, str) and self.source.startswith(
            ("rtsp", "http")
        )
        self._cap: cv2.VideoCapture | None = None
        self._lock = threading.Lock()
        self._frame_ready = threading.Event()
        self._grabber: threading.Thread | None = None
        self._stop_grabber = False
        # File playback schedule: the video's own frame rate, and the monotonic
        # time the next frame is due.
        self.native_fps = 0.0
        self._next_frame_at = 0.0

    def _open(self) -> bool:
        if isinstance(self.source, str) and self.source.startswith("rtsp"):
            os.environ.setdefault(
                "OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp"
            )
        self._cap = cv2.VideoCapture(self.source)
        # Keep the internal buffer tiny so we read near-live frames.
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        ok = self._cap.isOpened()
        if ok:
            if not self.is_live_stream:
                # Restart the playback clock (also covers looping at EOF).
                # Not every capture backend reports FPS (some lack .get at
                # all), so fall back rather than fail to open the source.
                try:
                    self.native_fps = float(self._cap.get(cv2.CAP_PROP_FPS)) or 0.0
                except Exception:
                    self.native_fps = 0.0
                if not (0 < self.native_fps <= 240):
                    self.native_fps = 25.0  # unreadable/bogus metadata
                self._next_frame_at = 0.0
                logger.info("source %s native fps: %.2f", self.source, self.native_fps)
            logger.info("opened video source %s", self.source)
            if self.is_live_stream:
                self._stop_grabber = False
                self._frame_ready.clear()
                self._grabber = threading.Thread(
                    target=self._grab_loop, name="grabber", daemon=True
                )
                self._grabber.start()
        else:
            logger.warning("failed to open video source %s", self.source)
        return ok

    def _grab_loop(self) -> None:
        """Consume frames without decoding, pinning the capture to 'now'."""
        while not self._stop_grabber:
            cap = self._cap
            if cap is None:
                return
            with self._lock:
                ok = cap.grab()
            if not ok:
                self._frame_ready.clear()
                return  # read() notices the stall and reconnects
            self._frame_ready.set()

    def _read_file_realtime(self):
        """Return the frame that is due *now* at the file's native rate.

        Files play sequentially, so if we simply read as fast as the consumer
        allows, a slow consumer (detection is ~100ms/frame) drags playback into
        slow motion — an hour of footage would take a day. Instead we keep a
        wall-clock schedule: sleep when early, and when late skip ahead by
        grabbing frames without decoding them (nearly free). Playback stays
        real-time; a slow consumer loses frames, never time — the same
        guarantee the grabber thread gives network streams.
        """
        period = 1.0 / self.native_fps
        now = time.monotonic()
        if self._next_frame_at == 0.0:
            self._next_frame_at = now

        behind = now - self._next_frame_at
        if behind >= period:
            # Cap the catch-up burst so a long stall can't spin here.
            skip = min(int(behind / period), 300)
            for _ in range(skip):
                if not self._cap.grab():
                    return None
                self._next_frame_at += period
        elif behind < 0:
            time.sleep(-behind)

        ok, frame = self._cap.read()
        self._next_frame_at += period
        return frame if ok else None

    def read(self):
        """Return the next frame, reconnecting forever until one is available.

        For live streams this is the NEWEST frame the camera has produced, not
        the next buffered one — a consumer slower than the camera stays
        real-time instead of drifting minutes behind. For files the equivalent
        is a wall-clock schedule (see _read_file_realtime), so the video always
        plays at its own frame rate.
        """
        while True:
            if self._cap is None or not self._cap.isOpened():
                if not self._open():
                    time.sleep(self.reconnect_delay)
                    continue
            if self.is_live_stream:
                if not self._frame_ready.wait(timeout=10.0):
                    logger.warning("stream %s stalled, reconnecting", self.source)
                    self.release()
                    time.sleep(self.reconnect_delay)
                    continue
                with self._lock:
                    ok, frame = self._cap.retrieve()
            else:
                frame = self._read_file_realtime()
                ok = frame is not None
            if ok and frame is not None:
                return frame
            logger.warning("stream %s dropped, reconnecting", self.source)
            self.release()
            time.sleep(self.reconnect_delay)

    def release(self) -> None:
        self._stop_grabber = True
        grabber = self._grabber
        if grabber is not None and grabber is not threading.current_thread():
            grabber.join(timeout=2.0)
        self._grabber = None
        if self._cap is not None:
            with self._lock:
                self._cap.release()
            self._cap = None
