"""words.hk wordslist + kaifang TXT lexicon ingest."""
from __future__ import annotations

import unittest
from pathlib import Path

from ingest.lexicon_sources import ingest_kaifang_txt, ingest_words_hk_wordslist

ROOT = Path(__file__).resolve().parents[1]
WORDS_HK_SAMPLE = ROOT / "data/lexicon/fixtures/words_hk_wordslist_sample.json"
KAIFANG_SAMPLE = ROOT / "data/lexicon/fixtures/kaifang_sample.txt"


class WordsHkWordslistIngestTests(unittest.TestCase):
    def test_reads_native_wordslist_dict(self):
        out = ingest_words_hk_wordslist(WORDS_HK_SAMPLE, source_id="words_hk")
        keys = {(c.char, c.jyutping) for c in out}
        self.assertIn(("開心", "hoi1 sam1"), keys)
        self.assertIn(("開心", "hoi1 sam3"), keys)
        self.assertIn(("香港", "hoeng1 gong2"), keys)
        self.assertTrue(all(c.sources == ("words_hk",) for c in out))
        self.assertTrue(all(c.code for c in out))


class KaifangTxtIngestTests(unittest.TestCase):
    def test_reads_kaifang_flat_array_txt(self):
        out = ingest_kaifang_txt(KAIFANG_SAMPLE, source_id="kaifang")
        keys = {(c.char, c.jyutping) for c in out}
        self.assertIn(("開心", "hoi1 sam1"), keys)
        self.assertIn(("就", "zau6"), keys)


if __name__ == "__main__":
    unittest.main()
