"""Maintainer's beng6-only selection removes variants without losing word forms."""
import csv
import unittest
from collections import Counter
from pathlib import Path

from app.lexicon.candidates import LexiconCandidate
from app.lexicon.corrections import DEFAULT_TSV, load_corrections
from app.utils.jyutping_codec import get_0243_code
from ingest.lexicon_overlay import apply_lexicon_overlay

ROOT = Path(__file__).resolve().parents[2]


class DiseaseReadingCorrectionsTests(unittest.TestCase):
    def test_reviewed_variants_keep_every_word_and_other_bing_syllables(self):
        with (ROOT / 'data/lexicon/reviews/2026-10-21-disease-readings.tsv').open(encoding='utf-8', newline='') as handle:
            review = list(csv.DictReader(handle, delimiter='\t'))
        self.assertEqual(Counter(row['action'] for row in review), {'delete': 23, 'set_jyutping': 11})
        candidates = []
        expected = set()
        for row in review:
            char, old, replacement = row['char'], row['old_jyutping'], row['replacement']
            candidates.append(LexiconCandidate(char, old, get_0243_code(old), ('rime_words',)))
            if row['action'] == 'delete':
                candidates.append(LexiconCandidate(char, replacement, get_0243_code(replacement), ('words_hk',)))
            expected.add((char, replacement, get_0243_code(replacement)))
        # bing on another character is outside this maintainer selection.
        for char, jyutping in [('冰', 'bing1'), ('冰病', 'bing1 beng6')]:
            candidates.append(LexiconCandidate(char, jyutping, get_0243_code(jyutping), ('rime_words',)))
            expected.add((char, jyutping, get_0243_code(jyutping)))
        corrected = apply_lexicon_overlay(candidates, load_corrections(DEFAULT_TSV))
        self.assertEqual({(row.char, row.jyutping, row.code) for row in corrected}, expected)
        self.assertEqual(len(corrected), len(expected))
        self.assertFalse(any(
            char == '病' and syllable.startswith('bing')
            for row in corrected for char, syllable in zip(row.char, row.jyutping.split())
        ))


if __name__ == '__main__':
    unittest.main()
