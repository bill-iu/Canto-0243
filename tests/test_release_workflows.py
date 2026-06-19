"""Release workflow contracts (ADR-0018)."""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LEXICON_WF = REPO / ".github" / "workflows" / "release-lexicon.yml"


class ReleaseWorkflowTests(unittest.TestCase):
    def test_lexicon_gate_requires_zip_and_x86_64_not_arm64(self):
        text = LEXICON_WF.read_text(encoding="utf-8")
        self.assertIn("canto-0243-portable-macos-x86_64.tar.gz", text)
        self.assertNotIn("has_mac_arm", text)

    def test_release_full_workflow_removed(self):
        self.assertFalse((REPO / ".github" / "workflows" / "release-full.yml").is_file())

    def test_split_channel_scripts_exist(self):
        self.assertTrue((REPO / "scripts" / "release-windows-local.ps1").is_file())
        mac = (REPO / "scripts" / "release-macos-local.sh").read_text(encoding="utf-8")
        self.assertIn("--tar-only", mac)
        self.assertIn("GH_REPO", mac)
        self.assertIn("publisher role must publish first", mac)
        self.assertIn("git checkout $TAG", mac)
        self.assertNotIn("release create", mac)
        self.assertNotIn('release upload "$TAG" "$ROOT/lyrics.db"', mac)


if __name__ == "__main__":
    unittest.main()
