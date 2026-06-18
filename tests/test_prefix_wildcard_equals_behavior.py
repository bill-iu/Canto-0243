"""前綴通配等號行為 — 經 search_words 公開介面（CONTEXT § 前綴通配等號查詢）。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import SearchContext, execute_search, search_words
from app.services.query_grammar.serial import PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT
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


def _kun_liu_dao() -> Word:
    return _word(
        "困潦倒",
        code="499",
        jyutping="kwan3 liu2 dou2",
        finals='["an", "iu", "ou"]',
        initials='["k", "l", "d"]',
        length=3,
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


def _gong_hei_faat_coi() -> Word:
    return _word(
        "恭喜發財",
        code="0243",
        jyutping="gung1 hei2 faat3 coi4",
        finals='["ung", "ei", "aat", "oi"]',
        initials='["g", "h", "f", "c"]',
        length=4,
    )


def _mou_sei_short_finals() -> Word:
    """length=4 但 finals 較短 — 前綴通配等號 span 不得通過。"""
    return _word(
        "冇say",
        code="0000",
        jyutping="mou5 sei1",
        finals='["ou", "ei"]',
        initials='["m", "s"]',
        length=4,
    )


class PrefixWildcardEqualsBehaviorTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def test_suffix_template_finds_compound_word(self):
        """?困潦倒= 用長詞後綴韻模板，應返窮困潦倒。"""
        db = _memory_db(_kun_liu_dao(), _qiong_kun_liu_dao())
        try:
            found = _chars(search_words(q="?困潦倒=", mode="m1", db=db, limit=20))
            self.assertIn("窮困潦倒", found)
        finally:
            db.close()

    def test_rhyme_mismatch_excluded_without_literal_requirement(self):
        """只比韻母：後綴模板唔夾嘅四字詞唔入選（窮愁潦倒）。"""
        db = _memory_db(_kun_liu_dao(), _qiong_kun_liu_dao(), _qiong_chou_liu_dao())
        try:
            found = _chars(search_words(q="?困潦倒=", mode="m1", db=db, limit=20))
            self.assertIn("窮困潦倒", found)
            self.assertNotIn("窮愁潦倒", found)
        finally:
            db.close()

    def test_xi_fa_coi_excludes_short_phoneme_rows(self):
        """?喜發財= 唔收 finals 音節不足嘅候選（即使 length 欄為 4）。"""
        db = _memory_db(_gong_hei_faat_coi(), _mou_sei_short_finals())
        try:
            found = _chars(search_words(q="?喜發財=", mode="m1", db=db, limit=20))
            self.assertIn("恭喜發財", found)
            self.assertNotIn("冇say", found)
        finally:
            db.close()

    def test_missing_trailing_equals_returns_hint(self):
        """?困潦倒 漏尾 = → 空結果 + hint。"""
        db = _memory_db(_qiong_kun_liu_dao())
        try:
            result = execute_search(
                SearchContext(
                    q="?困潦倒",
                    code=None,
                    char=None,
                    mode="m1",
                    limit=20,
                    offset=0,
                    db=db,
                )
            )
            self.assertEqual(result.items, [])
            self.assertEqual(result.hint, PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
