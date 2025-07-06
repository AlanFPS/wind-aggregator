"""
Thin wrapper around Amazon Rekognition DetectLabels.

`analyze_image(pil, client)` returns:
    {
      "damage": bool,
      "area":   str | None,     # roof / siding / garage / unknown
      "severity": int,          # 0-4
      "labels":  [(name, conf), ...]   # raw for debugging
    }
"""
from typing import Dict, List, Tuple
import boto3, io, re, logging
from PIL import Image

log = logging.getLogger(__name__)

# Map Rekognition label names to our canonical areas
AREA_MAP = {
    "Roof":  "roof",
    "Shingle": "roof",
    "Siding": "siding",
    "Wall":   "siding",
    "Garage": "garage",
    "Door":   "garage",
}

def _pil_to_bytes(pil: Image.Image) -> bytes:
    buf = io.BytesIO()
    pil.save(buf, format="JPEG")
    return buf.getvalue()

def _area_from_labels(labels: List[Tuple[str,float]]) -> str | None:
    for name, _ in labels:
        if name in AREA_MAP:
            return AREA_MAP[name]
    return None

def _severity_from_damage_conf(conf: float) -> int:
    """
    Map Rekognition confidence (0-100) to 0-4 band.
    Feel free to tweak thresholds in README assumptions.
    """
    return min(4, int(conf / 20))

DAMAGE_PAT = re.compile(
    r"(damage|crack|broken|missing|tear|dent|roof damage|home damage)",
    flags=re.I,
)

def analyze_image(pil: Image.Image, rek_client=None) -> Dict:
    if rek_client is None:
        rek_client = boto3.client("rekognition")

    resp = rek_client.detect_labels(Image={"Bytes": _pil_to_bytes(pil)},
                                    MaxLabels=50,
                                    MinConfidence=40)

    labels = [(l["Name"], l["Confidence"]) for l in resp["Labels"]]

    log.info("rekognition labels: %s", labels)

    damage_conf = max((c for n, c in labels if DAMAGE_PAT.search(n)), default=0)
    damage = damage_conf >= 40
    area   = _area_from_labels(labels)
    severity = _severity_from_damage_conf(damage_conf) if damage else 0

    return {
        "damage": damage,
        "area":   area,
        "severity": severity,
        "labels": labels
    }