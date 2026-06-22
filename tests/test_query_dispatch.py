"""Integration tests for query_dispatch — execute_search / search_words."""

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import search_words


class SearchWordsDispatchTests(unittest.TestCase):
    """search_words routes position queries through unified dispatch."""

    def _session_with_words(self, words):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all(words)
        session.commit()
        return session

    def test_left_code_only_equals_integration(self):
        session = self._session_with_words(
            [
                Word(
                    char="好我",
                    code="34",
                    jyutping="hou2 ngo5",
                    finals='["ou", "o"]',
                    initials='["h", "ng"]',
                    length=2,
                ),
                Word(
                    char="小馬騮",
                    code="944",
                    jyutping="siu2 maa5 ngau4",
                    finals='["iu", "aa", "au"]',
                    initials='["s", "m", "ng"]',
                    length=3,
                ),
            ]
        )
        try:
            results = search_words(q="34=我", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("好我", words)
            self.assertNotIn("小馬騮", words)
        finally:
            session.close()

    def test_mask_query_finds_matching_word(self):
        session = self._session_with_words(
            [
                Word(
                    char="門人",
                    code="00",
                    jyutping="mun4 jan4",
                    finals='["un", "an"]',
                    initials='["m", "j"]',
                    length=2,
                ),
                Word(
                    char="門下",
                    code="02",
                    jyutping="mun4 haa6",
                    finals='["un", "aa"]',
                    initials='["m", "h"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="門0", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("門人", words)
            self.assertNotIn("門下", words)
        finally:
            session.close()

    def test_hybrid_code_finds_rhyme_or_literal(self):
        session = self._session_with_words(
            [
                Word(
                    char="做就",
                    code="23",
                    jyutping="zou6 zau6",
                    finals='["ou", "au"]',
                    initials='["z", "z"]',
                    length=2,
                ),
                Word(
                    char="做得",
                    code="23",
                    jyutping="zou6 dak1",
                    finals='["ou", "ak"]',
                    initials='["z", "d"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="23就", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("做就", words)
            self.assertNotIn("做得", words)
        finally:
            session.close()

    def test_hybrid_tail_alias_matches_direct_hybrid(self):
        """23就= rewrites to hybrid_q and uses same unified dispatch path as 23就."""
        session = self._session_with_words(
            [
                Word(
                    char="做就",
                    code="23",
                    jyutping="zou6 zau6",
                    finals='["ou", "au"]',
                    initials='["z", "z"]',
                    length=2,
                ),
            ]
        )
        try:
            direct = search_words(q="23就", mode="m1", db=session, limit=10, offset=0)
            alias = search_words(q="23就=", mode="m1", db=session, limit=10, offset=0)
            direct_chars = [r["char"] for r in direct if r.get("result_type") == "word"]
            alias_chars = [r["char"] for r in alias if r.get("result_type") == "word"]
            self.assertEqual(alias_chars, direct_chars)
        finally:
            session.close()

    def test_literal_ref_tail(self):
        session = self._session_with_words(
            [
                Word(
                    char="做就",
                    code="23",
                    jyutping="zou6 zau6",
                    finals='["ou", "au"]',
                    initials='["z", "z"]',
                    length=2,
                ),
                Word(
                    char="做得",
                    code="23",
                    jyutping="zou6 dak1",
                    finals='["ou", "ak"]',
                    initials='["z", "d"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="23@就", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("做就", words)
            self.assertNotIn("做得", words)
        finally:
            session.close()

    def test_equals_whole_word_rhyme(self):
        session = self._session_with_words(
            [
                Word(
                    char="香港",
                    code="52",
                    jyutping="hoeng1 gong2",
                    finals='["oeng", "ong"]',
                    initials='["h", "g"]',
                    length=2,
                ),
                Word(
                    char="香江",
                    code="52",
                    jyutping="hoeng1 gong1",
                    finals='["oeng", "ong"]',
                    initials='["h", "g"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="香港=", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("香港", words)
            self.assertIn("香江", words)
        finally:
            session.close()

    def test_equals_jy_nucleus_excludes_but_fu(self):
        """粵語 jyut6 jyu5 must not rhyme with 撥付 but6 fu6 (yut/yu vs ut/u)."""
        session = self._session_with_words(
            [
                Word(
                    char="粵語",
                    code="24",
                    jyutping="jyut6 jyu5",
                    finals='["ut", "u"]',
                    initials='["jy", "jy"]',
                    length=2,
                ),
                Word(
                    char="撥付",
                    code="22",
                    jyutping="but6 fu6",
                    finals='["ut", "u"]',
                    initials='["b", "f"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="粵語=", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertNotIn("撥付", words)
        finally:
            session.close()

    def test_rhyme_anchor_yuan_excludes_un_final(self):
        """?元= last syllable must rhyme yun (jyun), not plain un (wun/bun)."""
        session = self._session_with_words(
            [
                Word(
                    char="好換",
                    code="42",
                    jyutping="hou2 wun6",
                    finals='["ou", "un"]',
                    initials='["h", "w"]',
                    length=2,
                ),
                Word(
                    char="圓形",
                    code="42",
                    jyutping="jyun4 jing4",
                    finals='["un", "ing"]',
                    initials='["jy", "j"]',
                    length=2,
                ),
                Word(
                    char="元",
                    code="40",
                    jyutping="jyun4",
                    finals='["un"]',
                    initials='["jy"]',
                    length=1,
                ),
            ]
        )
        try:
            results = search_words(q="?元=", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertNotIn("好換", words)
        finally:
            session.close()

    def test_39zhu_hybrid_excludes_u_rhyme_false_positives(self):
        """39住= 尾格同韻 yu（住），唔匹配 fu 系 u 尾（辛苦、功夫、師父）。"""
        session = self._session_with_words(
            [
                Word(
                    char="留住",
                    code="39",
                    jyutping="lau4 zyu6",
                    finals='["au", "yu"]',
                    initials='["l", "z"]',
                    length=2,
                ),
                Word(
                    char="辛苦",
                    code="39",
                    jyutping="san1 fu1",
                    finals='["an", "u"]',
                    initials='["s", "f"]',
                    length=2,
                ),
                Word(
                    char="功夫",
                    code="39",
                    jyutping="gung1 fu1",
                    finals='["ung", "u"]',
                    initials='["g", "f"]',
                    length=2,
                ),
                Word(
                    char="師父",
                    code="39",
                    jyutping="si1 fu6",
                    finals='["i", "u"]',
                    initials='["s", "f"]',
                    length=2,
                ),
            ]
        )
        try:
            results = search_words(q="39住=", mode="m1", db=session, limit=20, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("留住", words)
            self.assertNotIn("辛苦", words)
            self.assertNotIn("功夫", words)
            self.assertNotIn("師父", words)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
