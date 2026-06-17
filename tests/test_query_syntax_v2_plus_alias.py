"""ADR-0013：`+` slot 連接符別名 + 非法形狀 hint。"""
from __future__ import annotations

import unittest

from app.services.query_dispatch import SearchContext, execute_search
from app.services.query_parse import JyutpingAnchorQuery, StarAnchorQuery, UnmatchedQuery, parse_query
from app.services.word_query_parser import (
    CONSECUTIVE_SLOT_CONNECTOR_HINT,
    DIGIT_AFTER_SLOT_CONNECTOR_HINT,
    normalize_search_query,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word


def _parse(q: str):
    return parse_query(normalize_search_query(q))


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


class CodeRhymeStarTailTests(unittest.TestCase):
    def test_23_plus_o_is_three_syllable_jyutping(self):
        parsed = _parse("23+o")
        self.assertIsInstance(parsed, JyutpingAnchorQuery)
        self.assertEqual(parsed.width, 3)

    def test_23o_stays_two_syllable(self):
        parsed = _parse("23o")
        self.assertIsInstance(parsed, JyutpingAnchorQuery)
        self.assertEqual(parsed.width, 2)


class CodeRhymeStarTailSearchTests(unittest.TestCase):
    def test_23_plus_o_matches_three_char_not_two_char(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            db.add_all(
                [
                    Word(
                        char="好我",
                        code="23",
                        jyutping="hou2 ngo5",
                        finals='["ou","o"]',
                        initials='["h","ng"]',
                        length=2,
                    ),
                    Word(
                        char="好我哦",
                        code="230",
                        jyutping="hou2 ngo5 o1",
                        finals='["ou","o","o"]',
                        initials='["h","ng",""]',
                        length=3,
                    ),
                ]
            )
            db.commit()
            two = [
                r["char"]
                for r in execute_search(
                    SearchContext(q="23o", code=None, char=None, mode="m1", limit=10, offset=0, db=db)
                ).items
                if r.get("result_type") == "word"
            ]
            three = [
                r["char"]
                for r in execute_search(
                    SearchContext(q="23+o", code=None, char=None, mode="m1", limit=10, offset=0, db=db)
                ).items
                if r.get("result_type") == "word"
            ]
            self.assertIn("好我", two)
            self.assertNotIn("好我哦", two)
            self.assertIn("好我哦", three)
            self.assertNotIn("好我", three)


if __name__ == "__main__":
    unittest.main()
