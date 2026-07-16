"""Smoke: local_launch ensures product UI before start."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.local_launch import APP_UI_INDEX, app_ui_ready, ensure_app_ui


class LocalLaunchAppUiTests(unittest.TestCase):
    def test_app_ui_ready_false_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertFalse(app_ui_ready(root))

    def test_app_ui_ready_true_when_index_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            idx = root / APP_UI_INDEX
            idx.parent.mkdir(parents=True)
            idx.write_text("<!doctype html><title>ok</title>", encoding="utf-8")
            self.assertTrue(app_ui_ready(root))

    def test_ensure_app_ui_noop_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            idx = root / APP_UI_INDEX
            idx.parent.mkdir(parents=True)
            idx.write_text("<!doctype html>", encoding="utf-8")
            ensure_app_ui(root, silent=True)

    def test_ensure_app_ui_exits_when_missing_and_no_npm_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(SystemExit) as ctx:
                ensure_app_ui(root, lang="en", silent=True)
            self.assertIn("dist-portable", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
