"""ADR-0012/0013 查詢語法 v2 — normalize／parse／spec 契約（行為見 test_query_syntax_v2_behavior）。"""
from __future__ import annotations

import unittest

from app.services.query_parse import (
    CodeRefMiddleRhymeQuery,
    JyutpingAnchorQuery,
    RhymeAnchorQuery,
    StarAnchorQuery,
    UnmatchedQuery,
    WildcardCodeAnchorQuery,
    build_match_spec,
    parse_query,
)
from app.services.word_query_parser import (
    CONSECUTIVE_SLOT_CONNECTOR_HINT,
    DIGIT_AFTER_SLOT_CONNECTOR_HINT,
    mask_from_canonical_star_query,
    normalize_search_query,
)


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class NormalizeCanonicalStarTests(unittest.TestCase):
    def test_head_literal_mask(self):
        self.assertEqual(normalize_search_query("香??"), "*香??")
        self.assertEqual(normalize_search_query("門0"), "*門0")

    def test_head_skips_pure_word_lookup(self):
        self.assertEqual(normalize_search_query("香港"), "香港")
        self.assertEqual(normalize_search_query("香"), "香")

    def test_middle_wildcard_before_canto(self):
        self.assertEqual(normalize_search_query("?你?"), "?*你?")

    def test_no_star_when_digit_before_canto(self):
        self.assertEqual(normalize_search_query("?30人"), "?30人")

    def test_skips_equals_and_rhyme_anchors(self):
        self.assertEqual(normalize_search_query("=香港"), "=香港")
        self.assertEqual(normalize_search_query("香=?"), "香=?")

    def test_middle_rhyme_triple_normalizes(self):
        self.assertEqual(normalize_search_query("?港=?"), "?*港=?")
        self.assertEqual(normalize_search_query("?3人=?"), "?3人=?")

    def test_redundant_single_char_initial(self):
        self.assertEqual(normalize_search_query("?=就"), "=就")


class CanonicalStarMaskParseTests(unittest.TestCase):
    def test_head_mask_from_canonical(self):
        self.assertEqual(mask_from_canonical_star_query("*香??"), "香??")
        self.assertEqual(mask_from_canonical_star_query("*門0"), "門0")

    def test_middle_mask_from_canonical(self):
        self.assertEqual(mask_from_canonical_star_query("?*你?"), "?你?")

    def test_rejects_rhyme_head(self):
        self.assertIsNone(mask_from_canonical_star_query("*門=0"))


class P0EquivalentMatchSpecTests(unittest.TestCase):
    def test_men0_alias_same_spec(self):
        spec_a = build_match_spec(_parse("門0"))
        spec_b = build_match_spec(_parse("*門0"))
        self.assertEqual(spec_a.width, spec_b.width)
        self.assertEqual(spec_a.mask, spec_b.mask)
        self.assertEqual(
            [(s.pos, s.kind, s.value) for s in spec_a.slots],
            [(s.pos, s.kind, s.value) for s in spec_b.slots],
        )

    def test_heung_mask_alias_same_spec(self):
        spec_a = build_match_spec(_parse("香??"))
        spec_b = build_match_spec(_parse("*香??"))
        self.assertEqual(spec_a.mask, spec_b.mask)
        self.assertEqual(spec_a.width, 3)

    def test_middle_you_same_spec(self):
        spec_a = build_match_spec(_parse("?你?"))
        spec_b = build_match_spec(_parse("?*你?"))
        self.assertEqual(spec_a.mask, spec_b.mask)

    def test_middle_rhyme_triple_same_spec(self):
        spec_a = build_match_spec(_parse("?港=?"))
        spec_b = build_match_spec(_parse("?*港=?"))
        self.assertEqual(spec_a.width, spec_b.width)
        self.assertEqual(spec_a.mask, spec_b.mask)


class P1WildcardCodeAnchorParseTests(unittest.TestCase):
    def test_triple_ref_tail(self):
        parsed = _parse("?30人")
        self.assertIsInstance(parsed, WildcardCodeAnchorQuery)
        self.assertEqual(parsed.width, 3)

    def test_four_syllable_star_before_ref(self):
        parsed = _parse("?30*人")
        self.assertIsInstance(parsed, WildcardCodeAnchorQuery)
        self.assertEqual(parsed.width, 4)

    def test_not_mask_query(self):
        from app.services.query_parse import MaskQuery

        self.assertNotIsInstance(_parse("?30人"), MaskQuery)


class P2SingleCharRhymeTests(unittest.TestCase):
    def test_parse_single_char(self):
        parsed = _parse("?就=")
        self.assertIsInstance(parsed, RhymeAnchorQuery)
        self.assertEqual(parsed.width, 1)

    def test_spec_width_one(self):
        spec = build_match_spec(_parse("?就="))
        self.assertEqual(spec.width, 1)

    def test_double_char_star_rhyme(self):
        parsed = _parse("?*就=")
        self.assertIsInstance(parsed, RhymeAnchorQuery)
        self.assertEqual(parsed.width, 2)


class P3CodeRefMiddleRhymeTests(unittest.TestCase):
    def test_parse(self):
        from app.services.query_parse import SerialPhonemeAnchorQuery

        parsed = _parse("?3人=?")
        self.assertIsInstance(parsed, SerialPhonemeAnchorQuery)
        self.assertEqual(parsed.width, 3)
        self.assertEqual(parsed.anchors, [(1, "人")])

    def test_contradiction_hint(self):
        parsed = _parse("?3人?")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertIn("?3人=?", parsed.hint or "")


class P4HeadLiteralExtensionTests(unittest.TestCase):
    def test_head_plus_wca(self):
        parsed = _parse("*香?30人")
        self.assertIsInstance(parsed, WildcardCodeAnchorQuery)
        self.assertEqual(parsed.width, 4)
        self.assertEqual(parsed.head_literal, "香")


class PlusAliasNormalizeTests(unittest.TestCase):
    def test_plus_and_fullwidth_plus_to_star(self):
        self.assertEqual(normalize_search_query("23+就"), "23*就")
        self.assertEqual(normalize_search_query("23＋就"), "23*就")

    def test_plus_alias_parses_like_star(self):
        self.assertIsInstance(_parse("23+就"), StarAnchorQuery)
        self.assertEqual(_parse("23+就").anchor, "就")


class SlotConnectorSyntaxErrorTests(unittest.TestCase):
    def test_consecutive_connectors_hint(self):
        parsed = _parse("?30++人")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertEqual(parsed.hint, CONSECUTIVE_SLOT_CONNECTOR_HINT)

    def test_star_before_digit_hint(self):
        parsed = _parse("2*好*3")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertEqual(parsed.hint, DIGIT_AFTER_SLOT_CONNECTOR_HINT)


class JyutpingSlotNormalizeTests(unittest.TestCase):
    def test_question_hon_inserts_star(self):
        self.assertEqual(normalize_search_query("?hon"), "?*hon")

    def test_triple_yut_inserts_star(self):
        self.assertEqual(normalize_search_query("?yut?"), "?*yut?")

    def test_code_syllable_three_replaces_question(self):
        self.assertEqual(normalize_search_query("3?ngo4"), "3*ngo4")
        self.assertEqual(normalize_search_query("3+ngo4"), "3*ngo4")


class CodeRhymeStarTailParseTests(unittest.TestCase):
    def test_23_plus_o_is_three_syllable_jyutping(self):
        parsed = _parse("23+o")
        self.assertIsInstance(parsed, JyutpingAnchorQuery)
        self.assertEqual(parsed.width, 3)

    def test_23o_stays_two_syllable(self):
        parsed = _parse("23o")
        self.assertIsInstance(parsed, JyutpingAnchorQuery)
        self.assertEqual(parsed.width, 2)


if __name__ == "__main__":
    unittest.main()
