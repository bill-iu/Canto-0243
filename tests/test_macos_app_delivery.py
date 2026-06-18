"""macOS .app 淺簽與 Open.command 備用入口（公開契約）。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SH = REPO_ROOT / "scripts" / "build-portable.sh"
OPEN_CMD = REPO_ROOT / "portable" / "macos" / "Open Canto-0243.command"


class MacosAppDeliveryTests(unittest.TestCase):
    def test_build_portable_uses_shallow_codesign_not_deep(self):
        source = BUILD_SH.read_text(encoding="utf-8")
        self.assertIn('codesign --force --sign - "$APP_DIR/Contents/MacOS/Canto-0243"', source)
        self.assertNotIn("codesign --force --deep", source)

    def test_open_command_clears_quarantine_and_launches_app(self):
        self.assertTrue(OPEN_CMD.is_file(), "missing Open Canto-0243.command")
        source = OPEN_CMD.read_text(encoding="utf-8")
        self.assertIn("xattr", source)
        self.assertIn("Canto-0243.app", source)
        self.assertIn('open ', source)

    def test_macos_tar_includes_open_command(self):
        source = BUILD_SH.read_text(encoding="utf-8")
        self.assertIn("Open Canto-0243.command", source)


if __name__ == "__main__":
    unittest.main()
