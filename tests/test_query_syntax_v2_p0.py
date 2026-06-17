"""ADR-0012 P0：normalize 星號槽 + 首格／中格字面 MaskQuery 收斂。"""
from __future__ import annotations

import unittest

from app.services.query_parse import MaskQuery, StarAnchorQuery, build_match_spec, parse_query
from app.services.query_dispatch import search_words
from app.services.word_query_parser import mask_from_canonical_star_query, normalize_search_query
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class NormalizeCanonicalStarTests(unittest.TestCase):
    def test_head_literal_mask(self):
        self.assertEqual(normalize_search_query("香??"), "*香??")
        self.assertEqual(normalize_search_query("門0"), "*門0")

    def test_head_skips_pure_word_lookup(self):
        self.assertEqual(normalize_search_query("香港"), "香港")
        self.assertEqual(normalize_search_query("香"), "香")

    def test_middle_wildcard_before_hanzi(self):
        self.assertEqual(normalize_search_query("?你?"), "?*你?")

    def test_no_star_when_digit_before_hanzi(self):
        self.assertEqual(normalize_search_query("?30人"), "?30人")

    def test_skips_equals_and_rhyme_anchors(self):
        self.assertEqual(normalize_search_query("=香港"), "=香港")
        self.assertEqual(normalize_search_query("香=?"), "香=?")
        self.assertEqual(normalize_search_query("?港=?"), "?港=?")


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


class P0SearchEquivalenceTests(unittest.TestCase):
    def test_men0_search_same(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            db.add_all(
                [
                    Word(char="門前", code="20", jyutping="mun4 cin4", length=2),
                    Word(char="他人", code="20", jyutping="taa1 jan4", length=2),
                ]
            )
            db.commit()
            a = [
                r["char"]
                for r in search_words(q="門0", mode="m1", db=db, limit=10)
                if r.get("result_type") == "word"
            ]
            b = [
                r["char"]
                for r in search_words(q="*門0", mode="m1", db=db, limit=10)
                if r.get("result_type") == "word"
            ]
            self.assertEqual(a, b)
            self.assertIn("門前", a)
            self.assertNotIn("他人", a)


if __name__ == "__main__":
    unittest.main()
