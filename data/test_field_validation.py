"""
Sanity-checks the Step 5 validation rules directly against hand-crafted
good/bad values (independent of OCR) — confirms the rule engine actually
rejects malformed fields, not just that it accepts clean OCR output.

Usage:
    python data/test_field_validation.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.field_validation import (  # noqa: E402
    validate_name, validate_id_number, validate_dob, validate_address,
)

CASES = [
    ("name", validate_name, "Kavya Verma", True, None),
    ("name", validate_name, "", False, None),
    ("name", validate_name, "X7", False, None),  # digits in a name
    ("name", validate_name, "K", False, None),  # too short

    ("id_number (PAN)", lambda t: validate_id_number(t, "type_a"), "AHFTR8040G", True, None),
    ("id_number (PAN)", lambda t: validate_id_number(t, "type_a"), "AHFTR80G", False, None),  # wrong length
    ("id_number (PAN)", lambda t: validate_id_number(t, "type_a"), "123456789A", False, None),  # all digits
    ("id_number (Aadhaar)", lambda t: validate_id_number(t, "type_b"), "8712 2368 5290", True, None),
    ("id_number (Aadhaar)", lambda t: validate_id_number(t, "type_b"), "8712 2368", False, None),  # too short

    ("dob", validate_dob, "21/07/1982", True, None),
    ("dob", validate_dob, "31/02/2000", False, None),  # Feb 31 doesn't exist
    ("dob", validate_dob, "01/01/2020", False, None),  # too young
    ("dob", validate_dob, "not a date", False, None),

    ("address", validate_address, "46, MG Road, Chennai - 237174", True, None),
    ("address", validate_address, "NA", False, None),  # too short
]


def main():
    passed = 0
    for label, fn, value, expected_valid, _ in CASES:
        valid, reason = fn(value)
        ok = valid == expected_valid
        status = "PASS" if ok else "FAIL"
        passed += ok
        print(f"[{status}] {label:22s} input={value!r:35s} valid={valid} (expected {expected_valid}) reason={reason}")

    print(f"\n{passed}/{len(CASES)} cases behaved as expected")
    if passed != len(CASES):
        sys.exit(1)


if __name__ == "__main__":
    main()
