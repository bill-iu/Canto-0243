import unittest
from pathlib import Path
from unittest.mock import patch

FIXTURE = Path(__file__).resolve().parent.parent / "data" / "essay" / "fixtures" / "essay_sample.txt"


class EssayCorpusTests(unittest.TestCase):
    def tearDown(self):
        from app.lexicon.essay_index import reset_essay_for_tests

        reset_essay_for_tests()

    def test_essay_corpus_loads_word_frequency(self):
        from app.lexicon.essay_index import get_essay_frequency, load_essay_corpus

        count = load_essay_corpus(FIXTURE)
        self.assertEqual(count, 4)
        self.assertGreater(get_essay_frequency("開心"), get_essay_frequency("走你好"))
        self.assertEqual(get_essay_frequency("未知詞"), 0)


class EssaySearchRankingTests(unittest.TestCase):
    def setUp(self):
        from app.lexicon.essay_index import load_essay_corpus

        load_essay_corpus(FIXTURE)

    def tearDown(self):
        from app.lexicon.essay_index import reset_essay_for_tests
        from app.utils.word_cache import reset_word_cache_for_tests

        reset_essay_for_tests()
        reset_word_cache_for_tests()

    def test_mask_search_ranks_higher_essay_frequency_first(self):
        """Same match tier -> more common essay word sorts first (門童 before 門前 when 童 freq higher)."""
        from pathlib import Path

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.database import Base
        from app.lexicon.essay_index import load_essay_corpus, reset_essay_for_tests
        from app.models.word import Word
        from app.routers.word import search_words

        ranking_fixture = Path(__file__).resolve().parent.parent / "data" / "essay" / "fixtures" / "essay_ranking_sample.txt"
        reset_essay_for_tests()
        load_essay_corpus(ranking_fixture)

        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as session:
            session.add_all([
                Word(char="門", code="2", jyutping="mun4", finals='["un"]', initials='["m"]', length=1),
                Word(char="門前", code="20", jyutping="mun4 cin4", finals='["un","in"]', initials='["m","c"]', length=2),
                Word(char="門童", code="20", jyutping="mun4 tung4", finals='["un","ung"]', initials='["m","t"]', length=2),
            ])
            session.commit()
            results = search_words(q="門0", mode="m2", db=session, limit=10, offset=0)
            chars = [item["char"] for item in results]

        self.assertIn("門前", chars)
        self.assertIn("門童", chars)
        self.assertLess(chars.index("門童"), chars.index("門前"))

    def test_essay_frequency_does_not_open_injection_gate(self):
        """Essay freq is sort-only; lexicon miss still no inject."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        from app.database import Base
        from app.lexicon.essay_index import load_essay_corpus
        from app.services.word_ensure_service import ensure_word_in_db
        from tests.test_lexicon_ensure import FakeLexiconPort

        load_essay_corpus(FIXTURE)
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            with patch(
                "app.utils.syllable_reading.compose_lexicon_entries_from_rime",
                return_value=[],
            ):
                rows = ensure_word_in_db(db, "開心", lexicon=FakeLexiconPort({}))
            self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
