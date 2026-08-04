"""
Step 6 of the Verifio pipeline: Error Level Analysis (ELA) tampering
detection.

How ELA works: recompress the image at a known JPEG quality and diff it
against the input. A region that's already "settled" into a JPEG
quantization grid (i.e. genuinely part of the original capture,
compressed at least once before) barely changes on recompression. A
region edited/pasted in AFTER the document's last real compression is
fresh pixel data — compressing it for the first time here introduces a
much larger residual. That elevated residual is the tampering signal.

Different fields have different *natural* baseline ELA levels regardless
of tampering (denser text produces more inherent JPEG edge noise), so we
don't compare fields against each other within one document. Instead we
calibrate an expected mean/stdev ELA score per (doc_type, field) from a
corpus of known-clean reference documents (see
data/calibrate_tamper_baselines.py) and flag a field when it deviates
far enough from ITS OWN historical baseline — this is the same idea as
statistical anomaly detection against a learned reference distribution.
"""
import json
from pathlib import Path

import cv2
import numpy as np

from app.services.templates import TEMPLATES

ELA_JPEG_QUALITY = 60  # deliberately more lossy than the source's quality=90 to amplify
                        # the first-time-quantization residual (see module docstring)
Z_SCORE_THRESHOLD = 1.8  # tuned against data/synthetic/ (see data/evaluate_tampering.py):
                          # ~94% precision / ~63% recall — biased toward precision since
                          # a tampering flag is a strong signal in the decision engine (Step 7)
MIN_STDEV = 0.1  # floor to avoid dividing by a near-zero calibrated stdev

BASELINES_PATH = Path(__file__).parent / "tamper_baselines.json"
_baselines = None


def _load_baselines() -> dict:
    global _baselines
    if _baselines is None:
        if not BASELINES_PATH.exists():
            raise FileNotFoundError(
                f"{BASELINES_PATH} not found — run data/calibrate_tamper_baselines.py first"
            )
        with open(BASELINES_PATH) as f:
            _baselines = json.load(f)
    return _baselines


def compute_ela_map(image_bgr: np.ndarray, quality: int = ELA_JPEG_QUALITY) -> np.ndarray:
    ok, encoded = cv2.imencode(".jpg", image_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("JPEG encode failed during ELA")
    recompressed = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    diff = cv2.absdiff(image_bgr, recompressed)
    return cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)


def _field_ela_scores(ela_map: np.ndarray, doc_type: str) -> dict:
    scores = {}
    for field_name, spec in TEMPLATES[doc_type]["fields"].items():
        x, y, w, h = spec["box"]
        crop = ela_map[y:y + h, x:x + w]
        scores[field_name] = float(np.mean(crop)) if crop.size else 0.0
    return scores


def check_tampering(image_bgr: np.ndarray, doc_type: str) -> dict:
    baselines = _load_baselines()[doc_type]
    ela_map = compute_ela_map(image_bgr)
    field_scores = _field_ela_scores(ela_map, doc_type)

    field_z_scores = {}
    suspicious_fields = []
    for field_name, score in field_scores.items():
        baseline = baselines[field_name]
        stdev = max(baseline["stdev"], MIN_STDEV)
        z = (score - baseline["mean"]) / stdev
        field_z_scores[field_name] = round(z, 2)
        if z > Z_SCORE_THRESHOLD:
            suspicious_fields.append(field_name)

    return {
        "tampering_detected": len(suspicious_fields) > 0,
        "suspicious_fields": suspicious_fields,
        "field_ela_scores": {k: round(v, 3) for k, v in field_scores.items()},
        "field_z_scores": field_z_scores,
    }
