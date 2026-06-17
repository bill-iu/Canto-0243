"""ADR-0012 P1–P5：通配碼錨、單字韻錨、中格韻 hint、頭格擴展。"""
from __future__ import annotations

import unittest

from app.services.query_dispatch import execute_search, SearchContext
from app.services.query_parse import (
    CodeRefMiddleRhymeQuery,
    SingleCharRhymeAnchorQuery,
    UnmatchedQuery,
    WildcardCodeAnchorQuery,
    build_match_spec,
    parse_query,
)
from app.services.word_query_parser import normalize_search_query
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word


def _parse(q: str):
    return parse_query(normalize_search_query(q))


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


class P1SearchTests(unittest.TestCase):
    def _search(self, q: str, db):
        return execute_search(
            SearchContext(q=q, code=None, char=None, mode="m1", limit=20, offset=0, db=db)
        ).items

    def test_dok_syun_jan_in_zhong_nian_jan_out(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            db.add_all(
                [
                    Word(
                        char="讀書人",
                        code="230",
                        jyutping="duk6 syu1 jan4",
                        finals='["uk","yu","an"]',
                        initials='["d","s","j"]',
                        length=3,
                    ),
                    Word(
                        char="西班牙人",
                        code="300",
                        jyutping="sai1 baan1 jan4",
                        finals='["ai","aan","an"]',
                        initials='["s","b","j"]',
                        length=4,
                    ),
                ]
            )
            db.commit()
            chars = [
                r["char"]
                for r in self._search("?30人", db)
                if r.get("result_type") == "word"
            ]
            self.assertIn("讀書人", chars)
            self.assertNotIn("西班牙人", chars)


class P2SingleCharRhymeTests(unittest.TestCase):
    def test_parse_single_char(self):
        parsed = _parse("?就=")
        self.assertIsInstance(parsed, SingleCharRhymeAnchorQuery)
        self.assertEqual(parsed.width, 1)

    def test_spec_width_one(self):
        spec = build_match_spec(_parse("?就="))
        self.assertEqual(spec.width, 1)

    def test_double_char_star_rhyme(self):
        from app.services.query_parse import RhymeAnchorQuery

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


if __name__ == "__main__":
    unittest.main()
