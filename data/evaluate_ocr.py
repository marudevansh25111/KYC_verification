"""
Evaluates OCR field extraction + validation against ground truth (Day 3
deliverable). Only runs on 'clean' and 'tampered' variants — in the real
pipeline, blurred/glare/cropped documents are already rejected by the
Step 3 quality gate and never reach OCR.

Usage:
    python data/evaluate_ocr.py [--limit N]
"""
import argparse
import difflib
import json
import re
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "backend"))

from app.services.ocr_extraction import extract_fields  # noqa: E402
from app.services.field_validation import validate_fields  # noqa: E402

SYNTHETIC_DIR = ROOT / "synthetic"
GROUND_TRUTH = SYNTHETIC_DIR / "ground_truth.json"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="only evaluate first N eligible images")
    args = parser.parse_args()

    with open(GROUND_TRUTH) as f:
        records = json.load(f)

    eligible = [r for r in records if r["variant"] in ("clean", "tampered")]
    if args.limit:
        eligible = eligible[: args.limit]

    field_similarity_sum = {"name": 0.0, "id_number": 0.0, "dob": 0.0, "address": 0.0}
    field_exact_count = {"name": 0, "id_number": 0, "dob": 0, "address": 0}
    n = len(eligible)

    print(f"Running OCR on {n} images (clean + tampered)...")
    start = time.time()

    for i, rec in enumerate(eligible, 1):
        img = cv2.imread(str(SYNTHETIC_DIR / rec["filename"]))
        extracted = extract_fields(img, rec["doc_type"])
        validated = validate_fields(extracted, rec["doc_type"])

        for field_name, expected_value in rec["expected_fields"].items():
            got = validated[field_name]["text"]
            sim = similarity(got, expected_value)
            field_similarity_sum[field_name] += sim
            if normalize(got) == normalize(expected_value):
                field_exact_count[field_name] += 1

        if i % 10 == 0 or i == n:
            print(f"  [{i}/{n}] elapsed={time.time() - start:.1f}s")

    print("\n=== Field extraction accuracy (clean + tampered, n={}) ===".format(n))
    for field_name in field_similarity_sum:
        avg_sim = field_similarity_sum[field_name] / n
        exact_pct = field_exact_count[field_name] / n * 100
        print(f"  {field_name:10s}: avg_similarity={avg_sim:.3f}  exact_match={exact_pct:.1f}%")

    overall_avg = sum(field_similarity_sum.values()) / (n * len(field_similarity_sum))
    print(f"\nOverall average similarity: {overall_avg:.3f}")
    print(f"Total time: {time.time() - start:.1f}s ({(time.time() - start) / n:.2f}s/image)")


if __name__ == "__main__":
    main()
