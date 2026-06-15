"""整詞等號查詢（香港=、=香港）— cache 與 DB 路徑行為一致。"""

from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import search_words
from app.utils.word_cache import (
    complete_preload,
    populate_word_cache_from_rows,
    reset_word_cache_for_tests,
)


class WholeWordEqualsSearchTests(unittest.TestCase):
    """透過 search_words 驗證整詞同韻／同聲優化不改語意。"""

    def setUp(self):
        reset_word_cache_for_tests()

    def tearDown(self):
        reset_word_cache_for_tests()

    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)()

    @staticmethod
    def _word_chars(results) -> list[str]:
        return [r["char"] for r in results if r.get("result_type") == "word"]

    @staticmethod
    def _rows_to_cache(words: list[Word]) -> list[dict]:
        return [
            {
                "char": w.char,
                "code": w.code,
                "jyutping": w.jyutping,
                "finals": w.finals,
                "initials": w.initials,
                "length": w.length,
            }
            for w in words
        ]

    def _rhyme_fixture_words(self) -> list[Word]:
        return [
            Word(
                char="香港",
                code="22",
                jyutping="hoeng1 gong2",
                finals='["oeng", "ong"]',
                initials='["h", "g"]',
                length=2,
            ),
            Word(
                char="香江",
                code="22",
                jyutping="hoeng1 gong1",
                finals='["oeng", "ong"]',
                initials='["h", "g"]',
                length=2,
            ),
            Word(
                char="香島",
                code="22",
                jyutping="hoeng1 dou2",
                finals='["oeng", "ou"]',
                initials='["h", "d"]',
                length=2,
            ),
            Word(
                char="做就",
                code="23",
                jyutping="zou6 zau6",
                finals='["ou", "au"]',
                initials='["z", "z"]',
                length=2,
            ),
        ]

    def _initial_fixture_words(self) -> list[Word]:
        return [
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
                code="22",
                jyutping="hoeng1 gong1",
                finals='["oeng", "ong"]',
                initials='["h", "g"]',
                length=2,
            ),
            Word(
                char="航機",
                code="40",
                jyutping="hong4 gei1",
                finals='["ong", "ei"]',
                initials='["h", "g"]',
                length=2,
            ),
            Word(
                char="香島",
                code="22",
                jyutping="hoeng1 dou2",
                finals='["oeng", "ou"]',
                initials='["h", "d"]',
                length=2,
            ),
        ]

    def _jy_nucleus_fixture_words(self) -> list[Word]:
        return [
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

    def test_whole_word_rhyme_excludes_wrong_finals(self):
        with self._session() as session:
            session.add_all(self._rhyme_fixture_words())
            session.commit()
            chars = self._word_chars(
                search_words(q="香港=", mode="m1", db=session, limit=20, offset=0)
            )
        self.assertIn("香港", chars)
        self.assertIn("香江", chars)
        self.assertNotIn("香島", chars)
        self.assertNotIn("做就", chars)

    def test_whole_word_initial_includes_matching_initials(self):
        with self._session() as session:
            session.add_all(self._initial_fixture_words())
            session.commit()
            chars = self._word_chars(
                search_words(q="=香港", mode="m1", db=session, limit=20, offset=0)
            )
        self.assertIn("香港", chars)
        self.assertIn("香江", chars)
        self.assertIn("航機", chars)
        self.assertNotIn("香島", chars)

    def test_whole_word_rhyme_jy_nucleus_excludes_same_stored_finals(self):
        """儲存 finals 相同但粵拼韻母不同者不得入選（粵語 vs 撥付）。"""
        with self._session() as session:
            session.add_all(self._jy_nucleus_fixture_words())
            session.commit()
            chars = self._word_chars(
                search_words(q="粵語=", mode="m1", db=session, limit=20, offset=0)
            )
        self.assertIn("粵語", chars)
        self.assertNotIn("撥付", chars)

    def test_whole_word_rhyme_cache_matches_db_fallback(self):
        words = self._rhyme_fixture_words()
        with self._session() as session:
            session.add_all(words)
            session.commit()
            baseline = self._word_chars(
                search_words(q="香港=", mode="m1", db=session, limit=50, offset=0)
            )

            populate_word_cache_from_rows(self._rows_to_cache(words))
            complete_preload()
            indexed = self._word_chars(
                search_words(q="香港=", mode="m1", db=session, limit=50, offset=0)
            )
        self.assertEqual(indexed, baseline)

    def test_whole_word_initial_cache_matches_db_fallback(self):
        words = self._initial_fixture_words()
        with self._session() as session:
            session.add_all(words)
            session.commit()
            baseline = self._word_chars(
                search_words(q="=香港", mode="m1", db=session, limit=50, offset=0)
            )

            populate_word_cache_from_rows(self._rows_to_cache(words))
            complete_preload()
            indexed = self._word_chars(
                search_words(q="=香港", mode="m1", db=session, limit=50, offset=0)
            )
        self.assertEqual(indexed, baseline)

    def test_whole_word_rhyme_cache_with_stored_finals_distractor(self):
        """cache 內有同儲存 finals 但粵拼韻母不同者，結果不應誤入。"""
        words = self._jy_nucleus_fixture_words()
        with self._session() as session:
            session.add_all(words)
            session.commit()
            baseline = self._word_chars(
                search_words(q="粵語=", mode="m1", db=session, limit=50, offset=0)
            )

            populate_word_cache_from_rows(self._rows_to_cache(words))
            complete_preload()
            indexed = self._word_chars(
                search_words(q="粵語=", mode="m1", db=session, limit=50, offset=0)
            )
        self.assertEqual(indexed, baseline)
        self.assertNotIn("撥付", indexed)


if __name__ == "__main__":
    unittest.main()
