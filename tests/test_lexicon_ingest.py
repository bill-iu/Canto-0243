"""Lexicon SSOT ingest + merge tests."""
from __future__ import annotations

import unittest
from pathlib import Path

from app.lexicon.candidates import LexiconCandidate
from ingest.lexicon_merge import merge_lexicon_candidates
from ingest.lexicon_sources import ingest_rime_char_csv

ROOT = Path(__file__).resolve().parents[1]
RIME_FIXTURE = ROOT / "data" / "rime" / "fixtures" / "char_sample.csv"


class LexiconRimeIngestTests(unittest.TestCase):
    def test_ingest_rime_includes_all_pron_ranks(self):
        out = ingest_rime_char_csv(RIME_FIXTURE)
        keys = {(c.char, c.jyutping) for c in out}
        self.assertIn(("好", "hou2"), keys)
        self.assertIn(("好", "hou3"), keys)
        self.assertTrue(all(c.sources == ("rime",) for c in out))


class LexiconMergeTests(unittest.TestCase):
    def test_higher_priority_claims_multi_char_literal(self):
        high = [
            LexiconCandidate(char="開心", jyutping="hoi1 sam1", code="01", sources=("words_hk",)),
        ]
        low = [
            LexiconCandidate(char="開心", jyutping="hoi1 sam1", code="01", sources=("curated",)),
            LexiconCandidate(char="開心", jyutping="hoi1 sam3", code="03", sources=("curated",)),
        ]
        out = merge_lexicon_candidates([(90, high), (10, low)])
        keys = {(c.char, c.jyutping) for c in out}
        self.assertEqual(keys, {("開心", "hoi1 sam1")})
        self.assertEqual(out[0].sources, ("words_hk", "curated"))

    def test_single_char_allows_multiple_readings_from_layers(self):
        rime = [
            LexiconCandidate(char="好", jyutping="hou2", code="2", sources=("rime",)),
            LexiconCandidate(char="好", jyutping="hou3", code="3", sources=("rime",)),
        ]
        out = merge_lexicon_candidates([(100, rime)])
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
