"""左碼整詞等號 — `{code}{詞}=` 整詞同韻 + 0243 碼（如 0449窮困潦倒=）。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.lexicon.static_index import load_lexicon_from_folder, reset_lexicon_for_tests
from app.models.word import Word
from app.services.query_dispatch import execute_search, SearchContext, search_words
from app.services.query_grammar.equals import CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT
from app.services.query_parse import normalize_and_parse
from app.services.query_types import EqualsQuery, WordLookupQuery
from app.utils.word_cache import reset_word_cache_for_tests


def _memory_db(*words: Word):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add_all(words)
    session.commit()
    return session


def _word_chars(items) -> list[str]:
    return [r["char"] for r in items if r.get("result_type") == "word"]


class CodePrefixedWholeWordEqualsTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()
        reset_lexicon_for_tests()
        load_lexicon_from_folder(include_fixture=True)

    def test_parse_as_equals_not_lookup(self):
        parsed = normalize_and_parse("0449窮困潦倒=")
        self.assertIsInstance(parsed, EqualsQuery)
        self.assertNotIsInstance(parsed, WordLookupQuery)

    def test_not_same_as_plain_word_lookup(self):
        """0449窮困潦倒= 走缺字型等號，唔係詞條 lookup 版面。"""
        db = _memory_db(
            Word(
                char="窮困潦倒",
                code="0449",
                jyutping="kung4 kwan3 lou5 dou2",
                finals='["ung", "an", "ou", "ou"]',
                initials='["k", "k", "l", "d"]',
                length=4,
            )
        )
        try:
            plain = search_words(q="窮困潦倒", mode="m1", db=db, limit=20)
            prefixed = search_words(q="0449窮困潦倒=", mode="m1", db=db, limit=20)
            self.assertGreater(len(plain), len(_word_chars(prefixed)))
        finally:
            db.close()

    def test_finds_word_with_matching_code(self):
        db = _memory_db(
            Word(
                char="窮困潦倒",
                code="0449",
                jyutping="kung4 kwan3 lou5 dou2",
                finals='["ung", "an", "ou", "ou"]',
                initials='["k", "k", "l", "d"]',
                length=4,
            )
        )
        try:
            found = _word_chars(search_words(q="0449窮困潦倒=", mode="m1", db=db, limit=20))
            self.assertEqual(found, ["窮困潦倒"])
        finally:
            db.close()

    def test_stale_0499_db_row_still_finds_via_lexicon(self):
        db = _memory_db(
            Word(
                char="窮困潦倒",
                code="0499",
                jyutping="kung4 kwan3 liu2 dou2",
                finals='["ung", "an", "iu", "ou"]',
                initials='["k", "k", "l", "d"]',
                length=4,
            )
        )
        try:
            found = _word_chars(search_words(q="0449窮困潦倒=", mode="m1", db=db, limit=20))
            self.assertEqual(found, ["窮困潦倒"])
        finally:
            db.close()

    def test_wrong_code_prefix_shows_hint(self):
        db = _memory_db(
            Word(
                char="窮困潦倒",
                code="0449",
                jyutping="kung4 kwan3 lou5 dou2",
                finals='["ung", "an", "ou", "ou"]',
                initials='["k", "k", "l", "d"]',
                length=4,
            )
        )
        try:
            result = execute_search(
                SearchContext(
                    q="0999窮困潦倒=",
                    code=None,
                    char=None,
                    mode="m1",
                    limit=20,
                    offset=0,
                    db=db,
                )
            )
            self.assertEqual(_word_chars(result.items), [])
            self.assertEqual(
                result.hint,
                CODE_PREFIXED_WHOLE_WORD_EQUALS_EMPTY_HINT.format(
                    literal="窮困潦倒", code="0999"
                ),
            )
        finally:
            db.close()

    def test_unknown_literal_silent_empty(self):
        db = _memory_db()
        try:
            result = execute_search(
                SearchContext(
                    q="0449冇哩個詞=",
                    code=None,
                    char=None,
                    mode="m1",
                    limit=20,
                    offset=0,
                    db=db,
                )
            )
            self.assertEqual(result.items, [])
            self.assertIsNone(result.hint)
        finally:
            db.close()

    def test_ref_code_mismatch_still_rhymes_by_code_prefix(self):
        """23更好=：參考詞 code 49，左碼 23 只約束候選；幸好 code 29 同韻應入選。"""
        db = _memory_db(
            Word(
                char="更好",
                code="49",
                jyutping="gang3 hou2",
                finals='["ang", "ou"]',
                initials='["g", "h"]',
                length=2,
            ),
            Word(
                char="幸好",
                code="29",
                jyutping="hang6 hou2",
                finals='["ang", "ou"]',
                initials='["h", "h"]',
                length=2,
            ),
        )
        try:
            found = _word_chars(search_words(q="23更好=", mode="m1", db=db, limit=20))
            self.assertIn("幸好", found)
            self.assertNotIn("更好", found)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
