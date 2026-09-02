"""Per-camera processing loop implementing the full ANPR chain:

capture -> enhance -> vehicle detect -> track -> plate detect -> perspective
correction -> plate enhance -> OCR -> normalize/validate -> confidence gate ->
dedup -> speed estimate -> publish (with evidence).

One worker per camera; run in threads (I/O bound capture dominates) by main.py.
"""

import logging
import threading
import time
from collections import deque
from datetime import datetime, timezone

from anpr_pipeline.capture import VideoSource
from anpr_pipeline.config import PipelineConfig
from anpr_pipeline.enhance import enhance_frame, enhance_plate
from anpr_pipeline.ocr import normalize_plate, validate_plate
from anpr_pipeline.overlay import annotate_frame, encode_stream_jpeg
from anpr_pipeline.plate import correct_perspective
from anpr_pipeline.speed import estimate_speed_kmh
from anpr_pipeline.track import IouTracker, Track

logger = logging.getLogger(__name__)


class CameraWorker:
    def __init__(
        self,
        camera: dict,
        config: PipelineConfig,
        vehicle_detector,
        plate_detector,
        ocr_engine,
        dedup,
        publisher,
    ):
        self.camera = camera
        self.config = config
        self.vehicle_detector = vehicle_detector
        self.plate_detector = plate_detector
        self.ocr = ocr_engine
        self.dedup = dedup
        self.publisher = publisher
        self.tracker = IouTracker()
        self.source = VideoSource(camera["rtsp_url"])
        self.stop_requested = False
        self._live_plate_boxes: list[dict] = []
        # Hand-off between the read loop and the detector thread.
        self._latest_frame = None
        self._frame_lock = threading.Lock()
        # Newest boxes from the detector, drawn onto every streamed frame.
        self._overlay_boxes: list[dict] = []
        self._boxes_lock = threading.Lock()
        # (monotonic ts, plate_text, confidence) of recent sub-gate reads.
        self._recent_reads: deque[tuple[float, str, float]] = deque()
        # text -> last log time; keeps a static junk source (e.g. signage)
        # from flooding the log with identical rejection lines.
        self._last_reject_log: dict[str, float] = {}
        raw_fps = (camera.get("config") or {}).get("process_fps") or config.max_process_fps
        try:
            fps = float(raw_fps)
        except (TypeError, ValueError):
            fps = config.max_process_fps
        self._process_interval = 1.0 / min(max(fps, 1.0), 60.0)

    def run(self) -> None:
        """Read + stream the camera at its own frame rate.

        Recognition is deliberately NOT done here. A full detect pass costs
        ~250ms (vehicle YOLO + plate YOLO + OCR), so running it inline caps the
        live view at ~4fps — the operator sees a slideshow. The read loop only
        decodes, draws the newest boxes and ships the frame (~10ms), so the
        view keeps the camera's real frame rate; the detector thread consumes
        whatever frames it can and republishes boxes as it goes.
        """
        camera_id = self.camera["id"]
        logger.info("worker started for camera %s (%s)", camera_id, self.camera["name"])
        detector = threading.Thread(
            target=self._detect_loop, name=f"detect-{camera_id}", daemon=True
        )
        detector.start()
        while not self.stop_requested:
            frame = self.source.read()
            with self._frame_lock:
                self._latest_frame = frame
            self._stream_frame(frame)
        self.source.release()

    def _stream_frame(self, frame) -> None:
        """Draw the newest boxes on this frame and push it to the live view."""
        if self.config.stream_max_width <= 0:
            return
        with self._boxes_lock:
            boxes = list(self._overlay_boxes)
        jpeg = encode_stream_jpeg(
            annotate_frame(frame, boxes),
            self.config.stream_max_width,
            self.config.stream_jpeg_quality,
        )
        if jpeg is not None:
            self.publisher.push_live_frame(self.camera["id"], jpeg)

    def _detect_loop(self) -> None:
        """Run recognition on the newest available frame, as fast as we can.

        Always takes the LATEST frame and drops whatever piled up behind it:
        detecting on stale frames would put boxes on positions the vehicle has
        already left. Paced by the per-camera fps cap so a fast GPU doesn't
        burn the whole card on redundant frames.
        """
        camera_id = self.camera["id"]
        next_allowed = 0.0
        while not self.stop_requested:
            now = time.monotonic()
            if now < next_allowed:
                time.sleep(min(next_allowed - now, 0.02))
                continue
            with self._frame_lock:
                frame, self._latest_frame = self._latest_frame, None
            if frame is None:
                time.sleep(0.005)
                continue
            next_allowed = time.monotonic() + self._process_interval
            try:
                self.process_frame(frame, time.monotonic())
            except Exception:
                logger.exception("frame processing failed on camera %s", camera_id)

    def process_frame(self, frame, timestamp: float) -> None:
        enhanced = enhance_frame(frame)
        detections = self.vehicle_detector.detect(enhanced)
        tracks = self.tracker.update(detections, timestamp)
        # Collected during recognition attempts; pushed (with vehicle boxes)
        # to the backend for the live-view overlay at the end of the frame.
        self._live_plate_boxes: list[dict] = []
        for track in self._recognition_candidates(tracks, timestamp):
            self._try_recognize(enhanced, frame, track)
        if not detections and self.config.full_frame_plates:
            # Plate-first fallback: close-up, cropped, or parked vehicles the
            # vehicle detector misses can still yield a readable plate.
            self._try_recognize_frame(enhanced, frame)
        boxes = [
            {"x1": d.x1, "y1": d.y1, "x2": d.x2, "y2": d.y2,
             "kind": "vehicle", "label": d.label}
            for d in detections
        ] + self._live_plate_boxes + self._remembered_plate_boxes(tracks)
        # Hand the boxes to the read loop, which draws them on the frames it is
        # already streaming. They lag the video by one detect pass (~250ms) —
        # the alternative, baking boxes in here, pins the whole live view to
        # the detector's ~4fps, which is far worse to watch.
        with self._boxes_lock:
            self._overlay_boxes = boxes
        if boxes:
            self.publisher.push_live_boxes(self.camera["id"], boxes)

    def _recognition_candidates(self, tracks, now: float) -> list[Track]:
        """Choose which tracks get a plate-read attempt on this frame.

        Every attempt costs a plate-detector pass plus an OCR pass, so reading
        all unpublished tracks every frame collapses a busy scene to a couple
        of fps — and the worst offenders (parked or distant vehicles) never
        publish, so they never stop being retried. Instead each track is
        retried at most every `plate_retry_seconds`, and only the largest few
        run per frame: the nearest vehicle fills the most pixels and is the
        one whose plate is actually readable.
        """
        due = [
            t for t in tracks
            if not t.plate_published
            and now - t.last_attempt_at >= self.config.plate_retry_seconds
        ]
        due.sort(key=lambda t: (t.bbox[2] - t.bbox[0]) * (t.bbox[3] - t.bbox[1]), reverse=True)
        chosen = due[: max(self.config.max_plate_attempts_per_frame, 1)]
        for track in chosen:
            track.last_attempt_at = now
        return chosen

    def _remembered_plate_boxes(self, tracks) -> list[dict]:
        """Plate boxes for tracks whose plate has already been published.

        Those tracks are skipped by the recognition pass (one publish per
        vehicle), so without this their plate box would vanish the moment the
        read succeeded. Operators need the opposite: the plate stays boxed and
        labelled on the vehicle for as long as it is tracked.
        """
        boxes = []
        for track in tracks:
            if not (track.plate_published and track.best_plate and track.plate_rel):
                continue
            x1, y1, x2, y2 = track.bbox
            vw, vh = max(x2 - x1, 1), max(y2 - y1, 1)
            rx1, ry1, rx2, ry2 = track.plate_rel
            boxes.append({
                "x1": int(x1 + rx1 * vw), "y1": int(y1 + ry1 * vh),
                "x2": int(x1 + rx2 * vw), "y2": int(y1 + ry2 * vh),
                "kind": "plate", "label": track.best_plate[0],
            })
        return boxes

    def _log_reject(self, plate_text: str, confidence: float, reason: str) -> None:
        now = time.monotonic()
        if now - self._last_reject_log.get(plate_text, 0.0) < 30.0:
            return
        self._last_reject_log[plate_text] = now
        logger.info(
            "camera %s: read %r (conf %.2f) rejected: %s",
            self.camera["id"], plate_text, confidence, reason,
        )

    def _confidence_ok(self, plate_text: str, confidence: float) -> bool:
        """Confidence gate with multi-frame consensus.

        A single strong read passes outright. A weaker (but not junk) read
        passes once the same normalized text has been read consensus_reads
        times within the window — agreement across frames beats one lucky
        frame, which is what a moving vehicle rarely gives you."""
        if confidence >= self.config.min_ocr_confidence:
            return True
        if confidence < self.config.consensus_min_confidence:
            return False
        now = time.monotonic()
        window = self.config.consensus_window_seconds
        while self._recent_reads and now - self._recent_reads[0][0] > window:
            self._recent_reads.popleft()
        self._recent_reads.append((now, plate_text, confidence))
        votes = sum(1 for _, text, _ in self._recent_reads if text == plate_text)
        return votes >= self.config.consensus_reads

    def _try_recognize_frame(self, enhanced, original) -> None:
        """Detect + read a plate on the whole frame (no vehicle track).

        Same gates as the track path (confidence, grammar, dedup); published
        with vehicle_type 'unknown' and no speed since there is no track."""
        if self.ocr is None:
            return
        plate_det = self.plate_detector.detect(enhanced)
        if plate_det is None:
            return
        px1, py1, px2, py2 = plate_det.bbox
        # Camera OSD overlays (clock, name) sit in the top strip and trigger
        # the plate detector constantly; real plates don't live there.
        if (py1 + py2) / 2 < self.config.ignore_top_ratio * enhanced.shape[0]:
            return
        plate_live_box = {
            "x1": max(0, px1), "y1": max(0, py1), "x2": px2, "y2": py2, "kind": "plate",
        }
        self._live_plate_boxes.append(plate_live_box)
        plate_crop = enhanced[max(0, py1):py2, max(0, px1):px2]
        if plate_crop.size == 0:
            return
        plate_crop = correct_perspective(plate_crop)
        raw_text, confidence = self.ocr.read(enhance_plate(plate_crop))
        plate_text = normalize_plate(raw_text, self.config.region)
        camera_id = self.camera["id"]
        if not validate_plate(plate_text, self.config.region):
            self._log_reject(plate_text, confidence, "invalid plate format")
            return
        # Grammar-valid read: show it on the live view immediately, even before
        # the confidence/consensus publish gate resolves.
        plate_live_box["label"] = plate_text
        if not self._confidence_ok(plate_text, confidence):
            self._log_reject(plate_text, confidence, "below gate, awaiting consensus")
            return
        if self.dedup.is_duplicate(camera_id, plate_text):
            return
        plate_bbox = {"x1": max(0, px1), "y1": max(0, py1), "x2": px2, "y2": py2}
        payload = {
            "camera_id": camera_id,
            "plate_text": plate_text,
            "plate_confidence": round(min(confidence, 1.0), 4),
            "ocr_raw": raw_text[:64],
            "vehicle_type": "unknown",
            "vehicle_confidence": 0.0,
            "speed_kmh": None,
            "direction": self.camera.get("direction", ""),
            "track_id": "",
            "bbox": {**plate_bbox, "plate": plate_bbox},
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        self.publisher.publish(payload, frame=original, plate=plate_crop)
        logger.info(
            "camera %s: %s (conf %.2f, full-frame plate)", camera_id, plate_text, confidence
        )

    def _try_recognize(self, enhanced, original, track: Track) -> None:
        if self.ocr is None:
            return
        x1, y1, x2, y2 = track.bbox
        h, w = enhanced.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 < 40 or y2 - y1 < 40:
            return
        vehicle_crop = enhanced[y1:y2, x1:x2]

        plate_det = self.plate_detector.detect(vehicle_crop)
        if plate_det is None:
            return
        px1, py1, px2, py2 = plate_det.bbox
        plate_live_box = {
            "x1": x1 + max(0, px1), "y1": y1 + max(0, py1),
            "x2": min(x1 + px2, x2), "y2": min(y1 + py2, y2), "kind": "plate",
        }
        self._live_plate_boxes.append(plate_live_box)
        plate_crop = vehicle_crop[max(0, py1) : py2, max(0, px1) : px2]
        if plate_crop.size == 0:
            return

        plate_crop = correct_perspective(plate_crop)
        plate_ready = enhance_plate(plate_crop)
        raw_text, confidence = self.ocr.read(plate_ready)
        plate_text = normalize_plate(raw_text, self.config.region)

        if not validate_plate(plate_text, self.config.region):
            self._log_reject(plate_text, confidence, "invalid plate format")
            return
        # Grammar-valid read: label the live box immediately (pre-publish gate).
        plate_live_box["label"] = plate_text
        if not self._confidence_ok(plate_text, confidence):
            self._log_reject(plate_text, confidence, "below gate, awaiting consensus")
            return

        # Keep the best read per track; publish once per vehicle pass.
        if track.best_plate is None or confidence > track.best_plate[1]:
            track.best_plate = (plate_text, confidence)
            # Remember where the plate sits inside the vehicle box (as
            # fractions) so the live view can keep drawing it after publish,
            # following the vehicle as it moves.
            vw, vh = max(x2 - x1, 1), max(y2 - y1, 1)
            track.plate_rel = (
                max(0, px1) / vw, max(0, py1) / vh,
                min(px2, vw) / vw, min(py2, vh) / vh,
            )

        camera_id = self.camera["id"]
        if self.dedup.is_duplicate(camera_id, plate_text):
            track.plate_published = True
            return

        meters_per_pixel = (self.camera.get("config") or {}).get("meters_per_pixel")
        speed = estimate_speed_kmh(track, meters_per_pixel)

        # Plate box in full-frame coordinates (px* are vehicle-crop relative);
        # the backend draws it on the live restream.
        plate_bbox = {
            "x1": x1 + max(0, px1),
            "y1": y1 + max(0, py1),
            "x2": min(x1 + px2, x2),
            "y2": min(y1 + py2, y2),
        }

        payload = {
            "camera_id": camera_id,
            "plate_text": plate_text,
            "plate_confidence": round(min(confidence, 1.0), 4),
            "ocr_raw": raw_text[:64],
            "vehicle_type": track.label,
            "vehicle_confidence": round(min(track.confidence, 1.0), 4),
            "speed_kmh": speed,
            "direction": self.camera.get("direction", ""),
            "track_id": track.track_id,
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "plate": plate_bbox},
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        self.publisher.publish(payload, frame=original, plate=plate_crop)
        track.plate_published = True
        logger.info(
            "camera %s: %s (conf %.2f, speed %s)", camera_id, plate_text, confidence, speed
        )
