import unittest

from app.services.query_parse import (
    CodeTailQuery,
    CompoundAntQuery,
    CompoundSynQuery,
    DigitCodeQuery,
    EqualsQuery,
    HybridCodeQuery,
    HybridTailEqualsAliasQuery,
    JyutpingFragmentQuery,
    LiteralRefQuery,
    MaskQuery,
    QueryKind,
    RelationLookupQuery,
    RhymeAnchorQuery,
    UnmatchedQuery,
    WordLookupQuery,
    build_match_spec,
    parse_query,
    uses_match_spec,
)
from app.services.word_query_parser import normalize_search_query


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class ParseQueryGoldenTests(unittest.TestCase):
    def _parse(self, q: str):
        return _parse(q)

    def test_relation_syn_lookup(self):
        parsed = self._parse("~開心")
        self.assertIsInstance(parsed, RelationLookupQuery)
        self.assertEqual(parsed.kind, QueryKind.RELATION_LOOKUP)
        self.assertEqual(parsed.relation_kind, "syn")
        self.assertEqual(parsed.word, "開心")
        self.assertIsNone(parsed.code_prefix)

    def test_relation_ant_with_code_prefix(self):
        parsed = self._parse("33!開心")
        self.assertIsInstance(parsed, RelationLookupQuery)
        self.assertEqual(parsed.relation_kind, "ant")
        self.assertEqual(parsed.code_prefix, "33")
        self.assertEqual(parsed.word, "開心")

    def test_compound_ant(self):
        parsed = self._parse("!!")
        self.assertIsInstance(parsed, CompoundAntQuery)
        self.assertEqual(parsed.kind, QueryKind.COMPOUND_ANT)
        self.assertIsNone(parsed.code_prefix)
        self.assertIsNone(parsed.rhyme_char)

    def test_compound_ant_with_rhyme_char(self):
        parsed = self._parse("2!!就")
        self.assertIsInstance(parsed, CompoundAntQuery)
        self.assertEqual(parsed.code_prefix, "2")
        self.assertEqual(parsed.rhyme_char, "就")

    def test_compound_syn(self):
        parsed = self._parse("~~")
        self.assertIsInstance(parsed, CompoundSynQuery)
        self.assertEqual(parsed.kind, QueryKind.COMPOUND_SYN)
        self.assertIsNone(parsed.code_prefix)
        self.assertIsNone(parsed.rhyme_char)

    def test_compound_syn_with_rhyme_char(self):
        parsed = self._parse("33~~你")
        self.assertIsInstance(parsed, CompoundSynQuery)
        self.assertEqual(parsed.code_prefix, "33")
        self.assertEqual(parsed.rhyme_char, "你")

    def test_hybrid_tail_equals_alias(self):
        parsed = self._parse("23就=")
        self.assertIsInstance(parsed, HybridTailEqualsAliasQuery)
        self.assertEqual(parsed.hybrid_q, "23就")

    def test_equals_query_whole_word(self):
        parsed = self._parse("香港=")
        self.assertIsInstance(parsed, EqualsQuery)
        self.assertEqual(parsed.raw_q, "香港=")

    def test_equals_query_whole_word_initial_leading(self):
        parsed = self._parse("=香港")
        self.assertIsInstance(parsed, EqualsQuery)
        self.assertEqual(parsed.raw_q, "=香港")
        self.assertNotIsInstance(parsed, RhymeAnchorQuery)

    def test_equals_query_code_sandwich(self):
        parsed = self._parse("2=我3")
        self.assertIsInstance(parsed, EqualsQuery)

    def test_equals_query_left_code_only(self):
        parsed = self._parse("34=我")
        self.assertIsInstance(parsed, EqualsQuery)
        self.assertNotIsInstance(parsed, RhymeAnchorQuery)

    def test_code_tail_literal(self):
        parsed = self._parse("23*就")
        self.assertIsInstance(parsed, CodeTailQuery)
        self.assertEqual(parsed.code_digits, "23")
        self.assertEqual(parsed.constraint, "literal")
        self.assertEqual(parsed.anchor, "就")

    def test_literal_ref(self):
        parsed = self._parse("23@就")
        self.assertIsInstance(parsed, LiteralRefQuery)
        self.assertEqual(parsed.literal_char, "就")
        self.assertEqual(parsed.code_digits, "23")

    def test_rhyme_anchor_final(self):
        parsed = self._parse("香=?")
        self.assertIsInstance(parsed, RhymeAnchorQuery)
        self.assertEqual(parsed.constraint, "final")
        self.assertEqual(parsed.anchor, "香")

    def test_rhyme_anchor_initial(self):
        parsed = self._parse("?=就")
        self.assertIsInstance(parsed, RhymeAnchorQuery)
        self.assertEqual(parsed.constraint, "initial")
        self.assertEqual(parsed.anchor, "就")

    def test_hybrid_code(self):
        parsed = self._parse("23就")
        self.assertIsInstance(parsed, HybridCodeQuery)
        self.assertEqual(parsed.raw_q, "23就")

    def test_mask_query(self):
        parsed = self._parse("香??")
        self.assertIsInstance(parsed, MaskQuery)

    def test_digit_code(self):
        parsed = self._parse("23")
        self.assertIsInstance(parsed, DigitCodeQuery)

    def test_word_lookup(self):
        parsed = self._parse("香港")
        self.assertIsInstance(parsed, WordLookupQuery)

    def test_jyutping_fragment(self):
        parsed = self._parse("hoeng")
        self.assertIsInstance(parsed, JyutpingFragmentQuery)

    def test_hybrid_tail_equals_beats_equals(self):
        """23就= must classify as alias, not 等號查詢."""
        parsed = self._parse("23就=")
        self.assertNotIsInstance(parsed, EqualsQuery)

    def test_triple_rhyme_anchor_not_word_lookup(self):
        from app.services.query_parse import TripleRhymeAnchorQuery

        parsed = self._parse("?港=?")
        self.assertIsInstance(parsed, TripleRhymeAnchorQuery)
        self.assertEqual(parsed.anchor, "港")
        self.assertEqual(parsed.width, 3)
        self.assertEqual(parsed.anchor_pos, 1)

    def test_relation_beats_mask(self):
        parsed = self._parse("~開心")
        self.assertNotIsInstance(parsed, MaskQuery)

    def test_unmatched_empty_symbols(self):
        parsed = self._parse("+++")
        self.assertIsInstance(parsed, UnmatchedQuery)


class BuildMatchSpecTests(unittest.TestCase):
    """build_match_spec: ParsedQuery → MatchSpec (no DB)."""

    def test_equals_delegates(self):
        spec = build_match_spec(EqualsQuery(raw_q="香港="))
        self.assertEqual(spec.ref_literal, "香港")
        self.assertTrue(spec.whole_word_phoneme_match)

    def test_compound_ant(self):
        spec = build_match_spec(CompoundAntQuery(code_prefix="33", rhyme_char="就"))
        self.assertEqual(spec.width, 2)
        self.assertEqual(spec.code_prefix, "33")
        self.assertEqual(spec.compound_kind, "ant")
        self.assertEqual(spec.slots[0].kind, "final_anchor")

    def test_compound_syn(self):
        spec = build_match_spec(CompoundSynQuery(code_prefix="33", rhyme_char="你"))
        self.assertEqual(spec.width, 2)
        self.assertEqual(spec.code_prefix, "33")
        self.assertEqual(spec.compound_kind, "syn")
        self.assertEqual(spec.slots[0].kind, "final_anchor")
        self.assertEqual(spec.slots[0].value, "你")

    def test_code_tail(self):
        spec = build_match_spec(
            CodeTailQuery(
                code_digits="23", width=3, constraint="literal", anchor="就", anchor_pos=2
            )
        )
        self.assertEqual(spec.mask, "??就")

    def test_mask(self):
        spec = build_match_spec(MaskQuery(raw_q="門0"))
        self.assertEqual(spec.mask, "門0")
        self.assertEqual(spec.extra["literal_positions"], [(0, "門")])

    def test_hybrid(self):
        spec = build_match_spec(HybridCodeQuery(raw_q="23就"))
        self.assertEqual(spec.code_prefix, "23")

    def test_non_position_returns_none(self):
        self.assertIsNone(
            build_match_spec(
                RelationLookupQuery(relation_kind="syn", word="開心", code_prefix=None)
            )
        )
        self.assertIsNone(build_match_spec(DigitCodeQuery(raw_q="33")))
        self.assertIsNone(build_match_spec(WordLookupQuery(raw_q="香港")))
        self.assertIsNone(build_match_spec(UnmatchedQuery(raw_q="+++")))

    def test_alias_rewrites_to_hybrid_spec(self):
        spec = build_match_spec(
            HybridTailEqualsAliasQuery(raw_q="23就=", hybrid_q="23就")
        )
        self.assertIsNotNone(spec)
        self.assertEqual(spec.width, 2)
        self.assertEqual(spec.code_prefix, "23")

    def test_code_tail_from_parse(self):
        parsed = _parse("23*就")
        spec = build_match_spec(parsed)
        self.assertIsNotNone(spec)
        self.assertEqual(spec.code_prefix, "23")
        self.assertIn("就", spec.mask)

    def test_literal_ref_from_parse(self):
        parsed = _parse("23@就")
        spec = build_match_spec(parsed)
        self.assertEqual(spec.mask, "?就")

    def test_equals_from_parse(self):
        parsed = _parse("23=你4")
        spec = build_match_spec(parsed)
        self.assertEqual(spec.ref_start_pos, 1)
        self.assertEqual(spec.code_prefix, "234")

    def test_triple_rhyme_anchor_spec(self):
        from app.services.query_parse import TripleRhymeAnchorQuery

        spec = build_match_spec(
            TripleRhymeAnchorQuery(
                anchor="港",
                anchor_pos=1,
                width=3,
                leading_slots="?",
            )
        )
        self.assertEqual(spec.width, 3)
        self.assertEqual(spec.mask, "???")
        self.assertEqual(spec.slots[0].pos, 1)
        self.assertEqual(spec.slots[0].kind, "final_anchor")
        self.assertEqual(spec.slots[0].value, "港")


class UsesMatchSpecTests(unittest.TestCase):
    def test_compound_queries_use_match_spec(self):
        self.assertTrue(uses_match_spec(CompoundSynQuery(code_prefix=None, rhyme_char=None)))
        self.assertTrue(uses_match_spec(CompoundAntQuery(code_prefix="33", rhyme_char="就")))

    def test_non_position_queries_do_not(self):
        self.assertFalse(uses_match_spec(RelationLookupQuery(relation_kind="syn", word="開心")))
        self.assertFalse(uses_match_spec(DigitCodeQuery(raw_q="33")))


if __name__ == "__main__":
    unittest.main()
