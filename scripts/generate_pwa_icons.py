#!/usr/bin/env python3
"""Regenerate PWA / favicon assets from assets/brand/hedgehog.svg (needs cairosvg + Pillow)."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
# Auto-DM keeps the script at repo/scripts but public/ is frontend/public
if (ROOT / "frontend" / "public").is_dir() and not (ROOT / "public").is_dir():
    PUBLIC = ROOT / "frontend" / "public"
    APP_ICON = None
elif (ROOT / "frontend" / "public").is_dir() and (ROOT / "scripts").is_dir() and Path(__file__).resolve().parent.parent.name != "frontend":
    PUBLIC = ROOT / "frontend" / "public"
    APP_ICON = None
else:
    PUBLIC = ROOT / "public"
    APP_ICON = ROOT / "src" / "app" if (ROOT / "src" / "app").is_dir() else None

SOURCE = ROOT / "assets" / "brand" / "hedgehog.svg"
ICONS = PUBLIC / "icons"
CREAM = (250, 246, 238, 255)
RADIUS = 0.22
ANY_SIZES = [48, 72, 96, 128, 144, 152, 180, 192, 256, 384, 512]
MASKABLE_SIZES = [192, 512]
MASTER = 1024


def rounded_mask(size: int, radius: int, scale: int = 4) -> Image.Image:
    big = Image.new("L", (size * scale, size * scale), 0)
    ImageDraw.Draw(big).rounded_rectangle(
        (0, 0, size * scale - 1, size * scale - 1), radius=radius * scale, fill=255
    )
    return big.resize((size, size), Image.Resampling.LANCZOS)


def down(img: Image.Image, size: int) -> Image.Image:
    out = img.resize((size, size), Image.Resampling.LANCZOS)
    if size <= 64:
        out = out.filter(ImageFilter.UnsharpMask(radius=0.6, percent=60, threshold=1))
    return out


def save(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


def main() -> None:
    if not SOURCE.is_file():
        sys.exit(f"Missing {SOURCE}")
    raw = cairosvg.svg2png(url=str(SOURCE), output_width=MASTER, output_height=MASTER)
    master = Image.open(io.BytesIO(raw)).convert("RGBA")
    opaque = Image.new("RGBA", master.size, CREAM)
    opaque.alpha_composite(master)
    rounded = opaque.copy()
    rounded.putalpha(rounded_mask(rounded.width, int(rounded.width * RADIUS)))

    ICONS.mkdir(parents=True, exist_ok=True)
    for n in ANY_SIZES:
        save(down(rounded, n), ICONS / f"icon-{n}x{n}.png")
    auto_dm = PUBLIC.as_posix().endswith("frontend/public")
    for n in MASKABLE_SIZES:
        canvas = Image.new("RGBA", (n, n), CREAM)
        art = int(n * 0.8)
        canvas.alpha_composite(down(opaque, art), ((n - art) // 2, (n - art) // 2))
        name = f"icon-{n}x{n}-maskable.png" if auto_dm else f"maskable-{n}x{n}.png"
        save(canvas, ICONS / name)
    for n in (16, 32):
        save(down(rounded, n), ICONS / f"favicon-{n}x{n}.png")
        if (ICONS / f"icon-{n}x{n}.png").exists() or n in (16, 32):
            save(down(rounded, n), ICONS / f"icon-{n}x{n}.png")

    save(down(opaque, 180).convert("RGB"), PUBLIC / "apple-touch-icon.png")
    save(down(opaque, 180).convert("RGB"), ICONS / "apple-touch-icon.png")
    PUBLIC.joinpath("icon.svg").write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    down(rounded, 256).save(PUBLIC / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    if auto_dm:
        PUBLIC.joinpath("favicon.svg").write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    if APP_ICON and APP_ICON.is_dir():
        save(down(opaque, 180).convert("RGB"), APP_ICON / "apple-icon.png")
        down(rounded, 256).save(APP_ICON / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])
        APP_ICON.joinpath("icon.svg").write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Wrote icons from {SOURCE} to {PUBLIC}")


if __name__ == "__main__":
    main()
