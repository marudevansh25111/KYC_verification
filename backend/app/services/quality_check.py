"""
Step 3 of the Verifio pipeline: image quality checks that run BEFORE OCR.

Each check is independent, rule-based, and returns a small dict with the
raw measurement plus a pass/fail so the decision engine (Step 7) can weigh
them individually rather than getting a single opaque boolean.

Thresholds below were tuned against data/synthetic/ (see
data/evaluate_quality_checks.py) — they are deliberately simple,
explainable rules rather than a learned model, per the project's
validation-logic philosophy.
"""
from dataclasses import dataclass, field

import cv2
import numpy as np

BLUR_VARIANCE_THRESHOLD = 120.0
GLARE_BRIGHT_PIXEL_RATIO_THRESHOLD = 0.05
GLARE_BRIGHTNESS_LEVEL = 250
MIN_WIDTH = 600
MIN_HEIGHT = 400
BORDER_STRIP_PX = 6
BORDER_DARKNESS_LEVEL = 100
MIN_BORDER_DARK_FRACTION = 0.5


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: dict = field(default_factory=dict)


def check_resolution(gray: np.ndarray) -> CheckResult:
    h, w = gray.shape[:2]
    passed = w >= MIN_WIDTH and h >= MIN_HEIGHT
    return CheckResult("resolution", passed, {"width": w, "height": h,
                                               "min_width": MIN_WIDTH, "min_height": MIN_HEIGHT})


def check_blur(gray: np.ndarray) -> CheckResult:
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    passed = variance >= BLUR_VARIANCE_THRESHOLD
    return CheckResult("blur", passed, {"laplacian_variance": round(float(variance), 2),
                                         "threshold": BLUR_VARIANCE_THRESHOLD})


def check_glare(gray: np.ndarray) -> CheckResult:
    bright_ratio = float(np.mean(gray >= GLARE_BRIGHTNESS_LEVEL))
    passed = bright_ratio < GLARE_BRIGHT_PIXEL_RATIO_THRESHOLD
    return CheckResult("glare", passed, {"bright_pixel_ratio": round(bright_ratio, 4),
                                          "threshold": GLARE_BRIGHT_PIXEL_RATIO_THRESHOLD})


def check_completeness(gray: np.ndarray) -> CheckResult:
    """
    Confirms the document's printed border frame is visible along all four
    edges of the image. If the camera/scan cut off part of the document,
    the border along that side will be missing (replaced by interior
    content instead of the dark frame line), which this detects.
    """
    h, w = gray.shape[:2]
    s = BORDER_STRIP_PX

    def dark_fraction(strip: np.ndarray) -> float:
        return float(np.mean(strip < BORDER_DARKNESS_LEVEL))

    edge_fractions = {
        "top": dark_fraction(gray[0:s, :]),
        "bottom": dark_fraction(gray[h - s:h, :]),
        "left": dark_fraction(gray[:, 0:s]),
        "right": dark_fraction(gray[:, w - s:w]),
    }
    missing_edges = [edge for edge, frac in edge_fractions.items() if frac < MIN_BORDER_DARK_FRACTION]
    passed = len(missing_edges) == 0
    return CheckResult("completeness", passed, {
        "edge_dark_fraction": {k: round(v, 3) for k, v in edge_fractions.items()},
        "missing_edges": missing_edges,
    })


def run_quality_checks(image_bgr: np.ndarray) -> dict:
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    checks = [
        check_resolution(gray),
        check_blur(gray),
        check_glare(gray),
        check_completeness(gray),
    ]

    failed = [c for c in checks if not c.passed]
    overall_passed = len(failed) == 0

    return {
        "passed": overall_passed,
        "checks": {c.name: {"passed": c.passed, **c.details} for c in checks},
        "failure_reasons": [c.name for c in failed],
    }
