"""Unit tests for equals query → MatchSpec (candidate 2)."""

import unittest

from app.services.position_match import (
    build_equals_match_spec,
    matches_equals_phoneme_span,
)


class BuildEqualsMatchSpecTests(unittest.TestCase):
    def test_whole_word_rhyme(self):
        spec = build_equals_match_spec("香港=")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.ref_literal, "香港")
        self.assertTrue(spec.whole_word_phoneme_match)
        self.assertEqual(spec.ref_dimension, "final")
        self.assertEqual(spec.width, 2)
        self.assertIsNone(spec.code_prefix)

    def test_code_sandwich_initial(self):
        spec = build_equals_match_spec("2=我3")
        self.assertEqual(spec.ref_literal, "我")
        self.assertEqual(spec.ref_dimension, "initial")
        self.assertTrue(spec.phoneme_anchor_only)
        self.assertEqual(spec.ref_start_pos, 0)
        self.assertEqual(spec.code_prefix, "23")
        self.assertEqual(spec.width, 2)
        self.assertFalse(spec.whole_word_phoneme_match)

    def test_code_sandwich_final(self):
        spec = build_equals_match_spec("2我=3")
        self.assertEqual(spec.ref_dimension, "final")
        self.assertTrue(spec.phoneme_anchor_only)

    def test_multi_digit_left_anchor(self):
        spec = build_equals_match_spec("23=你4")
        self.assertEqual(spec.ref_start_pos, 1)
        self.assertEqual(spec.code_prefix, "234")
        self.assertEqual(spec.width, 3)
        self.assertEqual(spec.ref_dimension, "initial")

    def test_equals_query_to_match_spec(self):
        from app.services.query_engine import EqualsQuery

        spec = EqualsQuery(raw_q="23=你4").to_match_spec()
        self.assertEqual(spec.ref_start_pos, 1)


class MatchesEqualsPhonemeSpanTests(unittest.TestCase):
    def _word(self, char, *, initials, finals):
        return {"char": char, "initials": initials, "finals": finals}

    def test_anchor_only_skips_literal_presence(self):
        word = self._word("拿一好", initials=["n", "n", "h"], finals=["aa", "ei", "ou"])
        ref_parts = ["n"]
        self.assertTrue(
            matches_equals_phoneme_span(
                word,
                ref_parts,
                start_pos=1,
                phoneme_anchor_only=True,
                ref_literal="你",
                dimension="initial",
            )
        )

    def test_non_anchor_requires_literal_substring(self):
        word = self._word("好我", initials=["h", "ng"], finals=["ou", "o"])
        self.assertFalse(
            matches_equals_phoneme_span(
                word,
                ["ng"],
                start_pos=0,
                phoneme_anchor_only=False,
                ref_literal="我",
                dimension="initial",
            )
        )

    def test_mismatch_at_anchor_pos(self):
        word = self._word("做一好", initials=["z", "d", "h"], finals=["ou", "ak", "ou"])
        self.assertFalse(
            matches_equals_phoneme_span(
                word,
                ["n"],
                start_pos=1,
                phoneme_anchor_only=True,
                ref_literal="你",
                dimension="initial",
            )
        )


if __name__ == "__main__":
    unittest.main()
