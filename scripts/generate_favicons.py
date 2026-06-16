"""Install frontend favicon assets from a source PNG mask/icon."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend"
SOURCE_PNG = FRONTEND / "favicon-source.png"

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


def normalize_mask_png(src: Image.Image, *, alpha_threshold: int = 16) -> Image.Image:
    """Turn an alpha-mask PNG into a solid white glyph on a black square."""
    rgba = src.convert("RGBA")
    out = Image.new("RGB", rgba.size, BLACK)
    alpha = rgba.getchannel("A")
    mask = alpha.point(lambda value: 255 if value > alpha_threshold else 0)
    white_layer = Image.new("RGB", rgba.size, WHITE)
    out.paste(white_layer, mask=mask)
    return out


def render_icon(size: int, source: Image.Image) -> Image.Image:
    base = normalize_mask_png(source)
    if base.size != (size, size):
        return base.resize((size, size), Image.Resampling.LANCZOS)
    return base


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


if __name__ == "__main__":
    install_favicons()
    for name in ("favicon-32.png", "apple-touch-icon.png", "favicon.ico"):
        stats = analyze_icon_content(FRONTEND / name)
        print(name, stats, "ok" if icon_has_visible_mark(stats) else "BAD")