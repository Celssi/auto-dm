"""Draw Auto-DM PWA icons from the favicon d20 motif."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "frontend" / "public" / "icons"
BG = (10, 14, 20, 255)
GOLD = (212, 175, 55, 255)
INNER = (22, 31, 46, 255)
INNER_TINT = (212, 175, 55, 38)


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/Library/Fonts/Georgia.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ):
        candidate = Path(path)
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _draw_icon(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(image)
    pad = size * 0.08
    cx = cy = size / 2
    outer = [
        (cx, pad),
        (size - pad, cy * 0.72),
        (size - pad, size - cy * 0.72),
        (cx, size - pad),
        (pad, size - cy * 0.72),
        (pad, cy * 0.72),
    ]
    inner = [
        (cx, size * 0.22),
        (size * 0.78, cy * 0.78),
        (size * 0.78, size - cy * 0.78),
        (cx, size * 0.78),
        (size * 0.22, size - cy * 0.78),
        (size * 0.22, cy * 0.78),
    ]
    draw.polygon(outer, fill=INNER, outline=GOLD)
    draw.polygon(inner, fill=INNER_TINT, outline=GOLD)
    width = max(1, round(size * 0.035))
    draw.line(outer + [outer[0]], fill=GOLD, width=width)
    font = _font(max(10, int(size * 0.28)))
    text = "20"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2, (size - th) / 2 - bbox[1] * 0.15), text, font=font, fill=GOLD)
    return image


def _maskable(icon: Image.Image, size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), BG)
    inner = int(size * 0.8)
    scaled = icon.resize((inner, inner), Image.Resampling.LANCZOS)
    offset = (size - inner) // 2
    canvas.paste(scaled, (offset, offset), scaled)
    return canvas


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    icon_192 = _draw_icon(192)
    icon_512 = _draw_icon(512)
    icon_192.save(OUT / "icon-192x192.png")
    icon_512.save(OUT / "icon-512x512.png")
    _draw_icon(180).save(OUT / "apple-touch-icon.png")
    _maskable(icon_192, 192).save(OUT / "icon-192x192-maskable.png")
    _maskable(icon_512, 512).save(OUT / "icon-512x512-maskable.png")
    print(f"Wrote PWA icons to {OUT}")


if __name__ == "__main__":
    main()
