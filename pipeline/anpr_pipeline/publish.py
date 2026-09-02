"""Publishes recognitions to the backend ingest API.

Fault tolerance: if the backend is unreachable, the event (JSON + JPEG
evidence) is spooled to disk and replayed on the next successful publish
cycle, so a network outage never loses recognitions."""

import json
import logging
import uuid
from pathlib import Path

import cv2
import numpy as np
import requests

logger = logging.getLogger(__name__)


# Live overlay/frame pushes happen once per processed frame, so they must never
# hold up the pipeline: keep the timeout well under a frame budget and drop the
# frame if the backend can't take it now (the next one is milliseconds away).
_LIVE_TIMEOUT = 0.5


class BackendPublisher:
    def __init__(self, backend_url: str, api_key: str, spool_dir: str):
        base = backend_url.rstrip("/")
        self.url = base + "/api/v1/ingest/recognitions"
        self.detections_url = base + "/api/v1/ingest/detections"
        self.frame_url = base + "/api/v1/ingest/frame"
        self.api_key = api_key
        self.spool = Path(spool_dir)
        self.spool.mkdir(parents=True, exist_ok=True)
        # Keep-alive: at 30 fps a fresh TCP connection per frame is pure
        # overhead, and each push is to the same host.
        self._session = requests.Session()

    def push_live_boxes(self, camera_id: int, boxes: list[dict]) -> None:
        """Best-effort current-frame boxes for the live-view overlay.

        Ephemeral cosmetics: short timeout, no spooling, failures ignored."""
        try:
            self._session.post(
                self.detections_url,
                json={"camera_id": camera_id, "boxes": boxes[:32]},
                headers={"X-API-Key": self.api_key},
                timeout=_LIVE_TIMEOUT,
            )
        except requests.RequestException:
            pass

    def push_live_frame(self, camera_id: int, jpeg_bytes: bytes) -> None:
        """Best-effort annotated live-view frame (already boxed + downscaled).

        The backend caches the newest frame per camera and serves it to the
        dashboard, so no second camera connection is needed. Ephemeral: short
        timeout, no spooling, failures ignored."""
        try:
            self._session.post(
                self.frame_url,
                data={"camera_id": str(camera_id)},
                files={"frame": ("frame.jpg", jpeg_bytes, "image/jpeg")},
                headers={"X-API-Key": self.api_key},
                timeout=_LIVE_TIMEOUT,
            )
        except requests.RequestException:
            pass

    @staticmethod
    def _encode_jpeg(image: np.ndarray | None) -> bytes | None:
        if image is None or image.size == 0:
            return None
        ok, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
        return buffer.tobytes() if ok else None

    def publish(
        self,
        payload: dict,
        frame: np.ndarray | None = None,
        plate: np.ndarray | None = None,
    ) -> bool:
        frame_bytes = self._encode_jpeg(frame)
        plate_bytes = self._encode_jpeg(plate)
        if self._send(payload, frame_bytes, plate_bytes):
            self._drain_spool()
            return True
        self._spool_event(payload, frame_bytes, plate_bytes)
        return False

    def _send(self, payload: dict, frame_bytes: bytes | None, plate_bytes: bytes | None) -> bool:
        files = {}
        if frame_bytes:
            files["frame"] = ("frame.jpg", frame_bytes, "image/jpeg")
        if plate_bytes:
            files["plate"] = ("plate.jpg", plate_bytes, "image/jpeg")
        try:
            response = self._session.post(
                self.url,
                data={"payload": json.dumps(payload)},
                files=files or None,
                headers={"X-API-Key": self.api_key},
                timeout=10,
            )
            if response.status_code == 201:
                return True
            # 4xx (bad payload / unknown camera) will never succeed — drop it.
            if 400 <= response.status_code < 500:
                logger.error(
                    "ingest rejected (%s): %s", response.status_code, response.text[:300]
                )
                return True
            logger.warning("ingest failed with %s", response.status_code)
            return False
        except requests.RequestException as exc:
            logger.warning("backend unreachable: %s", exc)
            return False

    def _spool_event(self, payload: dict, frame_bytes: bytes | None, plate_bytes: bytes | None):
        event_id = uuid.uuid4().hex
        record = {"payload": payload, "frame": None, "plate": None}
        if frame_bytes:
            frame_path = self.spool / f"{event_id}_frame.jpg"
            frame_path.write_bytes(frame_bytes)
            record["frame"] = frame_path.name
        if plate_bytes:
            plate_path = self.spool / f"{event_id}_plate.jpg"
            plate_path.write_bytes(plate_bytes)
            record["plate"] = plate_path.name
        (self.spool / f"{event_id}.json").write_text(json.dumps(record))
        logger.info("spooled recognition %s for later delivery", event_id)

    def _drain_spool(self, limit: int = 50) -> None:
        for meta_path in sorted(self.spool.glob("*.json"))[:limit]:
            try:
                record = json.loads(meta_path.read_text())
                frame_bytes = plate_bytes = None
                if record.get("frame"):
                    frame_file = self.spool / record["frame"]
                    frame_bytes = frame_file.read_bytes() if frame_file.exists() else None
                if record.get("plate"):
                    plate_file = self.spool / record["plate"]
                    plate_bytes = plate_file.read_bytes() if plate_file.exists() else None
                if not self._send(record["payload"], frame_bytes, plate_bytes):
                    return  # backend went away again; stop draining
                for key in ("frame", "plate"):
                    if record.get(key):
                        (self.spool / record[key]).unlink(missing_ok=True)
                meta_path.unlink(missing_ok=True)
            except Exception:
                logger.exception("failed to replay spooled event %s", meta_path.name)
                meta_path.unlink(missing_ok=True)
