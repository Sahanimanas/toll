"""Live MJPEG restream of camera feeds for the dashboard.

Each viewer gets its own RTSP connection decoded and re-encoded as
multipart JPEG, which renders in a plain <img> tag. This is an operator
convenience view for a handful of concurrent watchers, not a video
distribution system — a hard viewer cap protects the backend, frames are
downscaled/throttled, and stale frames are dropped so the view stays live.
"""

import logging
import os
import threading
import time

from app.core.config import get_settings

logger = logging.getLogger(__name__)

BOUNDARY = "frame"
_JPEG_QUALITY = 80
# Consecutive read failures before we declare the stream dead.
_MAX_READ_FAILURES = 25


class StreamUnavailable(Exception):
    """The camera source could not be opened."""


class StreamLimitExceeded(Exception):
    """All viewer slots are in use."""


_slots_lock = threading.Lock()
_active_viewers = 0


def _acquire_slot(max_viewers: int) -> None:
    global _active_viewers
    with _slots_lock:
        if _active_viewers >= max_viewers:
            raise StreamLimitExceeded(f"{max_viewers} concurrent viewers reached")
        _active_viewers += 1


def _release_slot() -> None:
    global _active_viewers
    with _slots_lock:
        _active_viewers = max(0, _active_viewers - 1)


def _open_capture(source_url: str):
    import cv2  # deferred: optional heavy dependency

    if source_url.startswith("rtsp"):
        # TCP avoids UDP artifacts; stimeout bounds the connect attempt (µs).
        os.environ.setdefault(
            "OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp|stimeout;5000000"
        )
    source: str | int = int(source_url) if source_url.isdigit() else source_url
    capture = cv2.VideoCapture(source)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    if not capture.isOpened():
        capture.release()
        raise StreamUnavailable(f"could not open stream {source_url!r}")
    return capture


def probe_stream(source_url: str, timeout_seconds: float = 8.0) -> dict:
    """Try to open a stream URL and decode one frame; never raises on
    connection problems, only on missing OpenCV (ImportError).

    Runs in a worker thread because cv2.VideoCapture can block well past the
    ffmpeg socket timeout on misbehaving sources; a timed-out probe leaves the
    daemon thread to die with its socket rather than blocking the request.
    """
    import cv2  # noqa: F401  deferred: optional heavy dependency

    result: dict = {}

    def _worker() -> None:
        start = time.monotonic()
        capture = None
        try:
            capture = _open_capture(source_url)
            ok, frame = capture.read()
            if ok and frame is not None:
                height, width = frame.shape[:2]
                result.update(
                    ok=True,
                    detail="Stream opened, first frame decoded",
                    width=width,
                    height=height,
                    latency_ms=int((time.monotonic() - start) * 1000),
                )
            else:
                result.update(ok=False, detail="Stream opened but no frame could be decoded")
        except StreamUnavailable as exc:
            result.update(ok=False, detail=str(exc))
        except Exception as exc:  # cv2 raises plain errors for bad sources
            result.update(ok=False, detail=f"{type(exc).__name__}: {exc}")
        finally:
            if capture is not None:
                capture.release()

    thread = threading.Thread(target=_worker, name="stream-probe", daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive() or not result:
        return {"ok": False, "detail": f"No response within {int(timeout_seconds)}s"}
    return result


_VEHICLE_COLOR = (80, 200, 120)  # BGR green
_PLATE_COLOR = (0, 215, 255)  # BGR amber


def _draw_overlays(frame, overlays) -> None:
    """Draw recognition boxes (vehicle + plate + plate text) on a frame.

    Runs before downscaling, so coordinates are in source resolution."""
    import cv2

    for item in overlays:
        vehicle = item.get("vehicle")
        plate = item.get("plate")
        label = item.get("label", "")
        if vehicle:
            cv2.rectangle(frame, (vehicle[0], vehicle[1]), (vehicle[2], vehicle[3]),
                          _VEHICLE_COLOR, 2)
        if plate:
            cv2.rectangle(frame, (plate[0], plate[1]), (plate[2], plate[3]),
                          _PLATE_COLOR, 3)
        anchor = plate or vehicle
        if label and anchor:
            scale = max(frame.shape[1] / 1280.0, 0.7)
            thickness = max(int(scale * 2), 1)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
            tx, ty = anchor[0], max(anchor[1] - 8, th + 4)
            cv2.rectangle(frame, (tx - 2, ty - th - 4), (tx + tw + 2, ty + 4),
                          (0, 0, 0), cv2.FILLED)
            cv2.putText(frame, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, scale,
                        _PLATE_COLOR, thickness, cv2.LINE_AA)


def _multipart(jpeg: bytes) -> bytes:
    return (
        f"--{BOUNDARY}\r\n"
        f"Content-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n"
    ).encode() + jpeg + b"\r\n"


class PipelineFrameStream:
    """MJPEG restream sourced from the pipeline's pre-annotated frames.

    No camera connection, no decode, no server-side overlay: it just repeats
    the newest annotated JPEG the pipeline pushed, at the viewer fps cap. Used
    whenever the pipeline is feeding this camera; ends itself if frames go
    stale so the client reconnects (and falls back to a direct restream)."""

    # Give up if the pipeline stops feeding frames for this long.
    _STALE_TIMEOUT = 4.0

    def __init__(self, camera_id: int, fps: int | None = None):
        settings = get_settings()
        _acquire_slot(settings.stream_max_viewers)
        self._camera_id = camera_id
        self._interval = 1.0 / max(fps or settings.stream_fps, 1)
        self._last_sent = 0.0
        self._stale_since: float | None = None
        self._closed = False

    def __iter__(self):
        return self

    def __next__(self) -> bytes:
        from app.services.live_frames import get_frame

        if self._closed:
            raise StopIteration
        while True:
            wait = self._interval - (time.monotonic() - self._last_sent)
            if wait > 0:
                time.sleep(min(wait, 0.05))
            jpeg = get_frame(self._camera_id)
            if jpeg is None:
                now = time.monotonic()
                if self._stale_since is None:
                    self._stale_since = now
                elif now - self._stale_since > self._STALE_TIMEOUT:
                    self.close()
                    raise StopIteration
                time.sleep(0.1)
                continue
            self._stale_since = None
            self._last_sent = time.monotonic()
            return _multipart(jpeg)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            _release_slot()


class MjpegStream:
    """Iterator of multipart JPEG parts; opens the source eagerly so the
    endpoint can return a real HTTP error before the response starts."""

    def __init__(self, source_url: str, overlay_provider=None, fps: int | None = None):
        settings = get_settings()
        _acquire_slot(settings.stream_max_viewers)
        try:
            self._capture = _open_capture(source_url)
        except Exception:
            _release_slot()
            raise
        # Per-camera fps override (cameras.config["live_fps"]) beats the
        # global ANPR_STREAM_FPS default.
        self._interval = 1.0 / max(fps or settings.stream_fps, 1)
        self._max_width = settings.stream_max_width
        self._last_sent = 0.0
        self._failures = 0
        self._closed = False
        # Optional zero-arg callable -> [{vehicle, plate, label}, ...]; drawn
        # on every frame. Must be cheap — it runs per frame.
        self._overlay_provider = overlay_provider

    def __iter__(self):
        return self

    def __next__(self) -> bytes:
        import cv2

        if self._closed:
            raise StopIteration
        while True:
            # grab() advances the stream without decoding — nearly free. We
            # decode (retrieve) only the frames we actually send, so heavy
            # sources (4K HEVC on CPU) can't fall behind and build up lag.
            if not self._capture.grab():
                self._failures += 1
                if self._failures > _MAX_READ_FAILURES:
                    self.close()
                    raise StopIteration
                time.sleep(0.1)
                continue
            self._failures = 0
            now = time.monotonic()
            if now - self._last_sent < self._interval:
                continue
            ok, frame = self._capture.retrieve()
            if not ok or frame is None:
                self._failures += 1
                continue
            self._last_sent = now

            if self._overlay_provider is not None:
                try:
                    overlays = self._overlay_provider()
                except Exception:  # overlay is cosmetic; never kill the stream
                    overlays = ()
                if overlays:
                    _draw_overlays(frame, overlays)

            height, width = frame.shape[:2]
            if width > self._max_width:
                scale = self._max_width / width
                frame = cv2.resize(
                    frame, (self._max_width, int(height * scale)), interpolation=cv2.INTER_AREA
                )
            ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
            if not ok:
                continue
            jpeg = buffer.tobytes()
            return (
                f"--{BOUNDARY}\r\n"
                f"Content-Type: image/jpeg\r\nContent-Length: {len(jpeg)}\r\n\r\n"
            ).encode() + jpeg + b"\r\n"

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._capture.release()
            _release_slot()
