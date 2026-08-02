"""
Step 7 of the Verifio pipeline: combines every signal collected so far
into a single ACCEPT / REVIEW / REJECT verdict with explicit reasons.

Deliberately a plain rule cascade, not a learned/weighted score — every
verdict needs to be explainable to a reviewer ("rejected because the ID
number field didn't match the expected format"), and the checks upstream
already produce clean pass/fail + confidence signals, so there's nothing
for an ML model to add here.

Rule priority (first match wins):
  1. document type not recognized      -> REJECT
  2. quality gate failed                -> REJECT   (Step 3 already fails fast on this)
  3. tampering detected                 -> REJECT   (ELA precision is tuned high, ~94%,
                                                       so a flag here is trusted)
  4. a critical field (id_number/dob)
     fails format validation            -> REJECT
  5. a non-critical field invalid, or
     any field's OCR confidence is low  -> REVIEW   (needs a human to confirm)
  6. everything passed                  -> ACCEPT
"""
CRITICAL_FIELDS = {"id_number", "dob"}
# Tuned against data/synthetic/ clean documents: id_number/dob confidence
# legitimately dips to ~0.4-0.45 on correctly-extracted fields (short,
# mixed-character crops score lower even when EasyOCR gets them right,
# and our positional format-correction in field_validation.py already
# recovers correctness independent of raw confidence). A higher threshold
# routed ~1/3 of genuinely clean documents to REVIEW for no reason.
LOW_CONFIDENCE_THRESHOLD = 0.4


def make_decision(doc_type_result: dict, quality_result: dict | None,
                   validated_fields: dict | None, tamper_result: dict | None) -> dict:
    if doc_type_result["doc_type"] is None:
        return {
            "verdict": "REJECT",
            "reasons": [f"document type not recognized ({doc_type_result['reason']})"],
        }

    if not quality_result["passed"]:
        return {
            "verdict": "REJECT",
            "reasons": [f"quality check failed: {reason}" for reason in quality_result["failure_reasons"]],
        }

    if tamper_result["tampering_detected"]:
        fields = ", ".join(tamper_result["suspicious_fields"])
        return {
            "verdict": "REJECT",
            "reasons": [f"potential tampering detected in field(s): {fields}"],
        }

    invalid_fields = [f for f, d in validated_fields.items() if not d["valid"]]
    low_confidence_fields = [f for f, d in validated_fields.items()
                              if d["confidence"] < LOW_CONFIDENCE_THRESHOLD]

    critical_invalid = [f for f in invalid_fields if f in CRITICAL_FIELDS]
    if critical_invalid:
        return {
            "verdict": "REJECT",
            "reasons": [f"{f}: {validated_fields[f]['reason']}" for f in critical_invalid],
        }

    if invalid_fields or low_confidence_fields:
        reasons = [f"{f}: {validated_fields[f]['reason']}" for f in invalid_fields]
        reasons += [
            f"{f}: low OCR confidence ({validated_fields[f]['confidence']:.2f}), please verify manually"
            for f in low_confidence_fields if f not in invalid_fields
        ]
        return {"verdict": "REVIEW", "reasons": reasons}

    return {"verdict": "ACCEPT", "reasons": ["all checks passed"]}
