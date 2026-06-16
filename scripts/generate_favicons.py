"""Install frontend favicon assets from favicon-source.png (or bootstrap from raw PNG)."""

from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend"
SOURCE_PNG = FRONTEND / "favicon-source.png"

MASTER = 512
BASE = 64
GLYPH_SCALE = 1.30
GLYPH_COLOR = (0, 0, 0)
DEFAULT_STYLE = "boosted"


def scale_glyph_centered(rgba: Image.Image, scale: float) -> Image.Image:
    rgba = rgba.convert("RGBA")
    w, h = rgba.size
    nw = max(1, round(w * scale))
    nh = max(1, round(h * scale))
    scaled = rgba.resize((nw, nh), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(scaled, ((w - nw) // 2, (h - nh) // 2), scaled)
    return canvas


def recolor_glyph(
    rgba: Image.Image,
    *,
    color: tuple[int, int, int] = GLYPH_COLOR,
) -> Image.Image:
    arr = np.asarray(rgba.convert("RGBA"), dtype=np.uint8).copy()
    mask = arr[..., 3] > 8
    for i, component in enumerate(color):
        arr[..., i][mask] = component
    return Image.fromarray(arr, mode="RGBA")


def render_rgba(source: Image.Image, size: int, *, style: str = "plain") -> Image.Image:
    """Resize RGBA master; optional boosted = +30% scale + black glyph."""
    rgba = source.convert("RGBA")
    if rgba.size != (size, size):
        rgba = rgba.resize((size, size), Image.Resampling.LANCZOS)
    if style == "boosted":
        rgba = scale_glyph_centered(rgba, GLYPH_SCALE)
        rgba = recolor_glyph(rgba)
    return rgba


def write_master(source_png: Path, dest: Path = SOURCE_PNG, *, size: int = MASTER) -> Path:
    with Image.open(source_png) as src:
        master = render_rgba(src, size, style="plain")
    dest.parent.mkdir(parents=True, exist_ok=True)
    master.save(dest, format="PNG", optimize=True)
    return dest


def install_favicons(
    source_png: Path = SOURCE_PNG,
    frontend_dir: Path = FRONTEND,
    *,
    style: str = DEFAULT_STYLE,
) -> None:
    if not source_png.is_file():
        raise FileNotFoundError(f"missing favicon source: {source_png}")

    with Image.open(source_png) as src:
        favicon_png = render_rgba(src, BASE, style=style)
        apple_touch = render_rgba(src, 180, style=style)
        ico_16 = render_rgba(src, 16, style=style)
        ico_32 = render_rgba(src, 32, style=style)

    frontend_dir.mkdir(parents=True, exist_ok=True)
    favicon_png.save(frontend_dir / "favicon-32.png", format="PNG", optimize=True)
    apple_touch.save(frontend_dir / "apple-touch-icon.png", format="PNG", optimize=True)
    ico_32.save(
        frontend_dir / "favicon.ico",
        format="ICO",
        sizes=[(32, 32), (16, 16)],
        append_images=[ico_16],
    )


def mask_iou(reference: Image.Image, candidate: Image.Image, *, threshold: int = 15) -> float:
    """Compare glyph silhouettes via alpha / luma masks."""
    ref = np.asarray(reference.convert("RGBA"), dtype=np.float32)
    cand = np.asarray(candidate.convert("RGBA"), dtype=np.float32)
    if ref.shape[:2] != cand.shape[:2]:
        cand_img = Image.fromarray(cand.astype(np.uint8), "RGBA").resize(
            (ref.shape[1], ref.shape[0]), Image.Resampling.LANCZOS
        )
        cand = np.asarray(cand_img, dtype=np.float32)
    ref_mask = (ref[..., 3] > 8) | (ref[..., :3].max(axis=2) > threshold)
    cand_mask = (cand[..., 3] > 8) | (cand[..., :3].max(axis=2) > threshold)
    inter = (ref_mask & cand_mask).sum()
    union = (ref_mask | cand_mask).sum()
    return float(inter / union) if union else 0.0


def icon_lacks_solid_block(rgba: np.ndarray) -> bool:
    """False when favicon would render as a solid tab square (opaque bg block)."""
    alpha = rgba[..., 3]
    pixels = alpha.size
    if int((alpha <= 8).sum()) < pixels * 0.5:
        return False
    h, w = alpha.shape
    corners = (alpha[0, 0], alpha[0, w - 1], alpha[h - 1, 0], alpha[h - 1, w - 1])
    if sum(int(c) > 200 for c in corners) >= 2:
        return False
    return (alpha > 200).sum() / pixels <= 0.85


def _rgba_stats(rgba: np.ndarray) -> dict[str, float | int | bool]:
    alpha = rgba[..., 3]
    luma = 0.299 * rgba[..., 0] + 0.587 * rgba[..., 1] + 0.114 * rgba[..., 2]
    glyph = alpha > 8
    transparent = alpha <= 8
    return {
        "pixel_count": int(alpha.size),
        "transparent_pixels": int(transparent.sum()),
        "glyph_pixels": int(glyph.sum()),
        "avg_glyph_luma": float(luma[glyph].mean()) if glyph.any() else 0.0,
        "alpha_std": float(alpha.std()),
        "lacks_solid_block": icon_lacks_solid_block(rgba),
    }


def analyze_icon_content(path: Path) -> dict[str, float | int | bool]:
    with Image.open(path) as img:
        if img.format == "ICO":
            img.seek(0)
        rgba = np.asarray(img.convert("RGBA"), dtype=np.uint8)
    return _rgba_stats(rgba)


def analyze_icon_content_bytes(data: bytes) -> dict[str, float | int | bool]:
    with Image.open(BytesIO(data)) as img:
        if img.format == "ICO":
            img.seek(0)
        rgba = np.asarray(img.convert("RGBA"), dtype=np.uint8)
    return _rgba_stats(rgba)


def icon_has_visible_mark(stats: dict[str, float | int | bool]) -> bool:
    """Transparent favicon: glyph present, background mostly clear, no solid block."""
    pixels = int(stats["pixel_count"])
    return (
        stats["glyph_pixels"] >= 48
        and stats["transparent_pixels"] >= pixels * 0.5
        and stats["alpha_std"] >= 20.0
        and stats.get("lacks_solid_block", True)
    )


# Backwards-compatible aliases used by older tests/scripts.
analyze_icon_brightness = analyze_icon_content
analyze_icon_brightness_bytes = analyze_icon_content_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build frontend favicon assets from favicon-source.png")
    parser.add_argument(
        "--from",
        dest="from_path",
        type=Path,
        help="Bootstrap favicon-source.png from a raw transparent glyph PNG",
    )
    parser.add_argument(
        "--style",
        choices=("plain", "boosted"),
        default=DEFAULT_STYLE,
        help="plain = source colors; boosted = +30%% scale + black glyph",
    )
    args = parser.parse_args(argv)

    if args.from_path:
        write_master(args.from_path)
        print(f"Wrote master {SOURCE_PNG}")

    install_favicons(style=args.style)

    if args.from_path:
        with Image.open(args.from_path) as raw, Image.open(FRONTEND / "favicon-32.png") as out:
            iou = mask_iou(raw, out)
            print(f"shape IoU vs source @64: {iou:.3f}")

    ok = True
    for name in ("favicon-32.png", "apple-touch-icon.png", "favicon.ico"):
        stats = analyze_icon_content(FRONTEND / name)
        visible = icon_has_visible_mark(stats)
        print(name, stats, "ok" if visible else "BAD")
        ok = ok and visible
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
