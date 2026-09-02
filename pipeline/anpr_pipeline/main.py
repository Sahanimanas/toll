"""Pipeline orchestrator: fetches active cameras from the backend and runs a
CameraWorker thread per camera. Camera list is re-checked periodically so
cameras added in the dashboard start processing without a restart."""

import logging
import sys
import threading
import time

import requests

from anpr_pipeline.config import PipelineConfig
from anpr_pipeline.dedup import build_duplicate_filter
from anpr_pipeline.detect import build_vehicle_detector
from anpr_pipeline.device import resolve_device
from anpr_pipeline.ocr import build_ocr_engine
from anpr_pipeline.plate import build_plate_detector
from anpr_pipeline.publish import BackendPublisher
from anpr_pipeline.worker import CameraWorker

logger = logging.getLogger(__name__)


def fetch_cameras(config: PipelineConfig) -> list[dict]:
    """Fetch active cameras. Uses the ingest key via an internal listing —
    falls back to empty list if the backend is down (retried next cycle)."""
    try:
        response = requests.get(
            config.backend_url.rstrip("/") + "/api/v1/ingest/cameras",
            headers={"X-API-Key": config.ingest_api_key},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        logger.warning("could not fetch cameras: %s", exc)
        return []


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    config = PipelineConfig()
    device = resolve_device(config.device)
    ocr_engine = build_ocr_engine(config.ocr_engine, device)
    dedup = build_duplicate_filter(config.redis_url, config.dedup_ttl_seconds)
    publisher = BackendPublisher(config.backend_url, config.ingest_api_key, config.spool_dir)

    workers: dict[int, tuple[CameraWorker, threading.Thread]] = {}
    while True:
        cameras = {c["id"]: c for c in fetch_cameras(config) if c.get("is_active", True)}

        for camera_id, camera in cameras.items():
            if camera_id not in workers or not workers[camera_id][1].is_alive():
                # Detectors are built per worker: the motion fallback keeps a
                # per-scene background model, and neither cv2 subtractors nor
                # YOLO .predict() are safe under concurrent calls from threads.
                vehicle_detector = build_vehicle_detector(
                    config.vehicle_detector, config.vehicle_model_path, device,
                    imgsz=config.vehicle_imgsz, conf=config.vehicle_conf,
                )
                plate_detector = build_plate_detector(
                    config.plate_detector, config.plate_model_path, device,
                    imgsz=config.plate_imgsz, conf=config.plate_conf,
                )
                worker = CameraWorker(
                    camera, config, vehicle_detector, plate_detector,
                    ocr_engine, dedup, publisher,
                )
                thread = threading.Thread(
                    target=worker.run, name=f"camera-{camera_id}", daemon=True
                )
                thread.start()
                workers[camera_id] = (worker, thread)

        for camera_id in list(workers):
            if camera_id not in cameras:
                logger.info("camera %s removed/deactivated; stopping worker", camera_id)
                workers[camera_id][0].stop_requested = True
                del workers[camera_id]

        time.sleep(config.camera_refresh_seconds)


if __name__ == "__main__":
    main()
