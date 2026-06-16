"""Install frontend favicon assets from favicon-source.png (or bootstrap from raw PNG)."""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend"
SOURCE_PNG = FRONTEND / "favicon-source.png"

BLACK = (0, 0, 0)
GLYPH = (235, 223, 208)  # #EBDFD0 — matches frontend theme-color
MASTER = 512
PAD_RATIO = 0.10  # equal margin → centered in browser tab slot


def extract_mask(rgba: Image.Image, *, threshold: int = 24) -> Image.Image:
    """Binary mask from alpha and/or dark-on-black glyph."""
    rgb = rgba.convert("RGB")
    r, g, b = rgb.split()
    lum = ImageChops.lighter(ImageChops.lighter(r, g), b)
    alpha = rgba.getchannel("A")
    combined = ImageChops.lighter(lum, alpha)
    return combined.point(lambda value: 255 if value > threshold else 0)


def center_mask_on_square(mask: Image.Image, size: int, pad_ratio: float = PAD_RATIO) -> Image.Image:
    bbox = mask.getbbox()
    if not bbox:
        raise ValueError("empty glyph mask")
    cropped = mask.crop(bbox)
    inner = max(1, int(size * (1 - 2 * pad_ratio)))
    scale = min(inner / cropped.width, inner / cropped.height)
    new_w = max(1, int(cropped.width * scale))
    new_h = max(1, int(cropped.height * scale))
    resized = cropped.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (size, size), 0)
    canvas.paste(resized, ((size - new_w) // 2, (size - new_h) // 2))
    return canvas


def mask_to_rgb(mask: Image.Image, *, color: tuple[int, int, int] = GLYPH) -> Image.Image:
    out = Image.new("RGB", mask.size, BLACK)
    layer = Image.new("RGB", mask.size, color)
    out.paste(layer, mask=mask)
    return out


def render_icon(size: int, source: Image.Image) -> Image.Image:
    mask = center_mask_on_square(extract_mask(source.convert("RGBA")), MASTER)
    if size != MASTER:
        mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    return mask_to_rgb(mask)


def write_master(source_png: Path, dest: Path = SOURCE_PNG, *, size: int = MASTER) -> Path:
    with Image.open(source_png) as src:
        mask = center_mask_on_square(extract_mask(src.convert("RGBA")), size)
        master = mask_to_rgb(mask)
    dest.parent.mkdir(parents=True, exist_ok=True)
    master.save(dest, format="PNG", optimize=True)
    return dest


def install_favicons(
    source_png: Path = SOURCE_PNG,
    frontend_dir: Path = FRONTEND,
) -> None:
    if not source_png.is_file():
        raise FileNotFoundError(f"missing favicon source: {source_png}")

    with Image.open(source_png) as src:
        favicon_png = render_icon(64, src)
        apple_touch = render_icon(180, src)
        ico_16 = render_icon(16, src)
        ico_32 = render_icon(32, src)

    frontend_dir.mkdir(parents=True, exist_ok=True)
    favicon_png.save(frontend_dir / "favicon-32.png", format="PNG", optimize=True)
    apple_touch.save(frontend_dir / "apple-touch-icon.png", format="PNG", optimize=True)
    ico_32.save(
        frontend_dir / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32)],
        append_images=[ico_16],
    )


def analyze_icon_content(path: Path, *, bright_threshold: int = 200) -> dict[str, float | int]:
    with Image.open(path) as img:
        rgb = img.convert("RGB")
        pixels = list(rgb.get_flattened_data())

    luma = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in pixels]
    bright = sum(1 for value in luma if value >= bright_threshold)
    mean = sum(luma) / len(luma)
    variance = sum((value - mean) ** 2 for value in luma) / len(luma)
    return {
        "pixel_count": len(pixels),
        "bright_pixels": bright,
        "avg_luma": mean,
        "luma_std": variance**0.5,
    }


def analyze_icon_content_bytes(data: bytes, *, bright_threshold: int = 200) -> dict[str, float | int]:
    with Image.open(BytesIO(data)) as img:
        rgb = img.convert("RGB")
        pixels = list(rgb.get_flattened_data())

    luma = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in pixels]
    bright = sum(1 for value in luma if value >= bright_threshold)
    mean = sum(luma) / len(luma)
    variance = sum((value - mean) ** 2 for value in luma) / len(luma)
    return {
        "pixel_count": len(pixels),
        "bright_pixels": bright,
        "avg_luma": mean,
        "luma_std": variance**0.5,
    }


def icon_has_visible_mark(stats: dict[str, float | int]) -> bool:
    return stats["bright_pixels"] >= 48 and stats["luma_std"] >= 20.0


# Backwards-compatible aliases used by older tests/scripts.
analyze_icon_brightness = analyze_icon_content
analyze_icon_brightness_bytes = analyze_icon_content_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build frontend favicon assets from favicon-source.png")
    parser.add_argument(
        "--from",
        dest="from_path",
        type=Path,
        help="Bootstrap favicon-source.png from a raw glyph PNG (e.g. uploaded 64×64 asset)",
    )
    args = parser.parse_args(argv)

    if args.from_path:
        write_master(args.from_path)
        print(f"Wrote master {SOURCE_PNG}")

    install_favicons()
    ok = True
    for name in ("favicon-32.png", "apple-touch-icon.png", "favicon.ico"):
        stats = analyze_icon_content(FRONTEND / name)
        visible = icon_has_visible_mark(stats)
        print(name, stats, "ok" if visible else "BAD")
        ok = ok and visible
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
