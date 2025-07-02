"""
Image-quality filters and scoring.

Uses OpenCV Laplacian variance for blur detection
and a simple brightness threshold (grayscale mean).

`assess_quality` returns:
    • keep (bool)       – whether the image passes both checks
    • score (float 0-1) – quality weight for aggregation
"""
from typing import Tuple
import cv2
import numpy as np
from PIL import Image

BLUR_THRESHOLD   = 100.0   # Laplacian var; raise if too aggressive
BRIGHT_THRESHOLD = 30      # mean pixel (0-255)

def _to_cv_gray(pil: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2GRAY)

def assess_quality(pil: Image.Image) -> Tuple[bool, float]:
    gray = _to_cv_gray(pil)
    lap_var   = cv2.Laplacian(gray, cv2.CV_64F).var()
    blur_ok   = lap_var >= BLUR_THRESHOLD

    brightness = gray.mean()
    bright_ok  = brightness >= BRIGHT_THRESHOLD

    keep = blur_ok and bright_ok

    # Simple quality score: combine normalized blur + brightness
    blur_score  = min(lap_var / (BLUR_THRESHOLD * 4), 1.0)   # cap at 1
    bright_score= min(brightness / 255, 1.0)
    score = round(0.6 * blur_score + 0.4 * bright_score, 3)

    return keep, score