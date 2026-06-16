"""TDD: boosted favicon — larger + brighter glyph, still transparent (no tab square)."""

from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.generate_favicons import (
    analyze_icon_content,
    icon_has_visible_mark,
    icon_lacks_solid_block,
    render_rgba,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = REPO_ROOT / "frontend" / "favicon-source.png"


def _glyph_bbox_span(rgba: np.ndarray) -> int:
    mask = rgba[..., 3] > 8
    if not mask.any():
        return 0
    ys, xs = np.where(mask)
    return max(int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))


def _avg_glyph_luma(rgba: np.ndarray) -> float:
    mask = rgba[..., 3] > 8
    if not mask.any():
        return 0.0
    luma = 0.299 * rgba[..., 0] + 0.587 * rgba[..., 1] + 0.114 * rgba[..., 2]
    return float(luma[mask].mean())


class FaviconBoostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not SOURCE.is_file():
            raise unittest.SkipTest("missing frontend/favicon-source.png")

    def test_rejects_synthetic_opaque_square(self):
        square = np.zeros((32, 32, 4), dtype=np.uint8)
        square[..., 3] = 255
        square[..., :3] = (235, 223, 208)
        self.assertFalse(icon_lacks_solid_block(square))

    def test_boosted_has_transparent_background_not_block(self):
        with Image.open(SOURCE) as src:
            out = render_rgba(src, 64, style="boosted")
        rgba = np.asarray(out, dtype=np.uint8)
        self.assertTrue(icon_lacks_solid_block(rgba))
        stats = analyze_icon_content(SOURCE)  # wrong - analyze output
        # analyze from array via temp - use stats pattern on saved logic
        alpha = rgba[..., 3]
        self.assertGreater(int((alpha <= 8).sum()), rgba.shape[0] * rgba.shape[1] * 0.5)

    def test_boosted_glyph_larger_than_plain(self):
        with Image.open(SOURCE) as src:
            plain = np.asarray(render_rgba(src, 64, style="plain"), dtype=np.uint8)
            boosted = np.asarray(render_rgba(src, 64, style="boosted"), dtype=np.uint8)
        plain_span = _glyph_bbox_span(plain)
        boosted_span = _glyph_bbox_span(boosted)
        plain_px = int((plain[..., 3] > 8).sum())
        boosted_px = int((boosted[..., 3] > 8).sum())
        # ponytail: 64px canvas may clip high scale factors; still visibly larger than plain.
        self.assertGreater(boosted_span, plain_span)
        self.assertGreater(boosted_px, plain_px)

    def test_boosted_glyph_is_black(self):
        with Image.open(SOURCE) as src:
            boosted = np.asarray(render_rgba(src, 64, style="boosted"), dtype=np.uint8)
        mask = boosted[..., 3] > 8
        self.assertTrue(mask.any())
        rgb = boosted[..., :3][mask]
        self.assertLessEqual(int(rgb.max()), 0)
        self.assertLess(_avg_glyph_luma(boosted), 5.0)


if __name__ == "__main__":
    unittest.main()
