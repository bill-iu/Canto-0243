"""macOS .app 簽章與 Open.command 備用入口（公開契約）。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SH = REPO_ROOT / "scripts" / "build-portable.sh"
OPEN_CMD = REPO_ROOT / "portable" / "macos" / "Open Canto-0243.command"
LAUNCHER = REPO_ROOT / "portable" / "macos" / "launcher"
GITATTR = REPO_ROOT / ".gitattributes"


class MacosAppDeliveryTests(unittest.TestCase):
    def test_build_portable_uses_deep_adhoc_codesign_on_app_bundle(self):
        source = BUILD_SH.read_text(encoding="utf-8")
        self.assertIn('codesign --deep --force --sign - "$APP_DIR"', source)
        self.assertIn("codesign --verify --deep --strict", source)

    def test_build_portable_strips_crlf_before_codesign(self):
        source = BUILD_SH.read_text(encoding="utf-8")
        self.assertIn("strip_cr", source)

    def test_macos_entry_scripts_use_lf_line_endings(self):
        for path in (LAUNCHER, OPEN_CMD):
            data = path.read_bytes()
            self.assertNotIn(b"\r\n", data, f"{path.name} must use LF, not CRLF (breaks macOS shebang)")

    def test_gitattributes_enforces_lf_on_macos_entry_files(self):
        source = GITATTR.read_text(encoding="utf-8")
        self.assertIn("portable/macos/launcher", source)
        self.assertIn("Open*.command", source)

    def test_open_command_clears_quarantine_and_launches_app(self):
        self.assertTrue(OPEN_CMD.is_file(), "missing Open Canto-0243.command")
        source = OPEN_CMD.read_text(encoding="utf-8")
        self.assertIn("xattr", source)
        self.assertIn("Canto-0243.app", source)
        self.assertIn("open ", source)

    def test_macos_tar_includes_open_command(self):
        source = BUILD_SH.read_text(encoding="utf-8")
        self.assertIn("Open Canto-0243.command", source)

    def test_build_portable_adhoc_signs_open_command(self):
        source = BUILD_SH.read_text(encoding="utf-8")
        self.assertIn('codesign --force --sign - "$OPEN_CMD_DIST"', source)


if __name__ == "__main__":
    unittest.main()
