"""?{恰好2字} 無尾 = → 首格通配字面缺字（CONTEXT § 缺字查詢）。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import search_words
from app.services.query_grammar.serial import PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT
from app.services.query_lexer import normalize_search_query
from app.services.query_parse import MaskQuery, UnmatchedQuery, parse_query
from app.utils.word_cache import reset_word_cache_for_tests


def _memory_db(*words: Word):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    session.add_all(words)
    session.commit()
    return session


def _word(char: str, *, code: str, jyutping: str, finals: str, initials: str, length: int) -> Word:
    return Word(
        char=char,
        code=code,
        jyutping=jyutping,
        finals=finals,
        initials=initials,
        length=length,
    )


def _chars(items) -> list[str]:
    return [r["char"] for r in items if r.get("result_type") == "word"]


class MaskLiteralPrefixTwoCharsTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def test_dekuai_parses_as_mask_not_hint(self):
        parsed = parse_query(normalize_search_query("?得快"))
        self.assertIsInstance(parsed, MaskQuery)
        self.assertEqual(parsed.raw_q, "?得快")

    def test_kunliudao_still_gets_prefix_equals_hint(self):
        parsed = parse_query(normalize_search_query("?困潦倒"))
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertEqual(parsed.hint, PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT)

    def test_dekuai_finds_literal_suffix_words(self):
        db = _memory_db(
            _word(
                "跑得快",
                code="934",
                jyutping="paau2 dak1 faai3",
                finals='["aau", "ak", "aai"]',
                initials='["p", "d", "f"]',
                length=3,
            ),
            _word(
                "做得好",
                code="934",
                jyutping="zou6 dak1 hou2",
                finals='["ou", "ak", "ou"]',
                initials='["z", "d", "h"]',
                length=3,
            ),
        )
        try:
            found = _chars(search_words(q="?得快", mode="m1", db=db, limit=20))
            self.assertIn("跑得快", found)
            self.assertNotIn("做得好", found)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
