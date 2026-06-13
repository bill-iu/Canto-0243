"""Tests for syllable-composed readings (音節拼接讀音)."""

import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.lexicon.rime_char_index import load_rime_char_csv, reset_rime_char_for_tests
from app.lexicon.static_index import reset_lexicon_for_tests
from app.models.word import Word
from app.services.query_engine import search_words
from app.services.word_ensure_service import ensure_word_in_db
from app.services.word_lookup_executor import WordLookupExecutor
from app.utils.jyutping_codec import get_0243_code
from app.utils.syllable_reading import compose_lexicon_entries_from_rime
from app.utils.word_cache import reset_word_cache_for_tests

FIXTURE_CSV = Path(__file__).resolve().parent.parent / "data" / "rime" / "fixtures" / "char_sample.csv"


class FakeLexiconPort:
    def __init__(self, entries_by_char):
        self._entries = entries_by_char

    def ensure_loaded(self) -> None:
        pass

    def get_entries(self, char: str):
        return list(self._entries.get(char, []))


class SyllableReadingTests(unittest.TestCase):
    def setUp(self):
        reset_rime_char_for_tests()
        reset_lexicon_for_tests()
        reset_word_cache_for_tests()
        load_rime_char_csv(FIXTURE_CSV)

    def tearDown(self):
        reset_rime_char_for_tests()
        reset_lexicon_for_tests()
        reset_word_cache_for_tests()
        from app.lexicon.rime_char_index import DEFAULT_CHAR_CSV, load_rime_char_csv

        load_rime_char_csv(DEFAULT_CHAR_CSV)

    def test_compose_two_char_from_rime(self):
        entries = compose_lexicon_entries_from_rime("你好")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].jyutping, "nei5 hou2")
        self.assertEqual(entries[0].code, get_0243_code("nei5 hou2"))

    def test_compose_fails_when_char_missing(self):
        self.assertEqual(compose_lexicon_entries_from_rime("你X"), [])

    def test_ensure_injects_composed_multi_char(self):
        port = FakeLexiconPort({})
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            rows = ensure_word_in_db(db, "你好", lexicon=port)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].jyutping, "nei5 hou2")
            self.assertEqual(rows[0].code, get_0243_code("nei5 hou2"))

    def test_word_lookup_shows_composed_reading(self):
        port = FakeLexiconPort({})
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            executor = WordLookupExecutor(db)
            results = executor.lookup("你好", None, "m1", 10, 0)
            self.assertTrue(results)
            expected_code = get_0243_code("nei5 hou2")
            header_codes = [r for r in results if r.get("result_type") == "code"]
            self.assertTrue(any(r["char"] == expected_code for r in header_codes))
            word_rows = [r for r in results if r.get("result_type") == "word"]
            self.assertTrue(any(r["char"] == "你好" for r in word_rows))


class SyllableRhymeLookupIntegrationTests(unittest.TestCase):
    """Real DB: 催是 composed lookup and 03=催 anchor."""

    def tearDown(self):
        reset_rime_char_for_tests()
        reset_lexicon_for_tests()
        reset_word_cache_for_tests()
        from app.lexicon.rime_char_index import DEFAULT_CHAR_CSV, load_rime_char_csv

        load_rime_char_csv(DEFAULT_CHAR_CSV)

    def test_cui_shi_lookup_and_equals_anchor(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            db.add(
                Word(
                    char="隨時",
                    code="00",
                    jyutping="ceoi4 si4",
                    finals='["oi", "i"]',
                    initials='["c", "s"]',
                    length=2,
                )
            )
            db.commit()

            lookup = search_words(q="催是", mode="m1", db=db, limit=10, offset=0)
            lookup_words = [r for r in lookup if r.get("result_type") == "word"]
            self.assertEqual(len(lookup_words), 1)
            self.assertEqual(lookup_words[0]["char"], "催是")
            self.assertEqual(lookup_words[0]['jyutping'], "ceoi1 si6")
            self.assertEqual(lookup_words[0]['code'], "32")

            eq_cui_shi = search_words(q="03=催是", mode="m1", db=db, limit=20, offset=0)
            eq_sui_shi = search_words(q="03=隨時", mode="m1", db=db, limit=20, offset=0)
            cui_shi_chars = [r["char"] for r in eq_cui_shi if r.get("result_type") == "word"]
            sui_shi_chars = [r["char"] for r in eq_sui_shi if r.get("result_type") == "word"]
            self.assertEqual(cui_shi_chars[:10], sui_shi_chars[:10])


if __name__ == "__main__":
    unittest.main()
