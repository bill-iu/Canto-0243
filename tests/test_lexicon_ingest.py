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
    def test_same_layer_keeps_word_level_heteronym(self):
        words_hk = [
            LexiconCandidate(char="今晚", jyutping="gam1 maan5", code="34", sources=("words_hk",)),
            LexiconCandidate(char="今晚", jyutping="gam1 maan1", code="31", sources=("words_hk",)),
        ]
        out = merge_lexicon_candidates([(90, words_hk)])
        keys = {(c.char, c.jyutping) for c in out}
        self.assertEqual(
            keys,
            {("今晚", "gam1 maan5"), ("今晚", "gam1 maan1")},
        )

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

    def test_words_hk_lists_both_readings_when_high_priority(self):
        high = [
            LexiconCandidate(char="開心", jyutping="hoi1 sam1", code="01", sources=("words_hk",)),
            LexiconCandidate(char="開心", jyutping="hoi1 sam3", code="03", sources=("words_hk",)),
        ]
        low = [
            LexiconCandidate(char="開心", jyutping="hoi1 sam3", code="03", sources=("curated",)),
        ]
        out = merge_lexicon_candidates([(90, high), (10, low)])
        keys = {(c.char, c.jyutping) for c in out}
        self.assertEqual(keys, {("開心", "hoi1 sam1"), ("開心", "hoi1 sam3")})
        by_jy = {c.jyutping: c for c in out}
        self.assertEqual(by_jy["hoi1 sam3"].sources, ("words_hk", "curated"))


class LexiconReadingFormatTests(unittest.TestCase):
    def test_rejects_syllable_count_mismatch(self):
        from ingest.lexicon_validate import is_valid_word_lexicon_reading

        self.assertFalse(is_valid_word_lexicon_reading("開心", "hoi1"))
        self.assertTrue(is_valid_word_lexicon_reading("開心", "hoi1 sam1"))

    def test_rejects_invalid_tone_or_token(self):
        from ingest.lexicon_validate import is_valid_word_lexicon_reading

        self.assertFalse(is_valid_word_lexicon_reading("開心", "hoi1 sam"))
        self.assertFalse(is_valid_word_lexicon_reading("開心", "xyz9 wat8"))

    def test_words_hk_ingest_drops_malformed_readings(self):
        import json
        import tempfile

        from ingest.lexicon_sources import ingest_words_hk_wordslist

        payload = {
            "開心": ["hoi1 sam1", "hoi1"],
            "香港": ["hoeng1 gong2"],
        }
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as f:
            json.dump(payload, f, ensure_ascii=False)
            path = f.name
        try:
            out = ingest_words_hk_wordslist(path, source_id="words_hk")
            keys = {(c.char, c.jyutping) for c in out}
            self.assertEqual(keys, {("開心", "hoi1 sam1"), ("香港", "hoeng1 gong2")})
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
