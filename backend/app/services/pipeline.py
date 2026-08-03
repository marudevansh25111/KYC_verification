"""
Orchestrates the full Verifio pipeline (Steps 2-7) end to end. This is
what the FastAPI /verify endpoint and the offline evaluation scripts both
call, so the two never diverge in behavior.
"""
import numpy as np

from app.services.doc_type_detection import detect_doc_type
from app.services.quality_check import run_quality_checks
from app.services.ocr_extraction import extract_fields
from app.services.field_validation import validate_fields
from app.services.tamper_detection import check_tampering
from app.services.decision_engine import make_decision


def run_verification(image_bgr: np.ndarray) -> dict:
    doc_type_result = detect_doc_type(image_bgr)
    if doc_type_result["doc_type"] is None:
        decision = make_decision(doc_type_result, None, None, None)
        return {"doc_type": doc_type_result, "quality": None, "fields": None,
                "tampering": None, "decision": decision}

    doc_type = doc_type_result["doc_type"]

    quality_result = run_quality_checks(image_bgr)
    if not quality_result["passed"]:
        decision = make_decision(doc_type_result, quality_result, None, None)
        return {"doc_type": doc_type_result, "quality": quality_result, "fields": None,
                "tampering": None, "decision": decision}

    extracted = extract_fields(image_bgr, doc_type)
    validated_fields = validate_fields(extracted, doc_type)

    tamper_result = check_tampering(image_bgr, doc_type)

    decision = make_decision(doc_type_result, quality_result, validated_fields, tamper_result)

    return {
        "doc_type": doc_type_result,
        "quality": quality_result,
        "fields": validated_fields,
        "tampering": tamper_result,
        "decision": decision,
    }
