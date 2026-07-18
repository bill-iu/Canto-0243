"""cantonese_md lexicon raw + sources.yaml wiring (no full build-db)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class TestCantoneseMdLexiconSource(unittest.TestCase):
    def test_raw_json_ingests(self) -> None:
        from ingest.lexicon_sources import ingest_lexicon_json

        path = ROOT / "data" / "lexicon" / "raw" / "cantonese_md" / "lexicon.json"
        self.assertTrue(path.is_file(), path)
        cands = ingest_lexicon_json(path, source_id="cantonese_md")
        self.assertGreaterEqual(len(cands), 150)
        for c in cands[:5]:
            self.assertEqual(c.sources, ("cantonese_md",))
            self.assertTrue(c.char)
            self.assertTrue(c.jyutping)
            self.assertTrue(c.code)
            self.assertLessEqual(len(c.char), 12)

    def test_manifest_lists_source(self) -> None:
        from ingest.lexicon_build import DEFAULT_LEXICON_MANIFEST
        from ingest.syn_ant_manifest import load_manifest, select_sources

        manifest = load_manifest(DEFAULT_LEXICON_MANIFEST)
        sources = select_sources(manifest, defaults_only=True)
        by_id = {str(s["id"]): s for s in sources}
        self.assertIn("cantonese_md", by_id)
        src = by_id["cantonese_md"]
        self.assertEqual(src.get("parser"), "lexicon_json")
        self.assertTrue(src.get("enabled_by_default"))


if __name__ == "__main__":
    unittest.main()
