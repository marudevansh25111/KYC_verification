"""
Step 4 of the Verifio pipeline: region-based OCR field extraction.

Rather than running OCR on the whole document and guessing which text
belongs to which field, we use the known template layout (templates.py)
to crop just the value area of each field and OCR it in isolation. This
is both more accurate and gives a natural per-field confidence score
straight from EasyOCR's recognizer.

EasyOCR's reader (CRAFT detector + CRNN recognizer) is loaded once at
import time and reused across requests — instantiating it per-request
would reload the model weights every call.
"""
import cv2
import easyocr
import numpy as np

from app.services.templates import TEMPLATES, value_crop_box

_reader = None


def get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _reader


def _preprocess_for_ocr(crop_bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    scaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    denoised = cv2.fastNlMeansDenoising(scaled, h=10)
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def extract_fields(image_bgr: np.ndarray, doc_type: str) -> dict:
    """
    Returns: {field_name: {"text": str, "confidence": float}}
    confidence is the mean of EasyOCR's per-detection confidence for that
    field's crop (0.0 if nothing was detected).
    """
    if doc_type not in TEMPLATES:
        raise ValueError(f"Unknown doc_type: {doc_type}")

    reader = get_reader()
    fields = TEMPLATES[doc_type]["fields"]
    results = {}

    for field_name, spec in fields.items():
        x1, y1, x2, y2 = value_crop_box(spec["box"], field_name)
        crop = image_bgr[y1:y2, x1:x2]
        if crop.size == 0:
            results[field_name] = {"text": "", "confidence": 0.0}
            continue

        processed = _preprocess_for_ocr(crop)
        detections = reader.readtext(processed, detail=1, paragraph=False)

        if not detections:
            results[field_name] = {"text": "", "confidence": 0.0}
            continue

        texts = [d[1] for d in detections]
        confidences = [d[2] for d in detections]
        results[field_name] = {
            "text": " ".join(texts).strip(),
            "confidence": round(float(np.mean(confidences)), 4),
        }

    return results
