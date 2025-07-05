"""
Quality filters without OpenCV.

Blur detection:  variance of the FIND_EDGES image.
Brightness check:  grayscale mean.
"""
from typing import Tuple
from PIL import Image, ImageFilter
import numpy as np

BLUR_THRESHOLD   = 100.0   # tweak as needed
BRIGHT_THRESHOLD = 5       # 0–255

def assess_quality(pil: Image.Image) -> Tuple[bool, float]:
    gray = pil.convert("L")

    # Edge map and variance ≈ Laplacian variance
    edges = gray.filter(ImageFilter.FIND_EDGES)
    lap_var = float(np.var(edges))

    blur_ok  = lap_var >= BLUR_THRESHOLD
    bright_ok= float(np.mean(gray)) >= BRIGHT_THRESHOLD
    keep = blur_ok and bright_ok

    # Simple quality weight 0-1
    blur_score   = min(lap_var / (BLUR_THRESHOLD * 4), 1.0)
    bright_score = min(np.mean(gray) / 255.0, 1.0)
    score = round(0.6 * blur_score + 0.4 * bright_score, 3)

    return keep, score