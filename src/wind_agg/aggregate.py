"""
High-level orchestration for the wind-damage photo aggregator.
"""
from __future__ import annotations
import tempfile, urllib.request, uuid, os, logging, statistics, datetime
from typing import Dict, List

from PIL import Image
from PIL import ImageFilter
import numpy as np
import boto3

from .quality import assess_quality
from .dedup   import filter_near_dupes
from .vision  import analyze_image
from .models  import ClaimRequest, ClaimResponse, AreaResult, SourceImages

log = logging.getLogger(__name__)


def _download(url: str, dest_dir: str) -> str:
    fn = os.path.join(dest_dir, f"{uuid.uuid4()}.jpg")
    urllib.request.urlretrieve(url, fn)
    return fn


def process_claim(req: ClaimRequest, corr_id: str) -> ClaimResponse:
    rek = boto3.client("rekognition")
    tmp = tempfile.mkdtemp(prefix="wind_")

    url_to_info: Dict[str, dict] = {}
    discarded = 0

    # --- 1. download + quality filter ---------------------------------------
    for url in req.images:
        try:
            path = _download(str(url), tmp)
            pil  = Image.open(path).convert("RGB")
        except Exception as exc:
            log.warning("%s bad image %s (%s)", corr_id, url, exc)
            discarded += 1
            continue

        keep, qscore = assess_quality(pil)
        # Debug quality info
        gray = pil.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        lap_var = float(np.var(edges))
        bright = float(np.mean(gray))
        log.info("%s quality check %s: blur=%.2f bright=%.2f → keep=%s", corr_id, url, lap_var, bright, keep)

        if not keep:
            discarded += 1
            continue

        url_to_info[url] = {"pil": pil, "quality": qscore}

    if not url_to_info:
        raise ValueError("All images discarded as low quality")

    # --- 2. dedup ------------------------------------------------------------
    keep_urls, clusters = filter_near_dupes(url_to_info)
    url_to_info = {u: url_to_info[u] for u in keep_urls}

    # --- 3. vision analysis --------------------------------------------------
    for url, info in url_to_info.items():
        vision = analyze_image(info["pil"], rek_client=rek)
        info.update(vision)

    # --- 4. aggregate per area ----------------------------------------------
    areas: Dict[str, AreaResult] = {}
    for url, info in url_to_info.items():
        if not info["damage"]:
            continue
        area_key = info["area"] or "unknown"
        ar = areas.setdefault(area_key, AreaResult(area=area_key))
        ar.count += 1
        ar.severities.append(info["severity"])
        ar.rep_imgs.append(url)
        ar.quality_weights.append(info["quality"])

    # ---------- DAMAGE CONFIRMATION & SUMMARY ----------
    for ar in areas.values():
        high = [s for s in ar.severities if s >= 2]
        ar.damage_confirmed = len(high) >= 1
        ar.avg_severity     = round(statistics.mean(ar.severities), 2)
        # choose the sharpest photo as the representative
        if ar.rep_imgs:
            best = max(zip(ar.quality_weights, ar.rep_imgs))[1]
            ar.representative_images = [best]

    # keep every area (confirmed or not) so the UI always shows something
    area_results = list(areas.values())
    # ---------------------------------------------------

    # weighted overall severity
    numer = sum(info["severity"] * info["quality"] for info in url_to_info.values())
    denom = sum(info["quality"] for info in url_to_info.values())
    overall = round(numer / denom, 2) if denom else 0.0

    src_summary = SourceImages(
        total=len(req.images),
        analyzed=len(url_to_info),
        discarded_low_quality=discarded,
        clusters=len(clusters),
    )

    # confidence heuristic: proportion of kept imgs + damage confirmation count
    confirmed_count = sum(1 for ar in area_results if ar.damage_confirmed)
    confidence = round(
        min(1.0, 0.5 + confirmed_count / max(1, len(area_results)) * 0.5), 2
    )

    resp = ClaimResponse(
        claim_id=req.claim_id,
        source_images=src_summary,
        overall_damage_severity=overall,
        areas=area_results,
        data_gaps=["No attic photos"],   # stub – could be smarter
        confidence=confidence,
        generated_at=datetime.datetime.utcnow().isoformat() + "Z",
    )
    return resp