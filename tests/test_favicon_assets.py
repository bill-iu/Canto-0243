"""Regression: favicon assets must show a visible mark, not a blank black square."""

from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from scripts.generate_favicons import (
    analyze_icon_content,
    analyze_icon_content_bytes,
    icon_has_visible_mark,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "frontend"

ICON_FILES = (
    "favicon-32.png",
    "apple-touch-icon.png",
    "favicon.ico",
)


class FaviconAssetTests(unittest.TestCase):
    def test_icon_files_exist(self):
        for name in ICON_FILES:
            with self.subTest(name=name):
                self.assertTrue((FRONTEND / name).is_file(), f"missing frontend/{name}")

    def test_icons_show_visible_mark(self):
        for name in ICON_FILES:
            with self.subTest(name=name):
                stats = analyze_icon_content(FRONTEND / name)
                self.assertTrue(icon_has_visible_mark(stats), stats)

    def test_http_serves_visible_favicon(self):
        client = TestClient(app)
        for path in ("/favicon.ico", "/frontend/favicon-32.png", "/frontend/apple-touch-icon.png"):
            with self.subTest(path=path):
                response = client.get(path)
                self.assertEqual(response.status_code, 200, response.text)
                stats = analyze_icon_content_bytes(response.content)
                self.assertTrue(icon_has_visible_mark(stats), stats)


if __name__ == "__main__":
    unittest.main()