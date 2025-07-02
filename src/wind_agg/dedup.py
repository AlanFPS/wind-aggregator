"""
Perceptual-hash clustering to drop near-duplicates.

`filter_near_dupes(url_to_info)` expects:
    url_to_info = {url: {"pil": Image, "quality": float, ...}}

Returns:
    keep_urls  – list[str]   (one per cluster – best quality)
    clusters   – list[list[str]]  (all urls in each cluster)
"""
from collections import defaultdict
from typing import Dict, List, Tuple
import imagehash
from PIL import Image

HAMMING_THRESHOLD = 5   # smaller = stricter dedup

def _phash(img: Image.Image) -> imagehash.ImageHash:
    return imagehash.phash(img, hash_size=16)

def filter_near_dupes(url_to_info: Dict[str, dict]) -> Tuple[List[str], List[List[str]]]:
    hash_to_urls: Dict[str, List[str]] = defaultdict(list)

    for url, info in url_to_info.items():
        ph = _phash(info["pil"])
        hash_to_urls[str(ph)].append(url)

    keep_urls, clusters = [], []
    for urls in hash_to_urls.values():
        clusters.append(urls)
        # choose highest-quality in this bucket
        best = max(urls, key=lambda u: url_to_info[u]["quality"])
        keep_urls.append(best)

    return keep_urls, clusters