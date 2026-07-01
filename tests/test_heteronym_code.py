"""同音異讀（code/code）— 行為測試（CONTEXT § 同音異讀查詢）。"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.lexicon.heteronym_index import build_heteronym_index, reset_heteronym_index_for_tests
from app.models.word import Word
from app.services.query_dispatch import search_words
from app.services.query_lexer import normalize_search_query
from app.services.query_parse import HeteronymCodeQuery, parse_query
from app.services.query_types import QueryKind


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class HeteronymCodeTests(unittest.TestCase):
    def setUp(self):
        reset_heteronym_index_for_tests()

    def tearDown(self):
        reset_heteronym_index_for_tests()

    def test_33_slash_34_parses(self):
        parsed = _parse("33/34")
        self.assertIsInstance(parsed, HeteronymCodeQuery)
        self.assertEqual(parsed.kind, QueryKind.HETERONYM_CODE)
        self.assertEqual(parsed.left_template, "33")
        self.assertEqual(parsed.right_template, "34")

    def test_finds_same_literal_with_two_readings(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="今晚",
                        code="33",
                        jyutping="gum1 maan1",
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="今晚",
                        code="34",
                        jyutping="gum1 maan5",
                        length=2,
                    ),
                    Word(
                        id=3,
                        char="朋友",
                        code="33",
                        jyutping="pang4 jau5",
                        length=2,
                    ),
                ]
            )
            session.commit()
            build_heteronym_index(session)
            results = search_words(q="33/34", mode="m1", db=session, limit=20, offset=0)

        by_jyut = {r["jyutping"]: r for r in results if r["char"] == "今晚"}
        self.assertEqual(len(by_jyut), 2)
        self.assertIn("gum1 maan1", by_jyut)
        self.assertIn("gum1 maan5", by_jyut)
        self.assertEqual(set(by_jyut["gum1 maan1"].get("heteronym_tags", [])), {"左"})
        self.assertEqual(set(by_jyut["gum1 maan5"].get("heteronym_tags", [])), {"右"})
        self.assertFalse(any(r["char"] == "朋友" for r in results))


if __name__ == "__main__":
    unittest.main()
