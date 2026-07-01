"""Release workflow contracts (ADR-0018)."""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LEXICON_WF = REPO / ".github" / "workflows" / "release-lexicon.yml"
RELEASE_DOC = REPO / "docs" / "release.md"


class ReleaseWorkflowTests(unittest.TestCase):
    def test_lexicon_gate_requires_zip_and_x86_64_not_arm64(self):
        text = LEXICON_WF.read_text(encoding="utf-8")
        self.assertIn("canto-0243-portable-macos-x86_64.tar.gz", text)
        self.assertNotIn("has_mac_arm", text)

    def test_release_full_workflow_removed(self):
        self.assertFalse((REPO / ".github" / "workflows" / "release-full.yml").is_file())

    def test_release_docs_lexicon_publish_uses_build_db(self):
        text = RELEASE_DOC.read_text(encoding="utf-8")
        self.assertIn("python -m ingest build-db", text)
        self.assertNotIn("LYRICS_DB_LICENSE", text)

    def test_ci_runs_on_dev_branch(self):
        text = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("dev", text)

    def test_lexicon_workflow_has_no_lyrics_db_license(self):
        text = LEXICON_WF.read_text(encoding="utf-8")
        self.assertNotIn("LYRICS_DB_LICENSE", text)
        self.assertIn("build-db", text)

    def test_split_channel_scripts_exist(self):
        self.assertTrue((REPO / "scripts" / "release-windows-local.ps1").is_file())
        mac = (REPO / "scripts" / "release-macos-local.sh").read_text(encoding="utf-8")
        self.assertIn("--tar-only", mac)
        self.assertIn("GH_REPO", mac)
        self.assertIn("publisher role must publish first", mac)
        self.assertIn("git checkout $TAG", mac)
        self.assertNotIn("release create", mac)
        self.assertNotIn('release upload "$TAG" "$ROOT/lyrics.db"', mac)

    def test_release_windows_hints_build_db_when_db_missing(self):
        text = (REPO / "scripts" / "release-windows-local.ps1").read_text(encoding="utf-8")
        self.assertIn("build-db", text)
        self.assertNotIn("LYRICS_DB_LICENSE", text)


if __name__ == "__main__":
    unittest.main()
