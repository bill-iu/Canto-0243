"""四字部分聲錨 — 經 search_words 公開介面（=窮?潦倒 家族）。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import search_words
from app.services.query_parse import normalize_and_parse, normalize_query
from app.services.query_types import QueryKind
from app.utils.word_cache import reset_word_cache_for_tests


def _memory_db(*words: Word):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    session.add_all(words)
    session.commit()
    return session


def _chars(items) -> list[str]:
    return [r["char"] for r in items if r.get("result_type") == "word"]


def _word(char: str, *, code: str, jyutping: str, finals: str, initials: str, length: int) -> Word:
    return Word(
        char=char,
        code=code,
        jyutping=jyutping,
        finals=finals,
        initials=initials,
        length=length,
    )


def _qiong_kun_liu_dao() -> Word:
    return _word(
        "窮困潦倒",
        code="0449",
        jyutping="kung4 kwan3 lou5 dou2",
        finals='["ung", "an", "ou", "ou"]',
        initials='["k", "k", "l", "d"]',
        length=4,
    )


def _qiong_chou_liu_dao() -> Word:
    return _word(
        "窮愁潦倒",
        code="0049",
        jyutping="kung4 sau4 lou5 dou2",
        finals='["ung", "au", "ou", "ou"]',
        initials='["k", "s", "l", "d"]',
        length=4,
    )


def _qiong_tou_liu_dao() -> Word:
    return _word(
        "窮途潦倒",
        code="0049",
        jyutping="kung4 tou4 lou5 dou2",
        finals='["ung", "ou", "ou", "ou"]',
        initials='["k", "t", "l", "d"]',
        length=4,
    )


class PartialInitialMaskParseContractTests(unittest.TestCase):
    def test_variants_dispatch_to_partial_initial_mask(self):
        for q in ("=窮?潦倒", "=窮困?倒", "=窮困潦?"):
            parsed = normalize_and_parse(q)
            self.assertEqual(parsed.kind, QueryKind.PARTIAL_INITIAL_MASK, q)

    def test_leading_wildcard_with_equals_is_prefix_family_not_partial(self):
        parsed = normalize_and_parse("?=困潦倒")
        self.assertEqual(parsed.kind, QueryKind.PREFIX_WILDCARD_EQUALS)

    def test_tail_wildcard_is_canonical_shape(self):
        self.assertEqual(normalize_query("=窮困潦?"), "=窮困潦?")


class PartialInitialMaskBehaviorTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def test_middle_wildcard_finds_target_word(self):
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="=窮?潦倒", mode="m1", db=db, limit=30))
            self.assertIn("窮困潦倒", found)
        finally:
            db.close()

    def test_penultimate_wildcard_finds_target_word(self):
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="=窮困?倒", mode="m1", db=db, limit=30))
            self.assertIn("窮困潦倒", found)
        finally:
            db.close()

    def test_tail_wildcard_alias_finds_target_word(self):
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="=窮困潦?", mode="m1", db=db, limit=30))
            self.assertIn("窮困潦倒", found)
        finally:
            db.close()

    def test_fixed_anchor_initial_mismatch_excluded(self):
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="=窮困?倒", mode="m1", db=db, limit=30))
            self.assertNotIn("窮愁潦倒", found)
        finally:
            db.close()

    def test_tail_wildcard_excludes_anchor_initial_mismatch(self):
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="=窮困潦?", mode="m1", db=db, limit=30))
            self.assertNotIn("窮愁潦倒", found)
        finally:
            db.close()

    def test_wildcard_slot_allows_different_middle_initial(self):
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="=窮?潦倒", mode="m1", db=db, limit=30))
            self.assertIn("窮愁潦倒", found)
        finally:
            db.close()

    def test_unrelated_four_char_word_excluded(self):
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_tou_liu_dao())
        try:
            found = _chars(search_words(q="=窮困?倒", mode="m1", db=db, limit=30))
            self.assertIn("窮困潦倒", found)
            self.assertNotIn("窮途潦倒", found)
        finally:
            db.close()


class PrefixWildcardInitialBehaviorTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def test_suffix_template_finds_compound_word(self):
        """?=困潦倒 用長詞後綴聲母模板，應返窮困潦倒。"""
        db = _memory_db(
            _word(
                "困潦倒",
                code="499",
                jyutping="kwan3 liu2 dou2",
                finals='["an", "iu", "ou"]',
                initials='["k", "l", "d"]',
                length=3,
            ),
            _qiong_kun_liu_dao(),
            _qiong_chou_liu_dao(),
        )
        try:
            found = _chars(search_words(q="?=困潦倒", mode="m1", db=db, limit=20))
            self.assertIn("窮困潦倒", found)
            self.assertNotIn("窮愁潦倒", found)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
