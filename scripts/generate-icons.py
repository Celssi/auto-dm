#!/usr/bin/env python3
"""Regenerate the PWA / favicon icon set from the hedgehog source artwork.

Usage: python3 scripts/generate-icons.py  (needs Pillow)
Source: assets/brand/hedgehog-source.png (square, full-bleed cream background).

Follows the Paperi pipeline: rounded-square "any" icons (radius 0.22, transparent
corners), maskable icons with art in the central 80% on a full-bleed tile colour,
apple-touch 180px opaque, favicon.ico at 16/32/48. Favicons use a tighter crop
around the hedgehog so 16-32px sizes stay readable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "assets" / "brand" / "hedgehog-source.png"
PUBLIC = ROOT / 'frontend/public'
ICONS = PUBLIC / "icons"
APP_DIR = ROOT / "src" / "app"
ANY_SIZES = [48, 72, 96, 128, 144, 152, 192, 256, 384, 512]
MASKABLE_SIZES = [192, 512]
RADIUS = 0.22
# Optional extra copies with app-specific filenames (e.g. Libris icon-192.png).
EXTRA_ANY = []
EXTRA_MASKABLE = [(192, 'frontend/public/icons/icon-192x192-maskable.png'), (512, 'frontend/public/icons/icon-512x512-maskable.png')]
APPLE_PATHS = ['frontend/public/icons/apple-touch-icon.png']
ICO_PATHS = ['frontend/public/favicon.ico']
ICON_PNG_PATHS = []


def cream_of(img: Image.Image) -> tuple[int, int, int]:
    px = [
        img.getpixel(p)
        for p in [
            (2, 2),
            (img.width - 3, 2),
            (2, img.height - 3),
            (img.width - 3, img.height - 3),
        ]
    ]
    return tuple(sum(c[i] for c in px) // len(px) for i in range(3))


def rounded_mask(size: int, radius: int, scale: int = 4) -> Image.Image:
    big = Image.new("L", (size * scale, size * scale), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, size * scale - 1, size * scale - 1),
        radius=radius * scale,
        fill=255,
    )
    return big.resize((size, size), Image.Resampling.LANCZOS)


def down(img: Image.Image, size: int) -> Image.Image:
    out = img.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 64:
        out = out.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60, threshold=1))
    return out


def save(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".ico":
        return
    img.save(path, format="PNG", optimize=True)


def content_bbox(opaque: Image.Image, cream: tuple[int, int, int], thresh: int = 40):
    arr = np.array(opaque.convert("RGB")).astype("int16")

    diff = abs(arr - np.array(cream, dtype="int16")).sum(axis=2)
    ys, xs = np.where(diff > thresh)
    pad = 8
    l = max(0, int(xs.min()) - pad)
    t = max(0, int(ys.min()) - pad)
    r = min(opaque.size[0], int(xs.max()) + 1 + pad)
    b = min(opaque.size[1], int(ys.max()) + 1 + pad)
    return l, t, r, b


def square_crop(img: Image.Image, bbox) -> Image.Image:
    l, t, r, b = bbox
    side = max(r - l, b - t)
    cx = (l + r) / 2
    cy = (t + b) / 2 - side * 0.04
    l2 = int(round(cx - side / 2))
    t2 = int(round(cy - side / 2))
    r2 = l2 + side
    b2 = t2 + side
    if l2 < 0:
        r2 -= l2
        l2 = 0
    if t2 < 0:
        b2 -= t2
        t2 = 0
    if r2 > img.width:
        l2 -= r2 - img.width
        r2 = img.width
    if b2 > img.height:
        t2 -= b2 - img.height
        b2 = img.height
    return img.crop((max(0, l2), max(0, t2), r2, b2))


def main() -> None:
    src = Image.open(SOURCE).convert("RGB")
    s = min(src.size)
    src = src.crop(((src.width - s) // 2, (src.height - s) // 2, (src.width + s) // 2, (src.height + s) // 2))
    if s != 1024:
        src = src.resize((1024, 1024), Image.Resampling.LANCZOS)
    cream = cream_of(src)
    opaque = src.convert("RGBA")
    rounded = opaque.copy()
    rounded.putalpha(rounded_mask(rounded.width, int(rounded.width * RADIUS)))

    ICONS.mkdir(parents=True, exist_ok=True)
    for n in ANY_SIZES:
        save(down(rounded, n), ICONS / f"icon-{n}x{n}.png")
    for n, dest in EXTRA_ANY:
        save(down(rounded, n), Path(dest) if Path(dest).is_absolute() else ROOT / dest)
    for n in MASKABLE_SIZES:
        canvas = Image.new("RGBA", (n, n), cream + (255,))
        art = int(n * 0.8)
        canvas.alpha_composite(down(opaque, art), ((n - art) // 2, (n - art) // 2))
        save(canvas, ICONS / f"maskable-{n}x{n}.png")
    for n, dest in EXTRA_MASKABLE:
        canvas = Image.new("RGBA", (n, n), cream + (255,))
        art = int(n * 0.8)
        canvas.alpha_composite(down(opaque, art), ((n - art) // 2, (n - art) // 2))
        p = Path(dest) if Path(dest).is_absolute() else ROOT / dest
        save(canvas, p)

    bbox = content_bbox(src, cream)
    tight = square_crop(src, bbox).convert("RGBA")
    tight.putalpha(rounded_mask(tight.width, int(tight.width * RADIUS)))
    for n in (16, 32):
        save(down(tight, n), ICONS / f"favicon-{n}x{n}.png")
    # Common aliases used by layout metadata
    save(down(tight, 16), ICONS / "icon-16x16.png")
    save(down(tight, 32), ICONS / "icon-32x32.png")

    apple = down(src, 180).convert("RGB")
    for dest in APPLE_PATHS:
        p = ROOT / dest
        p.parent.mkdir(parents=True, exist_ok=True)
        apple.save(p, format="PNG", optimize=True)

    ico = down(tight, 256)
    for dest in ICO_PATHS:
        p = ROOT / dest
        p.parent.mkdir(parents=True, exist_ok=True)
        ico.save(p, format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])

    icon_png = down(rounded, 512)
    for dest in ICON_PNG_PATHS:
        p = ROOT / dest
        p.parent.mkdir(parents=True, exist_ok=True)
        icon_png.save(p, format="PNG", optimize=True)

    print("cream", "#%02x%02x%02x" % cream)


if __name__ == "__main__":
    main()
