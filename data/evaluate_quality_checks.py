"""
Evaluates the Step 3 quality-check module against the synthetic dataset's
ground truth, to validate/tune thresholds (Day 2 deliverable).

Usage:
    python data/evaluate_quality_checks.py
"""
import json
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "backend"))

from app.services.quality_check import run_quality_checks  # noqa: E402

SYNTHETIC_DIR = ROOT / "synthetic"
GROUND_TRUTH = SYNTHETIC_DIR / "ground_truth.json"


def main():
    with open(GROUND_TRUTH) as f:
        records = json.load(f)

    per_variant = {}
    tp = fp = tn = fn = 0
    mismatches = []

    for rec in records:
        img_path = SYNTHETIC_DIR / rec["filename"]
        img = cv2.imread(str(img_path))
        result = run_quality_checks(img)

        predicted_pass = result["passed"]
        expected_pass = rec["expected_quality_verdict"] == "pass"

        variant = rec["variant"]
        per_variant.setdefault(variant, {"correct": 0, "total": 0})
        per_variant[variant]["total"] += 1
        if predicted_pass == expected_pass:
            per_variant[variant]["correct"] += 1
        else:
            mismatches.append({
                "filename": rec["filename"],
                "expected": rec["expected_quality_verdict"],
                "predicted": "pass" if predicted_pass else "fail",
                "failure_reasons": result["failure_reasons"],
            })

        if expected_pass and predicted_pass:
            tn += 1  # true "clean", correctly passed
        elif expected_pass and not predicted_pass:
            fp += 1  # false alarm on a clean doc
        elif not expected_pass and not predicted_pass:
            tp += 1  # correctly caught a bad doc
        else:
            fn += 1  # missed a bad doc

    print("=== Per-variant accuracy ===")
    for variant, stats in sorted(per_variant.items()):
        acc = stats["correct"] / stats["total"] * 100
        print(f"  {variant:10s}: {stats['correct']:3d}/{stats['total']:3d}  ({acc:.1f}%)")

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else float("nan")
    recall = tp / (tp + fn) if (tp + fn) else float("nan")
    print("\n=== Bad-document detection (blur/glare/cropped) ===")
    print(f"  TP={tp}  FP={fp}  TN={tn}  FN={fn}  (n={total})")
    print(f"  Precision={precision:.2%}  Recall={recall:.2%}")

    if mismatches:
        print("\n=== Mismatches ===")
        for m in mismatches:
            print(f"  {m['filename']}: expected={m['expected']} predicted={m['predicted']} "
                  f"reasons={m['failure_reasons']}")
    else:
        print("\nNo mismatches — all quality verdicts match ground truth.")


if __name__ == "__main__":
    main()
