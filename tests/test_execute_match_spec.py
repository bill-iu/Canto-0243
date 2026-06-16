"""缺字型查詢執行 registry — execute_match_spec 僅收 MatchSpec。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.position_match import execute_match_spec
from app.services.query_dispatch import search_words
from app.services.query_parse import normalize_to_match_spec, parse_query
from app.utils.word_cache import complete_preload, populate_word_cache_from_rows, reset_word_cache_for_tests


class ExecuteMatchSpecTests(unittest.TestCase):
    def _session_with_words(self, words):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all(words)
        session.commit()
        return session

    def test_registry_mask_query_via_normalize(self):
        session = self._session_with_words(
            [
                Word(
                    char="門口",
                    code="10",
                    jyutping="mun4 hau2",
                    finals='["un","au"]',
                    initials='["m","h"]',
                    length=2,
                ),
            ]
        )
        try:
            spec = normalize_to_match_spec(parse_query("門0"))
            result = execute_match_spec(
                spec, code=None, mode="m1", limit=10, offset=0, db=session
            )
            words = [r.get("char") for r in result.items if r.get("result_type") == "word"]
            self.assertIn("門口", words)
        finally:
            session.close()

    def test_dispatch_uses_execute_match_spec_path(self):
        reset_word_cache_for_tests()
        session = self._session_with_words(
            [
                Word(
                    char="好我",
                    code="34",
                    jyutping="hou2 ngo5",
                    finals='["ou","o"]',
                    initials='["h","ng"]',
                    length=2,
                ),
            ]
        )
        try:
            populate_word_cache_from_rows(
                [
                    {
                        "char": "好我",
                        "code": "34",
                        "jyutping": "hou2 ngo5",
                        "finals": '["ou","o"]',
                        "initials": '["h","ng"]',
                        "length": 2,
                    }
                ]
            )
            complete_preload()
            results = search_words(q="34=我", mode="m1", db=session, limit=10, offset=0)
            words = [r["char"] for r in results if r.get("result_type") == "word"]
            self.assertIn("好我", words)
        finally:
            session.close()
            reset_word_cache_for_tests()


if __name__ == "__main__":
    unittest.main()