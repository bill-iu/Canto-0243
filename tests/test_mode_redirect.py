"""搜尋模式轉接 — 近反義模式 + 近反義關係查詢語法。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.relations.compound_ant import reset_compound_ant_snapshot_for_tests
from app.models.word import Word, WordRelation
from app.services.query_dispatch import SearchContext, execute_search
from app.services.query_parse import is_relation_syntax_query, mode_redirect_hint


class IsRelationSyntaxQueryTests(unittest.TestCase):
    def test_compound_and_lookup(self):
        self.assertTrue(is_relation_syntax_query("!!"))
        self.assertTrue(is_relation_syntax_query("~~"))
        self.assertTrue(is_relation_syntax_query("~開心"))
        self.assertTrue(is_relation_syntax_query("!你"))
        self.assertTrue(is_relation_syntax_query("!與!"))
        self.assertTrue(is_relation_syntax_query("33!!你"))

    def test_plain_chars_not_relation_syntax(self):
        self.assertFalse(is_relation_syntax_query("開心"))
        self.assertFalse(is_relation_syntax_query("香??"))
        self.assertFalse(is_relation_syntax_query("23"))


class SynModeRedirectTests(unittest.TestCase):
    def setUp(self):
        reset_compound_ant_snapshot_for_tests()

    def tearDown(self):
        reset_compound_ant_snapshot_for_tests()

    def _session_with_seed(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all([
            Word(id=1, char="開心", code="33", jyutping="hoi1 sam1", length=2),
            Word(id=2, char="愉快", code="33", jyutping="jyu4 faai3", length=2),
            Word(id=3, char="傷心", code="33", jyutping="soeng1 sam1", length=2),
            Word(id=5, char="生死", code="33", jyutping="saang1 sei2", length=2),
            Word(id=10, char="生", code="3", jyutping="saang1", length=1),
            Word(id=11, char="死", code="3", jyutping="sei2", length=1),
        ])
        session.add_all([
            WordRelation(word_id=1, related_id=2, relation_type="syn", source="test"),
            WordRelation(word_id=1, related_id=3, relation_type="ant", source="test"),
            WordRelation(word_id=10, related_id=11, relation_type="ant", source="test"),
        ])
        session.commit()
        return session

    def test_syn_mode_relation_lookup_redirects(self):
        session = self._session_with_seed()
        try:
            result = execute_search(
                SearchContext(
                    q="!開心",
                    code=None,
                    char=None,
                    mode="syn",
                    limit=20,
                    offset=0,
                    db=session,
                )
            )
            chars = [r["char"] for r in result.items]
            self.assertEqual(chars, ["傷心"])
            self.assertEqual(result.effective_mode, "m1")
            self.assertEqual(result.hint, mode_redirect_hint("m1"))
        finally:
            session.close()

    def test_syn_mode_compound_redirects_with_fallback_m2(self):
        session = self._session_with_seed()
        try:
            result = execute_search(
                SearchContext(
                    q="!!",
                    code=None,
                    char=None,
                    mode="syn",
                    limit=50,
                    offset=0,
                    db=session,
                    fallback_0243_mode="m2",
                )
            )
            chars = [r["char"] for r in result.items]
            self.assertIn("生死", chars)
            self.assertEqual(result.effective_mode, "m2")
            self.assertEqual(result.hint, mode_redirect_hint("m2"))
        finally:
            session.close()

    def test_syn_mode_plain_chars_stays_pool(self):
        session = self._session_with_seed()
        try:
            result = execute_search(
                SearchContext(
                    q="開心",
                    code=None,
                    char=None,
                    mode="syn",
                    limit=20,
                    offset=0,
                    db=session,
                )
            )
            self.assertIsNone(result.effective_mode)
            self.assertIsNone(result.hint)
            self.assertTrue(any(r.get("relation") == "syn" for r in result.items))
        finally:
            session.close()

    def test_syn_redirect_resets_offset(self):
        session = self._session_with_seed()
        try:
            result = execute_search(
                SearchContext(
                    q="!!",
                    code=None,
                    char=None,
                    mode="syn",
                    limit=1,
                    offset=99,
                    db=session,
                )
            )
            self.assertGreater(len(result.items), 0)
            self.assertEqual(result.effective_mode, "m1")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
