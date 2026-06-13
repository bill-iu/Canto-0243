import unittest

from app.services.query_engine import (
    CodeTailQuery,
    CompoundAntQuery,
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
    parse_query,
)
from app.services.word_query_parser import normalize_code_tail_separators


class ParseQueryGoldenTests(unittest.TestCase):
    def _parse(self, q: str):
        return parse_query(normalize_code_tail_separators(q.strip()))

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

    def test_hybrid_tail_equals_alias(self):
        parsed = self._parse("23就=")
        self.assertIsInstance(parsed, HybridTailEqualsAliasQuery)
        self.assertEqual(parsed.hybrid_q, "23就")

    def test_equals_query_whole_word(self):
        parsed = self._parse("香港=")
        self.assertIsInstance(parsed, EqualsQuery)
        self.assertEqual(parsed.raw_q, "香港=")

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

    def test_relation_beats_mask(self):
        parsed = self._parse("~開心")
        self.assertNotIsInstance(parsed, MaskQuery)

    def test_unmatched_empty_symbols(self):
        parsed = self._parse("+++")
        self.assertIsInstance(parsed, UnmatchedQuery)


if __name__ == "__main__":
    unittest.main()
