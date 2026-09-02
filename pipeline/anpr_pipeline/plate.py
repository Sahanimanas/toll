"""Plate localization within a vehicle crop, plus perspective correction.

- YoloPlateDetector: dedicated plate model (recommended for production).
- ContourPlateDetector: classical fallback — edge density + aspect-ratio
  heuristics. Works surprisingly well on frontal captures, fails gracefully
  (returns nothing) otherwise.
"""

import logging

import cv2
import numpy as np

from anpr_pipeline.detect import Detection

logger = logging.getLogger(__name__)

PLATE_ASPECT_MIN = 1.5
PLATE_ASPECT_MAX = 7.0


class YoloPlateDetector:
    def __init__(self, model_path: str, conf: float = 0.30, device: str = "cpu", imgsz: int = 1280):
        from ultralytics import YOLO

        self.model = YOLO(model_path)
        self.conf = conf
        self.device = device
        self.imgsz = imgsz
        self.half = device.startswith("cuda")

    def detect(self, vehicle_crop: np.ndarray) -> Detection | None:
        results = self.model.predict(
            vehicle_crop, conf=self.conf, device=self.device, half=self.half,
            imgsz=self.imgsz, verbose=False,
        )
        best: Detection | None = None
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0])
                confidence = float(box.conf[0])
                if best is None or confidence > best.confidence:
                    best = Detection(x1, y1, x2, y2, confidence, "plate")
        return best


class ContourPlateDetector:
    def detect(self, vehicle_crop: np.ndarray) -> Detection | None:
        h, w = vehicle_crop.shape[:2]
        if h < 40 or w < 40:
            return None
        gray = cv2.cvtColor(vehicle_crop, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 7, 30, 30)
        edges = cv2.Canny(gray, 60, 180)
        edges = cv2.morphologyEx(
            edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (17, 3))
        )
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        best: Detection | None = None
        best_score = 0.0
        for contour in contours:
            x, y, cw, ch = cv2.boundingRect(contour)
            if ch < 12 or cw < 40:
                continue
            aspect = cw / float(ch)
            if not (PLATE_ASPECT_MIN <= aspect <= PLATE_ASPECT_MAX):
                continue
            area_ratio = (cw * ch) / float(w * h)
            if not (0.005 <= area_ratio <= 0.30):
                continue
            # Prefer wider, lower-in-frame candidates (plates sit low on vehicles).
            score = area_ratio * (1.0 + y / float(h))
            if score > best_score:
                best_score = score
                best = Detection(x, y, x + cw, y + ch, 0.4, "plate")
        return best


def correct_perspective(plate_bgr: np.ndarray) -> np.ndarray:
    """Deskew the plate crop using its minimum-area rectangle, if measurable."""
    gray = cv2.cvtColor(plate_bgr, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return plate_bgr
    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) < 0.3 * plate_bgr.shape[0] * plate_bgr.shape[1]:
        return plate_bgr
    rect = cv2.minAreaRect(contour)
    angle = rect[2]
    if angle > 45:
        angle -= 90
    if abs(angle) < 2 or abs(angle) > 30:
        return plate_bgr
    h, w = plate_bgr.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(
        plate_bgr, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )


def build_plate_detector(
    kind: str, model_path: str, device: str = "cpu", imgsz: int = 1280, conf: float = 0.30
):
    if kind in ("auto", "yolo"):
        try:
            detector = YoloPlateDetector(model_path, conf=conf, device=device, imgsz=imgsz)
            logger.info(
                "plate detector: YOLO (%s) on %s, imgsz %s", model_path, device, imgsz
            )
            return detector
        except Exception as exc:
            if kind == "yolo":
                raise
            logger.warning("plate YOLO unavailable (%s); using contour detector", exc)
    logger.info("plate detector: contour heuristic")
    return ContourPlateDetector()
