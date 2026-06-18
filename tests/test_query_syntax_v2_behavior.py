"""ADR-0012/0013 行為測試 — 經 search_words / execute_search 公開介面。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import SearchContext, execute_search, search_words
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


class P0StarAliasSearchEquivalenceTests(unittest.TestCase):
    def test_men0_search_same(self):
        with _memory_db(
            Word(char="門前", code="20", jyutping="mun4 cin4", length=2),
            Word(char="他人", code="20", jyutping="taa1 jan4", length=2),
        ) as db:
            a = _chars(search_words(q="門0", mode="m1", db=db, limit=10))
            b = _chars(search_words(q="+門0", mode="m1", db=db, limit=10))
            self.assertEqual(a, b)
            self.assertIn("門前", a)
            self.assertNotIn("他人", a)


class CodeRhymeStarTailSearchTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def test_23_plus_o_matches_three_char_not_two_char(self):
        with _memory_db(
            Word(
                char="好我",
                code="23",
                jyutping="hou2 ngo5",
                finals='["ou","o"]',
                initials='["h","ng"]',
                length=2,
            ),
            Word(
                char="好我哦",
                code="230",
                jyutping="hou2 ngo5 o1",
                finals='["ou","o","o"]',
                initials='["h","ng",""]',
                length=3,
            ),
        ) as db:
            two = _chars(
                execute_search(
                    SearchContext(q="23o", code=None, char=None, mode="m1", limit=10, offset=0, db=db)
                ).items
            )
            three = _chars(
                execute_search(
                    SearchContext(q="23+o", code=None, char=None, mode="m1", limit=10, offset=0, db=db)
                ).items
            )
            self.assertIn("好我", two)
            self.assertNotIn("好我哦", two)
            self.assertIn("好我哦", three)
            self.assertNotIn("好我", three)


class WildcardCodeAnchorBehaviorTests(unittest.TestCase):
    """通配碼錨：?30人 等 — 詞長＝首通配＋碼位數，尾參考字同韻。"""

    def setUp(self):
        reset_word_cache_for_tests()

    def test_three_syllable_query_finds_matching_word_not_four_char(self):
        with _memory_db(
            Word(
                char="讀書人",
                code="230",
                jyutping="duk6 syu1 jan4",
                finals='["uk","yu","an"]',
                initials='["d","s","j"]',
                length=3,
            ),
            Word(
                char="西班牙人",
                code="300",
                jyutping="sai1 baan1 jan4",
                finals='["ai","aan","an"]',
                initials='["s","b","j"]',
                length=4,
            ),
        ) as db:
            found = _chars(search_words(q="?30人", mode="m1", db=db, limit=20))
            self.assertIn("讀書人", found)
            self.assertNotIn("西班牙人", found)

    def test_four_syllable_star_slot_requires_four_char_word(self):
        with _memory_db(
            Word(
                char="老師本人",
                code="4300",
                jyutping="lou5 si1 bun2 jan4",
                finals='["ou","i","un","an"]',
                initials='["l","s","b","j"]',
                length=4,
            ),
            Word(
                char="讀書人",
                code="230",
                jyutping="duk6 syu1 jan4",
                finals='["uk","yu","an"]',
                initials='["d","s","j"]',
                length=3,
            ),
        ) as db:
            found = _chars(search_words(q="?30+人", mode="m1", db=db, limit=20))
            self.assertIn("老師本人", found)
            self.assertNotIn("讀書人", found)

    def test_intermediate_wildcard_scan(self):
        with _memory_db(
            Word(
                char="口分王人",
                code="0300",
                jyutping="hau2 fan1 wong4 jan4",
                finals='["au","an","ong","an"]',
                initials='["h","f","w","j"]',
                length=4,
            ),
            Word(
                char="口分王門",
                code="0303",
                jyutping="hau2 fan1 wong4 mun4",
                finals='["au","an","ong","un"]',
                initials='["h","f","w","m"]',
                length=4,
            ),
        ) as db:
            found = _chars(search_words(q="?3?0人", mode="m1", db=db, limit=20))
            self.assertIn("口分王人", found)
            self.assertNotIn("口分王門", found)


class SingleCharRhymeBehaviorTests(unittest.TestCase):
    """單字韻錨 ?就= — 只返單字；?+就= 才返二字。"""

    def setUp(self):
        reset_word_cache_for_tests()

    def test_single_char_rhyme_returns_one_char_words_only(self):
        with _memory_db(
            Word(char="就", code="2", jyutping="zau6", finals='["au"]', initials='["z"]', length=1),
            Word(char="做", code="2", jyutping="zou6", finals='["ou"]', initials='["z"]', length=1),
            Word(
                char="做就",
                code="23",
                jyutping="zou6 zau6",
                finals='["ou","au"]',
                initials='["z","z"]',
                length=2,
            ),
        ) as db:
            found = _chars(search_words(q="?就=", mode="m1", db=db, limit=20))
            self.assertIn("就", found)
            self.assertNotIn("做", found)
            self.assertNotIn("做就", found)

    def test_double_char_rhyme_with_star_returns_two_char_words(self):
        with _memory_db(
            Word(
                char="做就",
                code="23",
                jyutping="zou6 zau6",
                finals='["ou","au"]',
                initials='["z","z"]',
                length=2,
            ),
            Word(
                char="做得",
                code="23",
                jyutping="zou6 dak1",
                finals='["ou","ak"]',
                initials='["z","d"]',
                length=2,
            ),
            Word(char="就", code="2", jyutping="zau6", finals='["au"]', initials='["z"]', length=1),
        ) as db:
            found = _chars(search_words(q="?+就=", mode="m1", db=db, limit=20))
            self.assertIn("做就", found)
            self.assertNotIn("做得", found)
            self.assertNotIn("就", found)


class CodeRefMiddleRhymeBehaviorTests(unittest.TestCase):
    """碼＋參考字＋通配（中格韻）：?3人=? 必須 =；?3人? 空結果＋hint。"""

    def setUp(self):
        reset_word_cache_for_tests()

    def test_middle_code_and_rhyme_requires_equals_form(self):
        with _memory_db(
            Word(
                char="口分王",
                code="030",
                jyutping="hau2 fan1 wong4",
                finals='["au","an","ong"]',
                initials='["h","f","w"]',
                length=3,
            ),
            Word(
                char="口分門",
                code="020",
                jyutping="hau2 fan1 mun4",
                finals='["au","an","un"]',
                initials='["h","f","m"]',
                length=3,
            ),
        ) as db:
            found = _chars(search_words(q="?3人=?", mode="m1", db=db, limit=20))
            self.assertIn("口分王", found)
            self.assertNotIn("口分門", found)

    def test_code_ref_without_equals_returns_empty_with_hint(self):
        with _memory_db(
            Word(
                char="口分王",
                code="030",
                jyutping="hau2 fan1 wong4",
                finals='["au","an","ong"]',
                initials='["h","f","w"]',
                length=3,
            ),
        ) as db:
            result = execute_search(
                SearchContext(q="?3人?", code=None, char=None, mode="m1", limit=20, offset=0, db=db)
            )
            self.assertEqual(_chars(result.items), [])
            self.assertIn("?3人=?", result.hint or "")


class HeadLiteralWildcardCodeAnchorBehaviorTests(unittest.TestCase):
    """頭格字面 + 通配碼錨：+香?30人"""

    def setUp(self):
        reset_word_cache_for_tests()

    def test_head_literal_plus_wildcard_code_anchor(self):
        with _memory_db(
            Word(
                char="香江本人",
                code="4030",
                jyutping="hoeng1 gong2 bun2 jan4",
                finals='["oeng","ong","un","an"]',
                initials='["h","g","b","j"]',
                length=4,
            ),
            Word(
                char="香港人",
                code="430",
                jyutping="hoeng1 gong2 jan4",
                finals='["oeng","ong","an"]',
                initials='["h","g","j"]',
                length=3,
            ),
        ) as db:
            found = _chars(search_words(q="+香?30人", mode="m1", db=db, limit=20))
            self.assertIn("香江本人", found)
            self.assertNotIn("香港人", found)


if __name__ == "__main__":
    unittest.main()
