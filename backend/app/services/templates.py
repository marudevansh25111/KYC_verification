"""
Single source of truth for the synthetic document layouts: field
bounding boxes on the CARD_W x CARD_H canvas. Used by both the synthetic
data generator (data/generate_synthetic_data.py) and the OCR field
extractor (Step 4) so the two never drift apart.

Each field box is (x, y, w, h) for the LABEL + VALUE block as drawn;
`value_offset_y` is how far below the box's top the actual value text
starts (skipping the label line), used to crop just the value for OCR.
"""

CARD_W, CARD_H = 900, 570
HEADER_HEIGHT = 70

LABEL_VALUE_OFFSET_Y = 24
ADDRESS_LINE_HEIGHT = 30

TEMPLATES = {
    "type_a": {
        "title": "PERMANENT ID CARD",
        "id_format": "pan",  # 5 letters + 4 digits + 1 letter
        "header_color_rgb": (20, 70, 140),
        "fields": {
            "name": {"box": (260, 90, 560, 45)},
            "id_number": {"box": (260, 160, 560, 45)},
            "dob": {"box": (260, 230, 300, 40)},
            "address": {"box": (260, 290, 560, 90)},
        },
    },
    "type_b": {
        "title": "RESIDENT ID CARD",
        "id_format": "aadhaar",  # 12 digits grouped 4-4-4
        "header_color_rgb": (30, 110, 60),
        "fields": {
            "name": {"box": (240, 100, 580, 45)},
            "dob": {"box": (240, 155, 300, 40)},
            # address wraps to 2 lines when rendered — box must be tall enough
            # (90px, matching type_a) or the OCR crop below will cut line 2 off.
            "address": {"box": (240, 205, 580, 90)},
            "id_number": {"box": (240, 305, 400, 45)},
        },
    },
}

FIELD_LABELS = {"name": "Name", "id_number": "ID Number", "dob": "Date of Birth", "address": "Address"}


def value_crop_box(field_box: tuple[int, int, int, int], field_name: str) -> tuple[int, int, int, int]:
    """Returns (x1, y1, x2, y2) covering just the value text, skipping the label line."""
    x, y, w, h = field_box
    y1 = y + LABEL_VALUE_OFFSET_Y - 6
    y2 = y + h if field_name == "address" else y1 + 40
    return (max(x - 4, 0), max(y1, 0), x + w, y2)
