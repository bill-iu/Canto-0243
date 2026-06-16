"""接縫測試：index.html 接入查詢分頁 chrome-tabs 與領域契約。"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = REPO_ROOT / "frontend" / "index.html"
LAYOUT_PATH = REPO_ROOT / "frontend" / "chrome-tabs-layout.js"
MAIN_PATH = REPO_ROOT / "main.py"
RELATION_ENTRY_PATH = REPO_ROOT / "frontend" / "relation-entry.html"

FRONTEND_ASSETS = (
    "chrome-tabs.css",
    "chrome-tabs-layout.js",
    "query-tabs.css",
    "query-tabs-state.mjs",
    "vendor/draggabilly.pkgd.min.js",
)

INDEX_REQUIRED = (
    'href="chrome-tabs.css"',
    'href="query-tabs.css"',
    'src="vendor/draggabilly.pkgd.min.js"',
    'src="chrome-tabs-layout.js"',
    'from "./query-tabs-state.mjs"',
    "SESSION_KEY",
    'id="queryChromeTabs"',
    'id="queryTabstrip"',
    "app-header--tabs",
    "view=relation",
    "openSingletonView",
    "reorderTabsByIds",
    "setupTabDrag",
    "setupDraggabilly",
    "activateTabOnPress",
    "data.gate_ready",
    'fetch("/ready"',
)

INDEX_FORBIDDEN = (
    "prototype-ribbon",
    "prototype-state-toggle",
    "prototype-query-tabs",
    "canto0243:prototype:query-tabs",
    "relation-entry.html",
    "PROTOTYPE ·",
)

RELATION_ENTRY_FORBIDDEN = (
    RELATION_ENTRY_PATH,
)

MAIN_FORBIDDEN = (
    '@app.get("/prototype")',
    "prototype/query-tabs.html",
)


class TestQueryTabsSeam(unittest.TestCase):
    def test_frontend_assets_promoted_to_root(self):
        for name in FRONTEND_ASSETS:
            path = REPO_ROOT / "frontend" / name
            with self.subTest(asset=name):
                self.assertTrue(path.is_file(), f"missing frontend/{name}")

    def test_index_html_wires_query_tabs(self):
        source = INDEX_PATH.read_text(encoding="utf-8")
        for symbol in INDEX_REQUIRED:
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)

    def test_index_html_has_no_prototype_or_relation_entry_links(self):
        source = INDEX_PATH.read_text(encoding="utf-8")
        for symbol in INDEX_FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_relation_entry_page_removed(self):
        for path in RELATION_ENTRY_FORBIDDEN:
            with self.subTest(path=str(path.relative_to(REPO_ROOT))):
                self.assertFalse(path.exists())

    def test_main_py_has_no_prototype_route(self):
        source = MAIN_PATH.read_text(encoding="utf-8")
        for symbol in MAIN_FORBIDDEN:
            with self.subTest(symbol=symbol):
                self.assertNotIn(symbol, source)

    def test_setup_draggabilly_relayouts_after_destroy(self):
        """Draggabilly.destroy() clears inline transforms; layout() must follow."""
        source = LAYOUT_PATH.read_text(encoding="utf-8")
        pattern = (
            r"(?s)"
            r"this\.draggabillies\.forEach\(\(d\) => d\.destroy\(\)\);"
            r".*?this\.layout\(\);"
            r".*?const tabEls = this\.normalTabEls"
        )
        self.assertRegex(
            source,
            pattern,
            "setupDraggabilly must call layout() after Draggabilly teardown",
        )


if __name__ == "__main__":
    unittest.main()
