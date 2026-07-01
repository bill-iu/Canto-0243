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


if __name__ == "__main__":
    unittest.main()
