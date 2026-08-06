"""
Evaluates the Step 6 ELA tampering detector against ground truth (Day 4
deliverable). Like OCR, this only runs on 'clean' and 'tampered' variants
— those are the only ones that reach Step 6 in the real pipeline (others
are already rejected by the Step 3 quality gate).

Usage:
    python data/evaluate_tampering.py
"""
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "backend"))

from app.services.tamper_detection import check_tampering  # noqa: E402

SYNTHETIC_DIR = ROOT / "synthetic"
GROUND_TRUTH = SYNTHETIC_DIR / "ground_truth.json"


def main():
    with open(GROUND_TRUTH) as f:
        records = json.load(f)

    eligible = [r for r in records if r["variant"] in ("clean", "tampered")]

    tp = fp = tn = fn = 0
    correct_field = 0
    mismatches = []

    for rec in eligible:
        img = cv2.imread(str(SYNTHETIC_DIR / rec["filename"]))
        result = check_tampering(img, rec["doc_type"])

        expected_tampered = rec["variant"] == "tampered"
        predicted_tampered = result["tampering_detected"]

        if expected_tampered and predicted_tampered:
            tp += 1
            if rec["tampered_field"] in result["suspicious_fields"]:
                correct_field += 1
        elif not expected_tampered and not predicted_tampered:
            tn += 1
        elif not expected_tampered and predicted_tampered:
            fp += 1
        else:
            fn += 1

        if expected_tampered != predicted_tampered:
            mismatches.append({
                "filename": rec["filename"],
                "expected_tampered_field": rec["tampered_field"],
                "predicted_suspicious": result["suspicious_fields"],
                "z_scores": result["field_z_scores"],
            })

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    tampered_n = tp + fn

    print(f"=== Tampering detection (n={total}) ===")
    print(f"  TP={tp}  FP={fp}  TN={tn}  FN={fn}")
    print(f"  Precision={precision:.2%}  Recall={recall:.2%}")
    print(f"  Correct field localized: {correct_field}/{tampered_n} "
          f"({correct_field / tampered_n:.1%} of true positives)" if tampered_n else "")

    if mismatches:
        print("\n=== Mismatches ===")
        for m in mismatches:
            print(f"  {m['filename']}: expected_field={m['expected_tampered_field']} "
                  f"predicted_suspicious={m['predicted_suspicious']} z_scores={m['z_scores']}")
    else:
        print("\nNo mismatches — all tampering verdicts match ground truth.")


if __name__ == "__main__":
    main()
