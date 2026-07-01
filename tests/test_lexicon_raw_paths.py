"""Lexicon SSOT raw path resolution (legacy data/raw fallback)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ingest.lexicon_raw_paths import resolve_lexicon_raw_path

ROOT = Path(__file__).resolve().parents[1]


class LexiconRawPathTests(unittest.TestCase):
    def test_prefers_lexicon_raw_path_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "data/lexicon/raw/words_hk/wordslist.json"
            primary.parent.mkdir(parents=True)
            primary.write_text("{}", encoding="utf-8")
            legacy = root / "data/raw/words.hk/wordslist.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("{}", encoding="utf-8")
            src = {"id": "words_hk", "raw_path": "data/lexicon/raw/words_hk/wordslist.json"}
            self.assertEqual(resolve_lexicon_raw_path(src, repo_root=root), primary)

    def test_falls_back_to_data_raw_words_hk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "data/raw/words.hk/wordslist.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("{}", encoding="utf-8")
            src = {"id": "words_hk", "raw_path": "data/lexicon/raw/words_hk/wordslist.json"}
            self.assertEqual(resolve_lexicon_raw_path(src, repo_root=root), legacy)

    def test_falls_back_to_data_raw_kaifang_txt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "data/raw/kaifang/cidian.txt"
            legacy.parent.mkdir(parents=True)
            legacy.write_text('["就", "zau6", "就"]', encoding="utf-8")
            src = {"id": "kaifang", "raw_path": "data/lexicon/raw/kaifang/cantonese.json"}
            self.assertEqual(resolve_lexicon_raw_path(src, repo_root=root), legacy)

    def test_repo_legacy_words_hk_exists_on_maintainer_machine(self):
        legacy = ROOT / "data/raw/words.hk/wordslist.json"
        if not legacy.is_file():
            self.skipTest("maintainer-local raw not present")
        src = {"id": "words_hk", "raw_path": "data/lexicon/raw/words_hk/wordslist.json"}
        self.assertEqual(resolve_lexicon_raw_path(src, repo_root=ROOT), legacy)


if __name__ == "__main__":
    unittest.main()
