#!/usr/bin/env python3
"""
Create watermarked copies of every image in Originals/ and save them to Watermarked/.

Usage (run from anywhere):
    python scripts/watermark.py            # process every image in Originals/
    python scripts/watermark.py Image3_watermark.png Image9_watermark.png   # only these
    python scripts/watermark.py --opacity 0.14 --angle -20   # try a different look

Requires Pillow and numpy:  pip install Pillow numpy

The look is controlled by the SETTINGS block below (or the command-line flags).
Originals are never modified. Output keeps the same file name and format.
"""

import argparse
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

# ----------------------------------------------------------------------------
# SETTINGS - edit these to change the look of the watermark
# ----------------------------------------------------------------------------
TEXT = "\u00a9 bernardozamora.com"
OPACITY = 0.06          # 0.0 (invisible) .. 1.0 (solid). ~0.06 barely there, ~0.16 moderate
ANGLE = 28              # degrees, counter-clockwise tilt of the text rows
FONT_SIZE_RATIO = 0.032 # text height as a fraction of the image's shorter side
SPACING_X = 1.9         # gap between repeats along a row, as a multiple of the text width
SPACING_Y = 3.2         # gap between rows, as a multiple of the text height
# The mark adapts to the image: white over dark areas, black over light areas, and its
# strength is scaled so it looks about equally visible everywhere.
LIGHT = (255, 255, 255)
DARK = (0, 0, 0)
# Images where the mark still looked too strong. Their opacity is multiplied by
# LOWER_FACTOR (0.55 = about half as strong). Add or remove image numbers freely;
# for finer control use per-image factors in IMAGE_FACTORS, e.g. {3: 0.4}.
LOWER_FACTOR = 0.55
LOWER_IMAGES = {30, 3, 25, 8, 5, 24, 36, 13, 35, 18, 17, 19, 22, 31, 37, 33}
# Images that need a stronger mark: opacity is multiplied by HIGHER_FACTOR (1.5 = 50% stronger).
HIGHER_FACTOR = 1.5
HIGHER_IMAGES = {40, 28}
# Per-image multipliers keyed by image number; these win over the groups above.
IMAGE_FACTORS = {
    # already in LOWER_IMAGES (0.55), reduced further
    22: 0.4, 19: 0.4, 18: 0.4, 13: 0.4, 24: 0.4, 8: 0.4, 25: 0.4,
    # newly reduced
    21: 0.55, 14: 0.55,
    # Image40 was 1.5, reduced
    40: 1.15,
    # increased
    2: 1.4,
}
LOCAL_BLUR_RATIO = 1.0  # how widely brightness is averaged, as a multiple of the font size
MAX_BOOST = 1.0         # >1.0 raises opacity over mid-tone areas (1.0 = off; 1.3 = stronger there)

# Fonts tried in order; first one found is used. Add your own path at the top.
FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
# ----------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "Originals"
OUT_DIR = ROOT / "Watermarked"
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def load_font(size):
    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    print("warning: no TrueType font found, falling back to tiny default font", file=sys.stderr)
    return ImageFont.load_default()


def build_mask(width, height, args):
    """Return an 'L' mask (same size as the image) holding the tiled, rotated text."""
    font_size = max(12, round(min(width, height) * FONT_SIZE_RATIO))
    font = load_font(font_size)

    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), args.text, font=font)
    text_w, text_h = right - left, bottom - top

    # Draw on a square canvas big enough that rotating it still covers the image.
    side = math.ceil(math.hypot(width, height)) + 2 * text_w
    canvas = Image.new("L", (side, side), 0)
    draw = ImageDraw.Draw(canvas)

    step_x = text_w * SPACING_X
    step_y = text_h * SPACING_Y
    row = 0
    y = 0.0
    while y < side:
        # Offset every other row by half a step so the pattern is staggered.
        x = -step_x + (step_x / 2 if row % 2 else 0)
        while x < side:
            draw.text((x - left, y - top), args.text, fill=255, font=font)
            x += step_x
        y += step_y
        row += 1

    canvas = canvas.rotate(args.angle, resample=Image.BICUBIC)
    cx, cy = side // 2, side // 2
    box = (cx - width // 2, cy - height // 2, cx - width // 2 + width, cy - height // 2 + height)
    return canvas.crop(box), font_size


def opacity_for(path, args):
    """Base opacity, adjusted for images listed in IMAGE_FACTORS / LOWER_IMAGES / HIGHER_IMAGES."""
    match = re.match(r"Image(\d+)(?:_|$)", path.stem)
    number = int(match.group(1)) if match else None
    if number in IMAGE_FACTORS:
        return args.opacity * IMAGE_FACTORS[number]
    if number in LOWER_IMAGES:
        return args.opacity * LOWER_FACTOR
    if number in HIGHER_IMAGES:
        return args.opacity * HIGHER_FACTOR
    return args.opacity


def watermark(path, args):
    img = Image.open(path)
    has_alpha = img.mode in ("RGBA", "LA") or "transparency" in img.info
    base = img.convert("RGBA")
    width, height = base.size

    mask, font_size = build_mask(width, height, args)

    # Local brightness (0..1), blurred so a letter is never split between two tones.
    luma = base.convert("L").filter(ImageFilter.GaussianBlur(font_size * LOCAL_BLUR_RATIO))
    lum = np.asarray(luma, dtype=np.float32) / 255.0

    use_light = lum < 0.5
    # Contrast available between the background and the chosen tone (0.5 .. 1.0).
    delta = np.where(use_light, lum_to_delta_light(lum), lum_to_delta_dark(lum))
    boost = np.minimum(0.95 / np.maximum(delta, 0.05), MAX_BOOST)

    alpha = (np.asarray(mask, dtype=np.float32) / 255.0) * opacity_for(path, args) * boost
    alpha = np.clip(alpha, 0.0, 1.0)[..., None]

    tone = np.where(use_light[..., None], np.array(LIGHT, np.float32), np.array(DARK, np.float32))
    rgb = np.asarray(base.convert("RGB"), dtype=np.float32)
    blended = rgb * (1.0 - alpha) + tone * alpha

    out = Image.fromarray(np.rint(blended).astype(np.uint8), "RGB").convert("RGBA")
    out.putalpha(base.getchannel("A"))
    return out if has_alpha else out.convert("RGB")


def lum_to_delta_light(lum):
    """Contrast of a white mark over a background of brightness `lum`."""
    return 1.0 - lum


def lum_to_delta_dark(lum):
    """Contrast of a black mark over a background of brightness `lum`."""
    return lum


def main():
    parser = argparse.ArgumentParser(description="Watermark images from Originals/ into Watermarked/.")
    parser.add_argument("files", nargs="*", help="file names inside Originals/ (default: all images)")
    parser.add_argument("--text", default=TEXT)
    parser.add_argument("--opacity", type=float, default=OPACITY)
    parser.add_argument("--angle", type=float, default=ANGLE)
    args = parser.parse_args()

    if not SRC_DIR.is_dir():
        sys.exit(f"Source folder not found: {SRC_DIR}")
    OUT_DIR.mkdir(exist_ok=True)

    if args.files:
        sources = [SRC_DIR / name for name in args.files]
    else:
        sources = sorted(p for p in SRC_DIR.iterdir() if p.suffix.lower() in EXTENSIONS)

    if not sources:
        sys.exit(f"No images found in {SRC_DIR}")

    for src in sources:
        if not src.is_file():
            print(f"skip (not found): {src.name}")
            continue
        dest = OUT_DIR / src.name
        result = watermark(src, args)
        if src.suffix.lower() in (".jpg", ".jpeg"):
            result.save(dest, quality=92, optimize=True)
        else:
            result.save(dest, optimize=True)
        print(f"ok: {src.name}")

    print(f"Done. {len(sources)} file(s) written to {OUT_DIR}")


if __name__ == "__main__":
    main()
