"""ADR-0068 §13: Desktop UI strip removes PWA browser-engine dead weight."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.desktop_ui_strip import (
    UI_BASENAME_DENY,
    assert_stripped,
    strip_desktop_ui,
)


class DesktopUiStripTests(unittest.TestCase):
    def test_strips_denylist_keeps_ui_and_project_pos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ui = Path(tmp) / "dist-portable"
            ui.mkdir()
            (ui / "index.html").write_text("<html></html>\n", encoding="utf-8")
            (ui / "project-pos-index.json").write_text("{}\n", encoding="utf-8")
            (ui / "assets").mkdir()
            (ui / "assets" / "app.js").write_text("ok\n", encoding="utf-8")
            for name in sorted(UI_BASENAME_DENY):
                (ui / name).write_bytes(b"dead")

            removed = strip_desktop_ui(ui)
            self.assertEqual(set(removed), set(UI_BASENAME_DENY))
            assert_stripped(ui)

            self.assertTrue((ui / "index.html").is_file())
            self.assertTrue((ui / "project-pos-index.json").is_file())
            self.assertTrue((ui / "assets" / "app.js").is_file())
            for name in UI_BASENAME_DENY:
                self.assertFalse((ui / name).exists(), name)

    def test_assert_stripped_fails_when_leftover(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ui = Path(tmp) / "ui"
            ui.mkdir()
            (ui / "lyrics.db").write_bytes(b"x")
            with self.assertRaises(AssertionError):
                assert_stripped(ui)

    def test_does_not_touch_sibling_root_db(self) -> None:
        """Strip only walks ui_root; package-root lyrics.db is caller's job."""
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp)
            ui = pkg / "client" / "dist-portable"
            ui.mkdir(parents=True)
            (ui / "lyrics.db").write_bytes(b"ui-copy")
            root_db = pkg / "lyrics.db"
            root_db.write_bytes(b"ssot")
            strip_desktop_ui(ui)
            self.assertFalse((ui / "lyrics.db").exists())
            self.assertEqual(root_db.read_bytes(), b"ssot")


if __name__ == "__main__":
    unittest.main()
