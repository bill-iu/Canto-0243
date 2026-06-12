"""TDD tests for candidate 1: central build_match_spec + unified _dispatch_position_query.

Tests exercise public interfaces (build_match_spec, search_words) — not private dispatch helpers.
"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.match_spec_factory import build_match_spec
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
    RelationLookupQuery,
    RhymeAnchorQuery,
    UnmatchedQuery,
    WordLookupQuery,
    parse_query,
    search_words,
)
from app.services.word_query_parser import normalize_code_tail_separators


def _parse(q: str):
    return parse_query(normalize_code_tail_separators(q.strip()))


class FactoryParityTests(unittest.TestCase):
    """Every position-type ParsedQuery: to_match_spec == build_match_spec."""

    def _assert_factory_parity(self, parsed):
        self.assertEqual(parsed.to_match_spec(), build_match_spec(parsed))

    def test_equals(self):
        self._assert_factory_parity(EqualsQuery(raw_q="2=我3"))

    def test_compound_ant(self):
        self._assert_factory_parity(
            CompoundAntQuery(code_prefix="2", rhyme_char="就")
        )

    def test_code_tail(self):
        self._assert_factory_parity(
            CodeTailQuery(
                code_digits="23", width=3, constraint="final", anchor="就", anchor_pos=2
            )
        )

    def test_literal_ref(self):
        self._assert_factory_parity(
            LiteralRefQuery(code_digits="23", literal_char="就", width=2)
        )

    def test_rhyme_anchor(self):
        self._assert_factory_parity(
            RhymeAnchorQuery(
                constraint="final", anchor_pos=1, anchor="香", slots="?", width=2
            )
        )

    def test_hybrid_code(self):
        self._assert_factory_parity(HybridCodeQuery(raw_q="23就"))

    def test_mask(self):
        self._assert_factory_parity(MaskQuery(raw_q="門0"))


class NonPositionQueryTests(unittest.TestCase):
    """build_match_spec returns None for types handled outside position dispatch."""

    def test_relation_lookup(self):
        self.assertIsNone(
            build_match_spec(
                RelationLookupQuery(relation_kind="syn", word="開心", code_prefix=None)
            )
        )

    def test_digit_code(self):
        self.assertIsNone(build_match_spec(DigitCodeQuery(raw_q="33")))

    def test_word_lookup(self):
        self.assertIsNone(build_match_spec(WordLookupQuery(raw_q="香港")))

    def test_hybrid_tail_alias(self):
        self.assertIsNone(
            build_match_spec(
                HybridTailEqualsAliasQuery(raw_q="23就=", hybrid_q="23就")
            )
        )

    def test_unmatched(self):
        self.assertIsNone(build_match_spec(UnmatchedQuery(raw_q="+++")))


class ParseToSpecPipelineTests(unittest.TestCase):
    """parse_query → build_match_spec produces usable MatchSpec (no DB)."""

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


class UnifiedDispatchTracerTests(unittest.TestCase):
    """Integration: search_words routes position queries through unified dispatch."""

    def _session_with_words(self, words):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all(words)
        session.commit()
        return session

    def test_mask_query_finds_matching_word(self):
        session = self._session_with_words(
            [
                Word(
                    char="門人",
                    code="00",
                    jyutping="mun4 jan4",
                    finals='["un", "an"]',
                    initials='["m", "j"]',
                    length=2,
                ),
                Word(
                    char="門下",
                    code="02",
                    jyutping="mun4 haa6",
                    finals='["un", "aa"]',
                    initials='["m", "h"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="門0", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("門人", words)
            self.assertNotIn("門下", words)
        finally:
            session.close()

    def test_hybrid_code_finds_rhyme_or_literal(self):
        session = self._session_with_words(
            [
                Word(
                    char="做就",
                    code="23",
                    jyutping="zou6 zau6",
                    finals='["ou", "au"]',
                    initials='["z", "z"]',
                    length=2,
                ),
                Word(
                    char="做得",
                    code="23",
                    jyutping="zou6 dak1",
                    finals='["ou", "ak"]',
                    initials='["z", "d"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="23就", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("做就", words)
            self.assertNotIn("做得", words)
        finally:
            session.close()

    def test_hybrid_tail_alias_matches_direct_hybrid(self):
        """23就= rewrites to hybrid_q and uses same unified dispatch path as 23就."""
        session = self._session_with_words(
            [
                Word(
                    char="做就",
                    code="23",
                    jyutping="zou6 zau6",
                    finals='["ou", "au"]',
                    initials='["z", "z"]',
                    length=2,
                ),
            ]
        )
        try:
            direct = search_words(q="23就", mode="m1", db=session, limit=10, offset=0)
            alias = search_words(q="23就=", mode="m1", db=session, limit=10, offset=0)
            direct_chars = [r["char"] for r in direct if r.get("result_type") == "word"]
            alias_chars = [r["char"] for r in alias if r.get("result_type") == "word"]
            self.assertEqual(alias_chars, direct_chars)
        finally:
            session.close()

    def test_literal_ref_tail(self):
        session = self._session_with_words(
            [
                Word(
                    char="做就",
                    code="23",
                    jyutping="zou6 zau6",
                    finals='["ou", "au"]',
                    initials='["z", "z"]',
                    length=2,
                ),
                Word(
                    char="做得",
                    code="23",
                    jyutping="zou6 dak1",
                    finals='["ou", "ak"]',
                    initials='["z", "d"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="23@就", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("做就", words)
            self.assertNotIn("做得", words)
        finally:
            session.close()

    def test_equals_whole_word_rhyme(self):
        session = self._session_with_words(
            [
                Word(
                    char="香港",
                    code="52",
                    jyutping="hoeng1 gong2",
                    finals='["oeng", "ong"]',
                    initials='["h", "g"]',
                    length=2,
                ),
                Word(
                    char="香江",
                    code="52",
                    jyutping="hoeng1 gong1",
                    finals='["oeng", "ong"]',
                    initials='["h", "g"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="香港=", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("香港", words)
            self.assertIn("香江", words)
        finally:
            session.close()


class BuildMatchSpecFactoryTests(unittest.TestCase):
    def test_equals_delegates(self):
        spec = build_match_spec(EqualsQuery(raw_q="香港="))
        self.assertEqual(spec.ref_literal, "香港")
        self.assertTrue(spec.whole_word_phoneme_match)

    def test_compound_ant(self):
        spec = build_match_spec(CompoundAntQuery(code_prefix="33", rhyme_char="就"))
        self.assertEqual(spec.width, 2)
        self.assertEqual(spec.code_prefix, "33")
        self.assertEqual(spec.slots[0].kind, "final_anchor")

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

    def test_to_match_spec_matches_factory(self):
        q = RhymeAnchorQuery(
            constraint="final", anchor_pos=2, anchor="就", slots="23", width=3
        )
        self.assertEqual(q.to_match_spec(), build_match_spec(q))


if __name__ == "__main__":
    unittest.main()
