"""
Synthetic ID document generator for Verifio.

Generates fake, non-branded "ID Card" style documents (NOT Aadhaar/PAN
reproductions — generic layouts inspired by the structure of Indian ID
documents, using entirely fake names/numbers) plus quality/tampering
variants, with a ground-truth manifest for evaluation.

Usage:
    python generate_synthetic_data.py
"""
import io
import json
import random
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "backend"))
from app.services.templates import CARD_W, CARD_H, HEADER_HEIGHT, TEMPLATES, FIELD_LABELS  # noqa: E402

random.seed(42)

OUT_DIR = ROOT / "synthetic"
FONT_DIR = Path("/System/Library/Fonts/Supplemental")
FONT_REGULAR = FONT_DIR / "Arial.ttf"
FONT_BOLD = FONT_DIR / "Arial Bold.ttf"

FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Ishaan", "Kabir", "Ananya", "Diya",
               "Saanvi", "Meera", "Rohan", "Kavya", "Arjun", "Neha", "Rahul", "Priya"]
LAST_NAMES = ["Sharma", "Verma", "Iyer", "Reddy", "Gupta", "Nair", "Patel",
              "Singh", "Rao", "Kulkarni", "Menon", "Chawla", "Bhatt", "Joshi"]

FIELD_LAYOUT_TYPE_A = {k: v["box"] for k, v in TEMPLATES["type_a"]["fields"].items()}
FIELD_LAYOUT_TYPE_B = {k: v["box"] for k, v in TEMPLATES["type_b"]["fields"].items()}


def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_dob():
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    year = random.randint(1965, 2005)
    return f"{day:02d}/{month:02d}/{year}"


def random_id_number(doc_type: str):
    if TEMPLATES[doc_type]["id_format"] == "pan":  # 5 letters, 4 digits, 1 letter
        letters1 = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5))
        digits = "".join(random.choices("0123456789", k=4))
        letter2 = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        return f"{letters1}{digits}{letter2}"
    else:  # Aadhaar-style: 12 digits, grouped as 4-4-4
        d = "".join(random.choices("0123456789", k=12))
        return f"{d[0:4]} {d[4:8]} {d[8:12]}"


def random_address():
    nums = random.randint(1, 999)
    streets = ["MG Road", "Park Street", "Church Road", "Station Road", "Lake View Lane"]
    cities = ["Pune", "Bengaluru", "Chennai", "Hyderabad", "Ahmedabad", "Jaipur"]
    return f"{nums}, {random.choice(streets)}, {random.choice(cities)} - {random.randint(100000, 699999)}"


@dataclass
class DocRecord:
    filename: str
    doc_type: str          # type_a (PAN-style) | type_b (Aadhaar-style)
    variant: str           # clean | blurred | glare | cropped | tampered
    expected_quality_verdict: str   # pass | fail
    expected_fields: dict
    tampered_field: str | None = None


def draw_base_card(doc_type: str, fields: dict) -> Image.Image:
    img = Image.new("RGB", (CARD_W, CARD_H), color=(245, 246, 240))
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, CARD_W, HEADER_HEIGHT], fill=TEMPLATES[doc_type]["header_color_rgb"])

    title_font = ImageFont.truetype(str(FONT_BOLD), 34)
    label_font = ImageFont.truetype(str(FONT_BOLD), 20)
    value_font = ImageFont.truetype(str(FONT_REGULAR), 26)

    draw.text((30, 15), TEMPLATES[doc_type]["title"], font=title_font, fill=(255, 255, 255))

    # photo placeholder box
    draw.rectangle([30, 100, 220, 320], outline=(120, 120, 120), width=2)
    draw.rectangle([32, 102, 218, 318], fill=(210, 210, 210))
    draw.text((70, 195), "PHOTO", font=label_font, fill=(140, 140, 140))

    layout = FIELD_LAYOUT_TYPE_A if doc_type == "type_a" else FIELD_LAYOUT_TYPE_B

    for key, (x, y, w, h) in layout.items():
        draw.text((x, y), FIELD_LABELS[key] + ":", font=label_font, fill=(90, 90, 90))
        text_y = y + 24
        text = fields[key]
        if key == "address":
            # wrap address across two lines roughly by char count
            mid = len(text) // 2
            split_at = text.find(",", mid)
            split_at = split_at if split_at != -1 else mid
            line1, line2 = text[:split_at + 1].strip(), text[split_at + 1:].strip()
            draw.text((x, text_y), line1, font=value_font, fill=(20, 20, 20))
            draw.text((x, text_y + 30), line2, font=value_font, fill=(20, 20, 20))
        else:
            draw.text((x, text_y), text, font=value_font, fill=(20, 20, 20))

    draw.rectangle([0, 0, CARD_W - 1, CARD_H - 1], outline=(60, 60, 60), width=3)
    return img, layout


def jpeg_round_trip(img: Image.Image, quality: int = 90) -> Image.Image:
    """
    Simulates the document having already been photographed/scanned and
    saved once as a JPEG. This matters for ELA-based tamper detection
    (Step 6): an *untouched* region that's been through N JPEG
    compressions has "settled" into that quantization grid, so
    recompressing it again barely changes it. A region edited AFTER this
    point (see make_tampered) is fresh pixel data compressed for the
    first time when the final file is saved, which is what makes it show
    up as a high-error blob under ELA — this wouldn't happen if we drew
    the tampered text directly onto the original uncompressed canvas.
    """
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def make_blurred(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius=8))


def make_glare(img: Image.Image) -> Image.Image:
    img = img.copy()
    overlay = Image.new("RGB", img.size, (255, 255, 255))
    mask = Image.new("L", img.size, 0)
    mdraw = ImageDraw.Draw(mask)
    cx, cy = random.randint(300, 700), random.randint(100, 400)
    mdraw.ellipse([cx - 220, cy - 160, cx + 220, cy + 160], fill=200)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=60))
    return Image.composite(overlay, img, mask)


def make_cropped(img: Image.Image) -> Image.Image:
    w, h = img.size
    crop_amount_x = int(w * 0.18)
    crop_amount_y = int(h * 0.15)
    return img.crop((crop_amount_x, crop_amount_y, w, h))


def make_tampered(img: Image.Image, layout: dict, fields: dict, doc_type: str):
    img = img.copy()
    draw = ImageDraw.Draw(img)
    tamper_field = random.choice(["name", "id_number"])
    x, y, w, h = layout[tamper_field]

    # paint over original field with background color, then re-draw with a
    # DIFFERENT font size/weight to simulate a pasted-in edit (font/layout
    # inconsistency is exactly what Step 6's authenticity check looks for)
    draw.rectangle([x, y + 20, x + w, y + 55], fill=(245, 246, 240))

    new_value = random_id_number(doc_type) if tamper_field == "id_number" else random_name()
    mismatched_font = ImageFont.truetype(str(FONT_BOLD), 30)  # different from original value_font (26, regular)
    draw.text((x, y + 22), new_value, font=mismatched_font, fill=(15, 15, 15))

    fields = dict(fields)
    fields[tamper_field] = new_value
    return img, fields, tamper_field


def generate(n_per_type: int = 12):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[DocRecord] = []
    idx = 0

    for doc_type in ["type_a", "type_b"]:
        for _ in range(n_per_type):
            fields = {
                "name": random_name(),
                "id_number": random_id_number(doc_type),
                "dob": random_dob(),
                "address": random_address(),
            }
            base_img, layout = draw_base_card(doc_type, fields)
            base_img = jpeg_round_trip(base_img)  # "settle" the compression history before branching

            variants = [
                ("clean", base_img, "pass", fields, None),
                ("blurred", make_blurred(base_img), "fail", fields, None),
                ("glare", make_glare(base_img), "fail", fields, None),
                ("cropped", make_cropped(base_img), "fail", fields, None),
            ]
            tampered_img, tampered_fields, tampered_field = make_tampered(base_img, layout, fields, doc_type)
            variants.append(("tampered", tampered_img, "pass", tampered_fields, tampered_field))

            for variant_name, vimg, quality_verdict, vfields, tampered_field_name in variants:
                idx += 1
                filename = f"{doc_type}_{idx:04d}_{variant_name}.jpg"
                vimg.convert("RGB").save(OUT_DIR / filename, quality=90)
                manifest.append(DocRecord(
                    filename=filename,
                    doc_type=doc_type,
                    variant=variant_name,
                    expected_quality_verdict=quality_verdict,
                    expected_fields=vfields,
                    tampered_field=tampered_field_name,
                ))

    manifest_path = OUT_DIR / "ground_truth.json"
    with open(manifest_path, "w") as f:
        json.dump([asdict(r) for r in manifest], f, indent=2)

    print(f"Generated {len(manifest)} images across {len({m.variant for m in manifest})} variants -> {OUT_DIR}")
    print(f"Ground truth manifest -> {manifest_path}")


if __name__ == "__main__":
    generate(n_per_type=12)
