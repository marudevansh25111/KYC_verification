"""
End-to-end evaluation of the full Verifio pipeline (Day 4 deliverable):
runs every synthetic image through Steps 2-7 and compares the final
verdict against the expected outcome per variant:

  clean    -> ACCEPT
  blurred  -> REJECT (quality)
  glare    -> REJECT (quality)
  cropped  -> REJECT (quality)
  tampered -> REJECT (tampering) — NOTE: since the tamper detector's
              recall is ~63% (see evaluate_tampering.py) and a tampered
              field's replacement value is still correctly *formatted*,
              some tampered documents will slip through to ACCEPT. This
              is a known, honestly-reported limitation, not a bug.

Usage:
    python data/evaluate_pipeline.py
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

import cv2

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "backend"))

from app.services.pipeline import run_verification  # noqa: E402

SYNTHETIC_DIR = ROOT / "synthetic"
GROUND_TRUTH = SYNTHETIC_DIR / "ground_truth.json"

EXPECTED_VERDICT = {
    "clean": "ACCEPT",
    "blurred": "REJECT",
    "glare": "REJECT",
    "cropped": "REJECT",
    "tampered": "REJECT",
}


def main():
    with open(GROUND_TRUTH) as f:
        records = json.load(f)

    per_variant = {v: Counter() for v in EXPECTED_VERDICT}
    mismatches = []
    start = time.time()

    for i, rec in enumerate(records, 1):
        img = cv2.imread(str(SYNTHETIC_DIR / rec["filename"]))
        result = run_verification(img)
        verdict = result["decision"]["verdict"]

        variant = rec["variant"]
        per_variant[variant][verdict] += 1

        expected = EXPECTED_VERDICT[variant]
        if verdict != expected and not (expected == "REJECT" and verdict == "REVIEW"):
            mismatches.append((rec["filename"], expected, verdict, result["decision"]["reasons"]))

        if i % 20 == 0 or i == len(records):
            print(f"  [{i}/{len(records)}] elapsed={time.time() - start:.1f}s")

    print(f"\n=== Verdict breakdown by variant (n={len(records)}) ===")
    for variant, counts in per_variant.items():
        total = sum(counts.values())
        breakdown = ", ".join(f"{v}={c}" for v, c in sorted(counts.items()))
        print(f"  {variant:10s} (expect {EXPECTED_VERDICT[variant]:6s}, n={total:2d}): {breakdown}")

    print(f"\n=== Hard mismatches (ACCEPT when REJECT/REVIEW expected, or vice versa) ===")
    if mismatches:
        for filename, expected, got, reasons in mismatches:
            print(f"  {filename}: expected={expected} got={got} reasons={reasons}")
    else:
        print("  none")

    print(f"\nTotal time: {time.time() - start:.1f}s ({(time.time() - start) / len(records):.2f}s/image)")


if __name__ == "__main__":
    main()
