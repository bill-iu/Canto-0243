"""CC-Canto removal policy (CONTEXT § 詞條源清單)."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _bootstrap_main():
    path = REPO / "scripts" / "bootstrap_data.py"
    spec = importlib.util.spec_from_file_location("bootstrap_data_cc", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bootstrap_data_cc"] = mod
    spec.loader.exec_module(mod)
    return mod.main


class CcCantoRemovalTests(unittest.TestCase):
    def test_third_party_notices_excludes_cc_canto(self):
        text = (REPO / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        self.assertNotIn("CC-Canto", text)
        self.assertNotIn("cantonese.org/download", text)

    def test_no_standalone_lyrics_db_license(self):
        self.assertFalse((REPO / "LYRICS_DB_LICENSE.md").is_file())

    def test_release_windows_skips_lyrics_db_license(self):
        text = (REPO / "scripts" / "release-windows-local.ps1").read_text(encoding="utf-8")
        self.assertNotIn("LYRICS_DB_LICENSE", text)

    def test_legacy_import_data_script_removed(self):
        self.assertFalse((REPO / "scripts/ingest/import_data.py").is_file())

    def test_bootstrap_next_steps_use_build_db(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = _bootstrap_main()(["--dry-run"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("build-db", out)
        self.assertNotIn("import_data.py", out)

    def test_lexicon_manifest_excludes_cc_canto(self):
        text = (REPO / "data/lexicon/sources.yaml").read_text(encoding="utf-8")
        self.assertNotIn("cc_canto", text.lower())
        self.assertNotIn("cc-canto", text.lower())

    def test_readme_upstream_acknowledgements_exclude_cc_canto(self):
        for rel in ("README.md", "docs/README.en.md", "docs/README.zh-Hans.md"):
            with self.subTest(path=rel):
                text = (REPO / rel).read_text(encoding="utf-8")
                self.assertNotIn("cantonese.org/download", text)
                self.assertNotIn("[CC-Canto]", text)

if __name__ == "__main__":
    unittest.main()
