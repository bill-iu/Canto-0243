"""API smoke — explain、search 排序、word_detail 形狀。"""
from __future__ import annotations

import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.lexicon.ranking import sort_search_results
from app.lexicon.essay_index import load_essay_corpus, reset_essay_for_tests
from app.models.word import Word
from app.services.query_dispatch import search_words
from app.services.query_explain import explain_query


ESSAY_FIXTURE = (
    Path(__file__).resolve().parents[2] / "data" / "essay" / "fixtures" / "essay_ranking_sample.txt"
)


class ApiSmokeTests(unittest.TestCase):
    def tearDown(self):
        reset_essay_for_tests()

    def test_query_explain_plus_anchor_summary(self):
        result = explain_query("23+好=")
        self.assertEqual(result.kind, "plus_anchor")
        self.assertIn("同韻", result.summary or "")
        self.assertIn("好", result.summary or "")

    def test_search_sort_pure_han_before_mixed(self):
        load_essay_corpus(ESSAY_FIXTURE)
        words = [
            Word(char="A片", code="33", jyutping="e1 pin3", length=2),
            Word(char="先生", code="33", jyutping="sin1 saang1", length=2),
        ]
        ordered = [w.char for w in sort_search_results(words)]
        self.assertEqual(ordered[0], "先生")

    def test_search_words_character_detail_shape(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as session:
            session.add_all([
                Word(char="字", code="23", jyutping="zi6", length=1),
                Word(char="子", code="23", jyutping="zi2", length=1),
            ])
            session.commit()
            payload = search_words(q="字", db=session, limit=20, offset=0)

        self.assertEqual(payload[0]["result_type"], "code")
        self.assertEqual(payload[1]["result_type"], "jyutping")
        word_chars = [item["char"] for item in payload if item.get("result_type") == "word"]
        self.assertEqual(word_chars[0], "字")


if __name__ == "__main__":
    unittest.main()
