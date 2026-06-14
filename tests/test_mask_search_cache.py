"""缺字／韻／聲錨：word_cache 索引路徑與代表查詢語意回歸。"""

import unittest
from unittest.mock import MagicMock

from app.models.word import Word
from app.services.query_dispatch import search_words
from app.utils.word_cache import (
    complete_preload,
    get_mask_index_candidates,
    get_phoneme_index_candidates,
    populate_word_cache_from_rows,
    reset_word_cache_for_tests,
)


class TestMaskIndexCandidates(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def tearDown(self):
        reset_word_cache_for_tests()

    def _populate_ready(self, rows):
        populate_word_cache_from_rows(rows)
        complete_preload()

    def test_literal_prefix_narrows_candidates(self):
        self._populate_ready([
            {"char": "香港", "code": "22", "jyutping": "hoeng1 gong2", "finals": '["oeng","ong"]', "initials": '["h","g"]', "length": 2},
            {"char": "香江", "code": "22", "jyutping": "hoeng1 gong1", "finals": '["oeng","ong"]', "initials": '["h","g"]', "length": 2},
            {"char": "做就", "code": "23", "jyutping": "zou6 zau6", "finals": '["ou","au"]', "initials": '["z","z"]', "length": 2},
        ])
        narrowed = get_mask_index_candidates(2, "香?")
        chars = {row["char"] for row in narrowed}
        self.assertEqual(chars, {"香港", "香江"})

    def test_phoneme_index_narrows_final_anchor(self):
        self._populate_ready([
            {"char": "做就", "code": "23", "jyutping": "zou6 zau6", "finals": '["ou","au"]', "initials": '["z","z"]', "length": 2},
            {"char": "做得", "code": "23", "jyutping": "zou6 dak1", "finals": '["ou","ak"]', "initials": '["z","d"]', "length": 2},
        ])
        db = MagicMock()
        rows = get_phoneme_index_candidates(2, 1, "就", "final", db)
        chars = {row["char"] for row in rows}
        self.assertEqual(chars, {"做就"})

    def test_code_digit_slot_narrows_candidates(self):
        self._populate_ready([
            {"char": "門人", "code": "00", "jyutping": "mun4 jan4", "finals": '["un","an"]', "initials": '["m","j"]', "length": 2},
            {"char": "門下", "code": "02", "jyutping": "mun4 haa5", "finals": '["un","a"]', "initials": '["m","h"]', "length": 2},
        ])
        narrowed = get_mask_index_candidates(2, "門0")
        chars = [row["char"] for row in narrowed]
        self.assertEqual(chars, ["門人"])


class TestRepresentativeMaskQueriesWithCache(unittest.TestCase):
    """代表查詢：cache+索引路徑須與 DB fallback 語意一致。"""

    def setUp(self):
        reset_word_cache_for_tests()

    def tearDown(self):
        reset_word_cache_for_tests()

    def _session(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.database import Base

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return sessionmaker(bind=engine)()

    def _fixture_rows(self):
        return [
            Word(char="香港", code="22", jyutping="hoeng1 gong2", finals='["oeng","ong"]', initials='["h","g"]', length=2),
            Word(char="香江", code="22", jyutping="hoeng1 gong1", finals='["oeng","ong"]', initials='["h","g"]', length=2),
            Word(char="香島", code="22", jyutping="hoeng1 dou2", finals='["oeng","ou"]', initials='["h","d"]', length=2),
            Word(char="做就", code="23", jyutping="zou6 zau6", finals='["ou","au"]', initials='["z","z"]', length=2),
            Word(char="做得", code="23", jyutping="zou6 dak1", finals='["ou","ak"]', initials='["z","d"]', length=2),
        ]

    def _chars(self, payload):
        return [r["char"] for r in payload]

    def test_representative_queries_match_db_fallback(self):
        with self._session() as session:
            session.add_all(self._fixture_rows())
            session.commit()
            cache_rows = [
                {
                    "char": w.char,
                    "code": w.code,
                    "jyutping": w.jyutping,
                    "finals": w.finals,
                    "initials": w.initials,
                    "length": w.length,
                }
                for w in self._fixture_rows()
            ]

            cases = ("香??", "香=?", "?就=", "??就=")
            for q in cases:
                reset_word_cache_for_tests()
                baseline = self._chars(search_words(q=q, mode="m1", db=session, limit=50, offset=0))

                populate_word_cache_from_rows(cache_rows)
                complete_preload()
                indexed = self._chars(search_words(q=q, mode="m1", db=session, limit=50, offset=0))
                self.assertEqual(indexed, baseline, msg=f"query {q!r}")


if __name__ == "__main__":
    unittest.main()
