"""Unified search result sorting (CONTEXT.md §搜尋結果排序)."""

import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ESSAY_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "essay" / "fixtures" / "essay_ranking_sample.txt"
ESSAY_EMPTY_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "essay" / "fixtures" / "essay_empty.txt"
CURATED_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "lexicon" / "fixtures" / "curated_sample.txt"


class EssaySortTierTests(unittest.TestCase):
    def tearDown(self):
        from app.lexicon.curated_index import reset_curated_for_tests
        from app.lexicon.essay_index import reset_essay_for_tests
        from app.lexicon.rime_char_index import reset_rime_char_for_tests

        reset_curated_for_tests()
        reset_essay_for_tests()
        reset_rime_char_for_tests()

    def test_pure_han_before_mixed_literal(self):
        from app.lexicon.essay_index import load_essay_corpus
        from app.models.word import Word
        from app.domain.lexicon.ranking import sort_search_results

        load_essay_corpus(ESSAY_FIXTURE)
        words = [
            Word(char="A片", code="33", jyutping="e1 pin3", length=2),
            Word(char="先生", code="33", jyutping="sin1 saang1", length=2),
        ]
        ordered = [w.char for w in sort_search_results(words)]
        self.assertEqual(ordered[0], "先生")

    def test_essay_frequency_before_curated_when_freq_differs(self):
        from app.lexicon.curated_index import load_curated_common
        from app.lexicon.essay_index import load_essay_corpus
        from app.models.word import Word
        from app.domain.lexicon.ranking import sort_search_results

        load_essay_corpus(ESSAY_FIXTURE)
        load_curated_common(CURATED_FIXTURE)
        words = [
            Word(char="門童", code="20", jyutping="mun4 tung4", length=2),
            Word(char="門前", code="20", jyutping="mun4 cin4", length=2),
        ]
        ordered = [w.char for w in sort_search_results(words)]
        self.assertEqual(ordered[0], "門童")
        self.assertEqual(ordered[1], "門前")

    def test_curated_breaks_tie_when_essay_equal(self):
        from app.lexicon.curated_index import load_curated_common
        from app.lexicon.essay_index import load_essay_corpus, reset_essay_for_tests
        from app.models.word import Word
        from app.domain.lexicon.ranking import sort_search_results

        reset_essay_for_tests()
        load_essay_corpus(ESSAY_EMPTY_FIXTURE)
        load_curated_common(CURATED_FIXTURE)
        words = [
            Word(char="門前", code="20", jyutping="mun4 cin4", length=2),
            Word(char="門童", code="20", jyutping="mun4 tung4", length=2),
        ]
        ordered = [w.char for w in sort_search_results(words)]
        self.assertEqual(ordered[0], "門童")


class WordRankingSignalTests(unittest.TestCase):
    def tearDown(self):
        from app.lexicon.curated_index import reset_curated_for_tests
        from app.lexicon.essay_index import reset_essay_for_tests
        from app.lexicon.rime_char_index import reset_rime_char_for_tests

        reset_curated_for_tests()
        reset_essay_for_tests()
        reset_rime_char_for_tests()

    def test_literal_priority_essay_before_curated_when_freq_differs(self):
        from app.domain.lexicon.ranking import literal_priority_sort_key, search_result_sort_key
        from app.models.word import Word

        w_curated_low = Word(char="門童", code="20", jyutping="mun4 tung4", length=2)
        w_high_essay = Word(char="門前", code="20", jyutping="mun4 cin4", length=2)
        positions = [(0, "門")]

        with patch("app.domain.lexicon.ranking.get_essay_frequency") as gf:
            with patch("app.domain.lexicon.ranking.curated_sort_boost") as cb:
                gf.side_effect = lambda ch: {"門童": 50, "門前": 900}.get(ch, 0)
                cb.side_effect = lambda ch: 1 if ch == "門童" else 0

                self.assertLess(
                    search_result_sort_key(w_high_essay),
                    search_result_sort_key(w_curated_low),
                )
                self.assertLess(
                    literal_priority_sort_key(w_high_essay, positions),
                    literal_priority_sort_key(w_curated_low, positions),
                )

    def test_literal_priority_exact_count_before_flat_tier(self):
        from app.domain.lexicon.ranking import literal_priority_sort_key

        w_more = MagicMock(char="門人", jyutping="mun4 jan4")
        w_less = MagicMock(char="門下", jyutping="mun4 haa5")
        positions = [(0, "門"), (1, "人")]

        self.assertLess(
            literal_priority_sort_key(w_more, positions),
            literal_priority_sort_key(w_less, positions),
        )

    def test_authoritative_reading_sort_key_pron_rank_before_essay(self):
        from app.domain.lexicon.ranking import authoritative_reading_sort_key
        from app.lexicon.rime_char_index import load_rime_char_csv, reset_rime_char_for_tests

        reset_rime_char_for_tests()
        fixture = Path(__file__).resolve().parent.parent / "data" / "rime" / "fixtures" / "char_sample.csv"
        load_rime_char_csv(fixture)

        default_row = SimpleNamespace(char="好", jyutping="hou2", code="2")
        common_row = SimpleNamespace(char="好", jyutping="hou3", code="3")
        self.assertLess(
            authoritative_reading_sort_key(default_row),
            authoritative_reading_sort_key(common_row),
        )

    def test_authoritative_reading_deprioritizes_aa_variant(self):
        from app.domain.lexicon.ranking import authoritative_reading_sort_key

        plain = SimpleNamespace(char="行", jyutping="hang4", code="4")
        aa = SimpleNamespace(char="行", jyutping="haang4", code="4")
        with patch("app.domain.lexicon.ranking.get_essay_frequency", return_value=0):
            with patch(
                "app.domain.lexicon.ranking.pron_rank_sort_value_for_word",
                return_value=0,
            ):
                self.assertLess(
                    authoritative_reading_sort_key(plain),
                    authoritative_reading_sort_key(aa),
                )


class SearchSortIntegrationTests(unittest.TestCase):
    def setUp(self):
        from app.database import Base
        from app.lexicon.curated_index import load_curated_common
        from app.lexicon.essay_index import load_essay_corpus

        load_essay_corpus(ESSAY_FIXTURE)
        load_curated_common(CURATED_FIXTURE)
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def tearDown(self):
        from app.lexicon.curated_index import reset_curated_for_tests
        from app.lexicon.essay_index import reset_essay_for_tests
        from app.utils.word_cache import reset_word_cache_for_tests

        reset_curated_for_tests()
        reset_essay_for_tests()
        reset_word_cache_for_tests()

    def test_pure_digit_search_sorts_by_unified_key(self):
        from app.models.word import Word
        from app.services.query_dispatch import search_words

        with self.Session() as db:
            db.add_all([
                Word(char="A片", code="33", jyutping="e1 pin3", length=2),
                Word(char="門前", code="33", jyutping="mun4 cin4", length=2),
                Word(char="門童", code="33", jyutping="mun4 tung4", length=2),
            ])
            db.commit()
            results = search_words(q="33", mode="m1", db=db, limit=10, offset=0)
            chars = [r["char"] for r in results]
        self.assertEqual(chars[0], "門童")
        self.assertLess(chars.index("門前"), chars.index("A片"))

    def test_mask_search_uses_same_sort_as_pure_digit(self):
        from app.models.word import Word
        from app.services.query_dispatch import search_words

        with self.Session() as db:
            db.add_all([
                Word(
                    char="門", code="2", jyutping="mun4",
                    finals='["un"]', initials='["m"]', length=1,
                ),
                Word(
                    char="門前", code="20", jyutping="mun4 cin4",
                    finals='["un","in"]', initials='["m","c"]', length=2,
                ),
                Word(
                    char="門童", code="20", jyutping="mun4 tung4",
                    finals='["un","ung"]', initials='["m","t"]', length=2,
                ),
            ])
            db.commit()
            results = search_words(q="門0", mode="m2", db=db, limit=10, offset=0)
            chars = [r["char"] for r in results]
        self.assertEqual(chars.index("門童"), 0)

    def test_equals_rhyme_search_sorts_by_essay_frequency(self):
        import json

        from app.models.word import Word
        from app.services.query_dispatch import search_words

        shared_finals = json.dumps(["oeng", "ong"])
        with self.Session() as db:
            db.add_all([
                Word(
                    char="香港", code="22", jyutping="hoeng1 gong2",
                    finals=shared_finals, initials='["h","g"]', length=2,
                ),
                Word(
                    char="香江", code="22", jyutping="hoeng1 gong1",
                    finals=shared_finals, initials='["h","g"]', length=2,
                ),
                Word(
                    char="香島", code="22", jyutping="hoeng1 dou2",
                    finals=json.dumps(["oeng", "ou"]), initials='["h","d"]', length=2,
                ),
            ])
            db.commit()
            results = search_words(q="香港=", mode="m1", db=db, limit=10, offset=0)
            chars = [r["char"] for r in results]
        self.assertEqual(chars[0], "香江")
        self.assertIn("香港", chars)
        self.assertNotIn("香島", chars)

    def test_jyutping_query_search_sorts_by_unified_key(self):
        from app.models.word import Word
        from app.services.query_dispatch import search_words

        with self.Session() as db:
            db.add_all([
                Word(char="門", code="0", jyutping="mun4", length=1),
                Word(char="問", code="3", jyutping="man6", length=1),
                Word(char="門前", code="20", jyutping="mun4 cin4", length=2),
                Word(char="路數", code="24", jyutping="lou6 sou3", length=2),
            ])
            db.commit()
            results = search_words(q="mun4", mode="m1", db=db, limit=10, offset=0)
            chars = [r["char"] for r in results]
        self.assertEqual(chars, ["門"])


if __name__ == "__main__":
    unittest.main()
