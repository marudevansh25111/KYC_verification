"""
Step 5 of the Verifio pipeline: rule-based field validation.

Plain regex/rule checks, deliberately no ML here — validation logic
needs to be explainable ("your PAN-style ID number doesn't match the
expected format"), not a black box.
"""
import re
from datetime import datetime

from app.services.templates import TEMPLATES

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
AADHAAR_RE = re.compile(r"^\d{4}\s?\d{4}\s?\d{4}$")
DOB_RE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")

MIN_AGE = 18
MAX_AGE = 100


# OCR commonly confuses visually similar glyphs (0/O, 1/I, 5/S, 8/B, 2/Z)
# in alphanumeric strings. Since PAN/Aadhaar-style ID numbers have a FIXED,
# KNOWN character class per position (e.g. PAN's first 5 characters must be
# letters, next 4 must be digits), the ambiguity can be resolved
# deterministically instead of guessing — the same technique real
# ID-parsing systems use for structured fields like passport MRZ lines.
DIGIT_TO_LETTER = {"0": "O", "1": "I", "5": "S", "8": "B", "2": "Z"}
LETTER_TO_DIGIT = {"O": "0", "I": "1", "S": "5", "B": "8", "Z": "2", "L": "1", "D": "0"}


def normalize_id_number_ocr(raw_text: str, doc_type: str) -> str:
    text = re.sub(r"\s+", "", raw_text.strip().upper())
    id_format = TEMPLATES[doc_type]["id_format"]

    if id_format == "pan" and len(text) == 10:
        chars = list(text)
        for i, c in enumerate(chars):
            expects_letter = i < 5 or i == 9
            if expects_letter and c.isdigit():
                chars[i] = DIGIT_TO_LETTER.get(c, c)
            elif not expects_letter and c.isalpha():
                chars[i] = LETTER_TO_DIGIT.get(c, c)
        text = "".join(chars)
    elif id_format == "aadhaar":
        text = "".join(LETTER_TO_DIGIT.get(c, c) if c.isalpha() else c for c in text)
        if len(text) == 12:
            text = f"{text[0:4]} {text[4:8]} {text[8:12]}"

    return text


def validate_name(text: str) -> tuple[bool, str | None]:
    text = text.strip()
    if not text:
        return False, "name is empty"
    if not (2 <= len(text) <= 60):
        return False, "name length implausible"
    if not re.match(r"^[A-Za-z .'-]+$", text):
        return False, "name contains unexpected characters"
    return True, None


def validate_id_number(text: str, doc_type: str) -> tuple[bool, str | None]:
    text = normalize_id_number_ocr(text, doc_type)
    id_format = TEMPLATES[doc_type]["id_format"]

    if id_format == "pan":
        if not PAN_RE.match(text.replace(" ", "")):
            return False, "ID number does not match PAN-style format (5 letters, 4 digits, 1 letter)"
    elif id_format == "aadhaar":
        if not AADHAAR_RE.match(text):
            return False, "ID number does not match Aadhaar-style format (12 digits)"
    return True, None


def validate_dob(text: str) -> tuple[bool, str | None]:
    text = text.strip()
    match = DOB_RE.match(text)
    if not match:
        return False, "date of birth is not in DD/MM/YYYY format"

    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        dob = datetime(year, month, day)
    except ValueError:
        return False, "date of birth is not a valid calendar date"

    age = (datetime.now() - dob).days / 365.25
    if not (MIN_AGE <= age <= MAX_AGE):
        return False, f"implausible age ({age:.0f}) derived from date of birth"
    return True, None


def validate_address(text: str) -> tuple[bool, str | None]:
    text = text.strip()
    if len(text) < 10:
        return False, "address is too short to be plausible"
    return True, None


_VALIDATORS = {
    "name": lambda text, doc_type: validate_name(text),
    "id_number": lambda text, doc_type: validate_id_number(text, doc_type),
    "dob": lambda text, doc_type: validate_dob(text),
    "address": lambda text, doc_type: validate_address(text),
}


def validate_fields(extracted_fields: dict, doc_type: str) -> dict:
    """
    extracted_fields: {field_name: {"text": str, "confidence": float}}
    Returns: {field_name: {"text", "raw_ocr_text", "confidence", "valid", "reason"}}

    For id_number, "text" is replaced with the format-corrected value (see
    normalize_id_number_ocr) while "raw_ocr_text" keeps what EasyOCR
    actually returned, so the dashboard can show both.
    """
    results = {}
    for field_name, data in extracted_fields.items():
        validator = _VALIDATORS.get(field_name)
        if validator is None:
            results[field_name] = {**data, "raw_ocr_text": data["text"], "valid": True, "reason": None}
            continue

        valid, reason = validator(data["text"], doc_type)
        display_text = data["text"]
        if field_name == "id_number":
            display_text = normalize_id_number_ocr(data["text"], doc_type)

        results[field_name] = {
            **data,
            "text": display_text,
            "raw_ocr_text": data["text"],
            "valid": valid,
            "reason": reason,
        }
    return results
