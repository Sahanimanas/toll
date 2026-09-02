"""Vehicle detection with pluggable backends.

- YoloVehicleDetector: ultralytics YOLO (GPU-capable, accurate).
- MotionVehicleDetector: background-subtraction fallback so the pipeline
  works on any machine with no model weights (accuracy is lower; it exists
  for bring-up, testing, and constrained edge devices).
"""

import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# COCO class ids for vehicles when using pretrained YOLO.
COCO_VEHICLES = {2: "car", 3: "motorcycle", 5: "bus", 7: "truck"}


@dataclass
class Detection:
    x1: int
    y1: int
    x2: int
    y2: int
    confidence: float
    label: str = "vehicle"

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return (self.x1, self.y1, self.x2, self.y2)


class YoloVehicleDetector:
    def __init__(
        self,
        model_path: str = "yolov8n.pt",
        conf: float = 0.35,
        device: str = "cpu",
        imgsz: int = 640,
    ):
        from ultralytics import YOLO  # deferred: heavy optional dependency

        self.model = YOLO(model_path)
        self.conf = conf
        self.device = device
        self.imgsz = imgsz
        # FP16 halves VRAM and roughly doubles throughput; CUDA-only.
        self.half = device.startswith("cuda")

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self.model.predict(
            frame, conf=self.conf, device=self.device, half=self.half,
            imgsz=self.imgsz, verbose=False,
        )
        detections: list[Detection] = []
        for result in results:
            for box in result.boxes:
                cls = int(box.cls[0])
                if cls not in COCO_VEHICLES:
                    continue
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                detections.append(
                    Detection(x1, y1, x2, y2, float(box.conf[0]), COCO_VEHICLES[cls])
                )
        return detections


class MotionVehicleDetector:
    def __init__(self, min_area_ratio: float = 0.005):
        self.subtractor = cv2.createBackgroundSubtractorMOG2(
            history=300, varThreshold=32, detectShadows=True
        )
        self.min_area_ratio = min_area_ratio

    def detect(self, frame: np.ndarray) -> list[Detection]:
        mask = self.subtractor.apply(frame)
        # Shadows are 127 in MOG2 output — drop them.
        _, mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = self.min_area_ratio * frame.shape[0] * frame.shape[1]
        detections = []
        for contour in contours:
            if cv2.contourArea(contour) < min_area:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            detections.append(Detection(x, y, x + w, y + h, 0.5, "vehicle"))
        return detections


def build_vehicle_detector(
    kind: str, model_path: str, device: str = "cpu", imgsz: int = 640, conf: float = 0.35
):
    if kind in ("auto", "yolo"):
        try:
            detector = YoloVehicleDetector(model_path, conf=conf, device=device, imgsz=imgsz)
            logger.info(
                "vehicle detector: YOLO (%s) on %s, imgsz %s", model_path, device, imgsz
            )
            return detector
        except Exception as exc:
            if kind == "yolo":
                raise
            logger.warning("YOLO unavailable (%s); falling back to motion detector", exc)
    logger.info("vehicle detector: motion (background subtraction)")
    return MotionVehicleDetector()
