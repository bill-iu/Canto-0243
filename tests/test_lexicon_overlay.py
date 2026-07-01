"""Declarative lexicon corrections overlay during build (CONTEXT § 詞庫勘誤)."""
from __future__ import annotations

import unittest

from app.lexicon.candidates import LexiconCandidate
from app.lexicon.corrections import LexiconCorrection
from ingest.lexicon_overlay import apply_lexicon_overlay


class LexiconOverlayTests(unittest.TestCase):
    def test_set_jyutping_updates_candidate_reading(self):
        candidates = [
            LexiconCandidate(char="你", jyutping="nei9", code="9", sources=("rime",)),
        ]
        corrections = [
            LexiconCorrection(
                char="你",
                old_jyutping="nei9",
                old_code="9",
                action="set_jyutping",
                value="nei5",
                note="",
            ),
        ]
        out = apply_lexicon_overlay(candidates, corrections)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].jyutping, "nei5")
        self.assertEqual(out[0].code, "4")

    def test_set_code_from_repo_buduan_row(self):
        candidates = [
            LexiconCandidate(char="不斷", jyutping="but1 dyun6", code="34", sources=("rime",)),
        ]
        corrections = [
            LexiconCorrection(
                char="不斷",
                old_jyutping="but1 dyun6",
                old_code="34",
                action="set_code",
                value="32",
            ),
        ]
        out = apply_lexicon_overlay(candidates, corrections)
        self.assertEqual(out[0].jyutping, "but1 dyun6")
        self.assertEqual(out[0].code, "32")


if __name__ == "__main__":
    unittest.main()
