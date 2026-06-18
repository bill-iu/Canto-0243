"""四字部分韻錨 — 經 search_words 公開介面（CONTEXT § 韻／聲錨 · 四字部分韻錨）。"""
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


class PartialRhymeMaskParseContractTests(unittest.TestCase):
    """解析契約 — 與行為測試分開。"""

    def test_variants_dispatch_to_partial_rhyme_mask(self):
        for q in ("窮?潦倒=", "窮困?倒=", "窮困潦=?"):
            parsed = normalize_and_parse(q)
            self.assertEqual(parsed.kind, QueryKind.PARTIAL_RHYME_MASK, q)

    def test_leading_wildcard_with_equals_is_prefix_family_not_partial(self):
        parsed = normalize_and_parse("?困潦倒=")
        self.assertEqual(parsed.kind, QueryKind.PREFIX_WILDCARD_EQUALS)

    def test_tail_wildcard_before_equals_normalizes(self):
        self.assertEqual(normalize_query("窮困潦=?"), "窮困潦?=")


class PartialRhymeMaskBehaviorTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def test_middle_wildcard_finds_target_word(self):
        """窮?潦倒=：中格通配，首尾錨韻母夾則入選。"""
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="窮?潦倒=", mode="m1", db=db, limit=30))
            self.assertIn("窮困潦倒", found)
        finally:
            db.close()

    def test_penultimate_wildcard_finds_target_word(self):
        """窮困?倒=：倒數第二格通配。"""
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="窮困?倒=", mode="m1", db=db, limit=30))
            self.assertIn("窮困潦倒", found)
        finally:
            db.close()

    def test_tail_wildcard_equals_alias_finds_target_word(self):
        """窮困潦=? normalize 後等同窮困潦?=。"""
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="窮困潦=?", mode="m1", db=db, limit=30))
            self.assertIn("窮困潦倒", found)
        finally:
            db.close()

    def test_fixed_anchor_rhyme_mismatch_excluded(self):
        """固定錨位韻母唔夾 — 窮困?倒= 唔收窮愁潦倒（困≠愁）。"""
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="窮困?倒=", mode="m1", db=db, limit=30))
            self.assertNotIn("窮愁潦倒", found)
        finally:
            db.close()

    def test_tail_wildcard_excludes_anchor_rhyme_mismatch(self):
        """窮困潦=?：尾格通配，中格錨困韻母唔夾則排除窮愁潦倒。"""
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="窮困潦=?", mode="m1", db=db, limit=30))
            self.assertNotIn("窮愁潦倒", found)
        finally:
            db.close()

    def test_wildcard_slot_allows_different_middle_rhyme(self):
        """通配格唔約束韻母：窮?潦倒= 可收窮愁潦倒（中格愁韻母唔使同困）。"""
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="窮?潦倒=", mode="m1", db=db, limit=30))
            self.assertIn("窮愁潦倒", found)
        finally:
            db.close()

    def test_unrelated_four_char_word_excluded(self):
        """唔相關四字詞 — 錨位韻母全唔夾則排除。"""
        db = _memory_db(_qiong_kun_liu_dao(), _qiong_tou_liu_dao())
        try:
            found = _chars(search_words(q="窮困?倒=", mode="m1", db=db, limit=30))
            self.assertIn("窮困潦倒", found)
            self.assertNotIn("窮途潦倒", found)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
