"""macOS Canto-0243.command 交付契約（公開）。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SH = REPO_ROOT / "scripts" / "build-portable.sh"
MAC_CMD = REPO_ROOT / "portable" / "macos" / "Canto-0243.command"
GITATTR = REPO_ROOT / ".gitattributes"


class MacosAppDeliveryTests(unittest.TestCase):
    def test_build_portable_strips_crlf_on_command(self):
        source = BUILD_SH.read_text(encoding="utf-8")
        self.assertIn("strip_cr", source)

    def test_macos_entry_scripts_use_lf_line_endings(self):
        data = MAC_CMD.read_bytes()
        self.assertNotIn(b"\r\n", data, f"{MAC_CMD.name} must use LF, not CRLF (breaks macOS shebang)")

    def test_gitattributes_enforces_lf_on_macos_command(self):
        source = GITATTR.read_text(encoding="utf-8")
        self.assertIn("Canto-0243.command", source)

    def test_mac_command_clears_quarantine_and_starts(self):
        self.assertTrue(MAC_CMD.is_file(), "missing Canto-0243.command")
        source = MAC_CMD.read_text(encoding="utf-8")
        self.assertIn("xattr -cr", source)
        self.assertIn("START.sh", source)

    def test_start_sh_sets_pythonhome_on_darwin(self):
        start = REPO_ROOT / "portable" / "START.sh"
        source = start.read_text(encoding="utf-8")
        self.assertIn('PYTHONHOME="$ROOT/venv"', source)
        self.assertIn("portable_macos.py", source)
        self.assertNotIn("Canto-0243.app", source)

    def test_macos_tar_is_portable_folder_only(self):
        source = BUILD_SH.read_text(encoding="utf-8")
        self.assertIn('"canto-0243-portable"', source)
        self.assertNotIn("Canto-0243.app", source)

    def test_build_portable_adhoc_signs_mac_command(self):
        source = BUILD_SH.read_text(encoding="utf-8")
        self.assertIn('codesign --force --sign - "$OUT_DIR/Canto-0243.command"', source)
        self.assertNotIn('codesign --deep', source)

    def test_release_macos_local_script_exists(self):
        script = REPO_ROOT / "scripts" / "release-macos-local.sh"
        self.assertTrue(script.is_file())
        source = script.read_text(encoding="utf-8")
        self.assertIn("--upload", source)
        self.assertIn("build-portable.sh", source)
        self.assertIn("canto-0243-portable-macos-", source)


if __name__ == "__main__":
    unittest.main()
