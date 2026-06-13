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

    def test_left_code_only_equals_integration(self):
        session = self._session_with_words(
            [
                Word(
                    char="好我",
                    code="34",
                    jyutping="hou2 ngo5",
                    finals='["ou", "o"]',
                    initials='["h", "ng"]',
                    length=2,
                ),
                Word(
                    char="小馬騮",
                    code="944",
                    jyutping="siu2 maa5 ngau4",
                    finals='["iu", "aa", "au"]',
                    initials='["s", "m", "ng"]',
                    length=3,
                ),
            ]
        )
        try:
            results = search_words(q="34=我", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("好我", words)
            self.assertNotIn("小馬騮", words)
        finally:
            session.close()

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

    def test_equals_jy_nucleus_excludes_but_fu(self):
        """粵語 jyut6 jyu5 must not rhyme with 撥付 but6 fu6 (yut/yu vs ut/u)."""
        session = self._session_with_words(
            [
                Word(
                    char="粵語",
                    code="24",
                    jyutping="jyut6 jyu5",
                    finals='["ut", "u"]',
                    initials='["jy", "jy"]',
                    length=2,
                ),
                Word(
                    char="撥付",
                    code="22",
                    jyutping="but6 fu6",
                    finals='["ut", "u"]',
                    initials='["b", "f"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="粵語=", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertNotIn("撥付", words)
        finally:
            session.close()

    def test_rhyme_anchor_yuan_excludes_un_final(self):
        """?元= last syllable must rhyme yun (jyun), not plain un (wun/bun)."""
        session = self._session_with_words(
            [
                Word(
                    char="好換",
                    code="42",
                    jyutping="hou2 wun6",
                    finals='["ou", "un"]',
                    initials='["h", "w"]',
                    length=2,
                ),
                Word(
                    char="圓形",
                    code="42",
                    jyutping="jyun4 jing4",
                    finals='["un", "ing"]',
                    initials='["jy", "j"]',
                    length=2,
                ),
                Word(
                    char="元",
                    code="40",
                    jyutping="jyun4",
                    finals='["un"]',
                    initials='["jy"]',
                    length=1,
                ),
            ]
        )
        try:
            results = search_words(q="?元=", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertNotIn("好換", words)
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
