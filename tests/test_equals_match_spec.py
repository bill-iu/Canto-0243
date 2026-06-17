"""Unit tests for equals query → MatchSpec (EqualsSpan in extra)."""

import unittest

from app.services.position_match.filters import matches_equals_phoneme_span
from app.services.position_match.spec import get_equals_span
from app.services.query_parse import build_equals_match_spec


def _span(spec):
    span = get_equals_span(spec)
    assert span is not None
    return span


class BuildEqualsMatchSpecTests(unittest.TestCase):
    def test_whole_word_rhyme(self):
        spec = build_equals_match_spec("香港=")
        self.assertIsNotNone(spec)
        span = _span(spec)
        self.assertEqual(span.ref_literal, "香港")
        self.assertTrue(span.whole_word)
        self.assertEqual(span.dimension, "final")
        self.assertEqual(spec.width, 2)
        self.assertIsNone(spec.code_prefix)

    def test_whole_word_initial_leading_equals(self):
        spec = build_equals_match_spec("=香港")
        span = _span(spec)
        self.assertEqual(span.ref_literal, "香港")
        self.assertTrue(span.whole_word)
        self.assertEqual(span.dimension, "initial")
        self.assertFalse(span.phoneme_anchor_only)

    def test_code_sandwich_initial(self):
        spec = build_equals_match_spec("2=我3")
        span = _span(spec)
        self.assertEqual(span.ref_literal, "我")
        self.assertEqual(span.dimension, "initial")
        self.assertTrue(span.phoneme_anchor_only)
        self.assertEqual(span.start_pos, 0)
        self.assertEqual(spec.code_prefix, "23")
        self.assertFalse(span.whole_word)

    def test_code_sandwich_final(self):
        spec = build_equals_match_spec("2我=3")
        span = _span(spec)
        self.assertEqual(span.dimension, "final")
        self.assertTrue(span.phoneme_anchor_only)

    def test_left_code_only_sandwich(self):
        spec = build_equals_match_spec("34=我")
        span = _span(spec)
        self.assertEqual(span.ref_literal, "我")
        self.assertEqual(span.start_pos, 1)

    def test_multi_char_ref_whole_word_equals(self):
        spec = build_equals_match_spec("03=催是")
        span = _span(spec)
        self.assertEqual(span.ref_literal, "催是")
        self.assertTrue(span.whole_word)

    def test_multi_digit_left_anchor(self):
        spec = build_equals_match_spec("23=你4")
        span = _span(spec)
        self.assertEqual(span.start_pos, 1)
        self.assertEqual(spec.code_prefix, "234")

    def test_equals_query_build_match_spec(self):
        from app.services.query_parse import EqualsQuery, build_match_spec

        spec = build_match_spec(EqualsQuery(raw_q="23=你4"))
        self.assertEqual(_span(spec).start_pos, 1)


class MatchesEqualsPhonemeSpanTests(unittest.TestCase):
    def _word(self, char, *, initials, finals):
        return {"char": char, "initials": initials, "finals": finals}

    def test_anchor_only_skips_literal_presence(self):
        word = self._word("拿一好", initials=["n", "n", "h"], finals=["aa", "ei", "ou"])
        self.assertTrue(
            matches_equals_phoneme_span(
                word, ["n"], start_pos=1, phoneme_anchor_only=True, ref_literal="你", dimension="initial",
            )
        )

    def test_non_anchor_requires_literal_substring(self):
        word = self._word("好我", initials=["h", "ng"], finals=["ou", "o"])
        self.assertFalse(
            matches_equals_phoneme_span(
                word, ["ng"], start_pos=0, phoneme_anchor_only=False, ref_literal="我", dimension="initial",
            )
        )

    def test_prefix_wildcard_span_rejects_short_phoneme_lists(self):
        """音節不足不得通過（?喜發財= 假陽性：length=4 但 finals 較短）。"""
        word = self._word("冇say", initials=["m", "s"], finals=["ou", "ei"])
        target = ["ei", "aat", "oi"]
        self.assertFalse(
            matches_equals_phoneme_span(
                word,
                target,
                start_pos=1,
                phoneme_anchor_only=True,
                ref_literal="喜發財",
                dimension="final",
            )
        )

    def test_prefix_wildcard_span_accepts_full_rhyme_tail(self):
        word = self._word(
            "恭喜發財",
            initials=["g", "h", "f", "c"],
            finals=["ung", "ei", "aat", "oi"],
        )
        target = ["ei", "aat", "oi"]
        self.assertTrue(
            matches_equals_phoneme_span(
                word,
                target,
                start_pos=1,
                phoneme_anchor_only=True,
                ref_literal="喜發財",
                dimension="final",
            )
        )


if __name__ == "__main__":
    unittest.main()
