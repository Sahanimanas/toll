"""Image enhancement tuned for plate legibility, not aesthetics.

Frame-level: mild denoise + CLAHE on luminance (helps night/backlit scenes).
Plate-level: grayscale, upscale, CLAHE, sharpen — applied just before OCR.
"""

import cv2
import numpy as np

_clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))


def enhance_frame(frame: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    l_channel = _clahe.apply(l_channel)
    return cv2.cvtColor(cv2.merge((l_channel, a, b)), cv2.COLOR_LAB2BGR)


def enhance_plate(plate_bgr: np.ndarray, target_height: int = 64) -> np.ndarray:
    gray = cv2.cvtColor(plate_bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    if h < target_height and h > 0:
        scale = target_height / h
        gray = cv2.resize(
            gray, (int(w * scale), target_height), interpolation=cv2.INTER_CUBIC
        )
    gray = cv2.bilateralFilter(gray, 5, 40, 40)
    gray = _clahe.apply(gray)
    blur = cv2.GaussianBlur(gray, (0, 0), 2.0)
    return cv2.addWeighted(gray, 1.6, blur, -0.6, 0)
