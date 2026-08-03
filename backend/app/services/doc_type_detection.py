"""
Step 2 of the Verifio pipeline: document type detection.

Runs before the quality gate, so it can't assume the document is clean —
it only needs enough of the header band visible to read its color. Each
registered template has a distinctive header color; we sample the mean
color of the top HEADER_HEIGHT pixels and match it to the closest
registered template. If nothing matches closely enough (e.g. the header
was cropped out of frame, or this isn't a recognized document at all),
we report "unknown" rather than guessing — the decision engine treats
that as a hard reject.
"""
import numpy as np

from app.services.templates import TEMPLATES, HEADER_HEIGHT

MAX_COLOR_DISTANCE = 40.0  # in 0-255 RGB Euclidean distance; tuned against data/synthetic/


def detect_doc_type(image_bgr: np.ndarray) -> dict:
    h, w = image_bgr.shape[:2]
    header_strip = image_bgr[0:min(HEADER_HEIGHT, h), :]
    if header_strip.size == 0:
        return {"doc_type": None, "confidence": 0.0, "reason": "image too small to contain a header"}

    mean_bgr = header_strip.reshape(-1, 3).mean(axis=0)
    mean_rgb = mean_bgr[::-1]  # BGR -> RGB

    best_type, best_distance = None, float("inf")
    for doc_type, spec in TEMPLATES.items():
        target = np.array(spec["header_color_rgb"], dtype=float)
        distance = float(np.linalg.norm(mean_rgb - target))
        if distance < best_distance:
            best_type, best_distance = doc_type, distance

    if best_distance > MAX_COLOR_DISTANCE:
        return {"doc_type": None, "confidence": 0.0,
                "reason": f"header color didn't match any known template (distance={best_distance:.1f})"}

    confidence = max(0.0, 1.0 - best_distance / MAX_COLOR_DISTANCE)
    return {"doc_type": best_type, "confidence": round(confidence, 3), "reason": None}
