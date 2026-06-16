import unittest
from pathlib import Path

RIME_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "rime" / "fixtures" / "char_sample.csv"
CURATED_FIXTURE = Path(__file__).resolve().parent.parent / "data" / "lexicon" / "fixtures" / "curated_sample.txt"


class PronRankSortTests(unittest.TestCase):
    def tearDown(self):
        from app.lexicon.rime_char_index import reset_rime_char_for_tests

        reset_rime_char_for_tests()

    def test_pron_rank_default_sorts_before_common_for_same_char(self):
        """預設 > 常用 > 罕見 (lower sort value = higher priority)."""
        from app.lexicon.rime_char_index import load_rime_char_csv, pron_rank_sort_value

        load_rime_char_csv(RIME_FIXTURE)
        self.assertLess(pron_rank_sort_value("好", "hou2"), pron_rank_sort_value("好", "hou3"))
        self.assertEqual(pron_rank_sort_value("好", "hou2"), 0)
        self.assertEqual(pron_rank_sort_value("好", "hou3"), 1)


class CuratedCommonTests(unittest.TestCase):
    def tearDown(self):
        from app.lexicon.curated_index import reset_curated_for_tests

        reset_curated_for_tests()

    def test_curated_list_marks_common_words(self):
        from app.lexicon.curated_index import is_curated_common, load_curated_common

        n = load_curated_common(CURATED_FIXTURE)
        self.assertEqual(n, 2)
        self.assertTrue(is_curated_common("門童"))
        self.assertFalse(is_curated_common("門前"))


class CuratedSearchRankingTests(unittest.TestCase):
    def tearDown(self):
        from app.lexicon.curated_index import reset_curated_for_tests
        from app.lexicon.essay_index import reset_essay_for_tests
        from app.utils.word_cache import reset_word_cache_for_tests

        reset_curated_for_tests()
        reset_essay_for_tests()
        reset_word_cache_for_tests()

    def test_curated_word_sorts_before_non_curated_when_essay_tied(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.database import Base
        from app.lexicon.curated_index import load_curated_common
        from app.lexicon.essay_index import load_essay_corpus, reset_essay_for_tests
        from app.models.word import Word
        from app.routers.word import search_words

        essay_empty = Path(__file__).resolve().parent.parent / "data" / "essay" / "fixtures" / "essay_empty.txt"
        reset_essay_for_tests()
        load_essay_corpus(essay_empty)
        load_curated_common(CURATED_FIXTURE)

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            db.add_all([
                Word(char="門", code="2", jyutping="mun4", finals='["un"]', length=1),
                Word(char="門前", code="20", jyutping="mun4 cin4", finals='["un","in"]', length=2),
                Word(char="門童", code="20", jyutping="mun4 tung4", finals='["un","ung"]', length=2),
            ])
            db.commit()
            results = search_words(q="門0", mode="m2", db=db, limit=10, offset=0)
            chars = [r["char"] for r in results]

        self.assertLess(chars.index("門童"), chars.index("門前"))


if __name__ == "__main__":
    unittest.main()
