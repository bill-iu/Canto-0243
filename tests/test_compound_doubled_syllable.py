"""同音節疊字（$$）— 行為測試（CONTEXT § 同音節疊字查詢）。"""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.compound_doubled_syllable import (
    build_doubled_syllable_snapshot,
    reset_doubled_syllable_snapshot_for_tests,
)
from app.models.word import Word
from app.services.query_dispatch import search_words
from app.services.query_lexer import normalize_search_query
from app.services.query_parse import CompoundDoubledSyllableQuery, parse_query
from app.services.query_types import QueryKind


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class CompoundDoubledSyllableTests(unittest.TestCase):
    def setUp(self):
        reset_doubled_syllable_snapshot_for_tests()

    def tearDown(self):
        reset_doubled_syllable_snapshot_for_tests()

    def test_bare_doubled_dollar_parses(self):
        parsed = _parse("$$")
        self.assertIsInstance(parsed, CompoundDoubledSyllableQuery)
        self.assertEqual(parsed.kind, QueryKind.COMPOUND_DOUBLED_SYLLABLE)
        self.assertIsNone(parsed.code_prefix)
        self.assertIsNone(parsed.rhyme_char)

    def test_doubled_dollar_finds_same_syllable_two_char_words(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

        with Session() as session:
            session.add_all(
                [
                    Word(
                        id=1,
                        char="慢慢",
                        code="55",
                        jyutping="maan5 maan5",
                        finals='["aan","aan"]',
                        initials='["m","m"]',
                        length=2,
                    ),
                    Word(
                        id=2,
                        char="識食",
                        code="11",
                        jyutping="sik1 sik6",
                        finals='["ik","ik"]',
                        initials='["s","s"]',
                        length=2,
                    ),
                    Word(
                        id=3,
                        char="朋友",
                        code="33",
                        jyutping="pang4 jau5",
                        finals='["ang","au"]',
                        initials='["p","j"]',
                        length=2,
                    ),
                ]
            )
            session.commit()
            build_doubled_syllable_snapshot(session)
            results = search_words(q="$$", mode="m1", db=session, limit=20, offset=0)

        chars = [r["char"] for r in results]
        self.assertIn("慢慢", chars)
        self.assertIn("識食", chars)
        self.assertNotIn("朋友", chars)


if __name__ == "__main__":
    unittest.main()
