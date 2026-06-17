"""串列韻／聲錨行為 — 多錨 AND，經 search_words 公開介面（ADR-0014）。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import search_words
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


def _zhong_yin_ban_dao() -> Word:
    """第 4 格同「倒」韻，第 2 格同「困」韻，但第 1 格唔係串列要求嘅錨組合。"""
    return _word(
        "中印半島",
        code="0449",
        jyutping="zung1 jan3 bun2 dou2",
        finals='["ung", "an", "un", "ou"]',
        initials='["z", "j", "b", "d"]',
        length=4,
    )


def _gai_shi_tai_bao() -> Word:
    """只得尾格「倒」韻相合，前格唔夾。"""
    return _word(
        "蓋世太保",
        code="0449",
        jyutping="koi3 sai3 taai3 bou2",
        finals='["oi", "ai", "aai", "ou"]',
        initials='["g", "s", "t", "b"]',
        length=4,
    )


class SerialPhonemeAnchorBehaviorTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def test_two_rhyme_anchors_require_both(self):
        """04困=49倒= 須同時滿足第 2／4 格韻錨（困、倒）。"""
        db = _memory_db(_qiong_kun_liu_dao(), _gai_shi_tai_bao())
        try:
            found = _chars(search_words(q="04困=49倒=", mode="m1", db=db, limit=20))
            self.assertIn("窮困潦倒", found)
            self.assertNotIn("蓋世太保", found)
        finally:
            db.close()

    def test_three_rhyme_anchors_all_required(self):
        """?4困=4潦=9倒= 三個韻錨須全部通過，唔可以只得尾格倒。"""
        db = _memory_db(_qiong_kun_liu_dao(), _gai_shi_tai_bao(), _zhong_yin_ban_dao())
        try:
            found = _chars(search_words(q="?4困=4潦=9倒=", mode="m1", db=db, limit=20))
            self.assertNotIn("蓋世太保", found)
            self.assertNotIn("中印半島", found)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
