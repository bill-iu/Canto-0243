"""缺字型查詢執行 registry — execute_match_spec 僅收 MatchSpec。"""
from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.mask_family_normalize import build_mask_family_match_spec, normalize_mask_family_parsed
from app.services.position_match import execute_match_spec, execute_mask_family_search
from app.services.query_dispatch import search_words
from app.services.query_parse import parse_query


class ExecuteMatchSpecTests(unittest.TestCase):
    def _session_with_words(self, words):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        session = Session()
        session.add_all(words)
        session.commit()
        return session

    def test_registry_mask_query_matches_legacy_wrapper(self):
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
            parsed = normalize_mask_family_parsed(parse_query("門0"))
            spec = build_mask_family_match_spec(parsed)
            direct = execute_match_spec(
                spec, code=None, mode="m1", limit=10, offset=0, db=session
            )
            legacy = execute_mask_family_search(
                parsed, code=None, mode="m1", limit=10, offset=0, db=session
            )
            self.assertEqual(
                [r.get("char") for r in direct.items if r.get("result_type") == "word"],
                [r.get("char") for r in legacy.items if r.get("result_type") == "word"],
            )
        finally:
            session.close()

    def test_dispatch_uses_execute_match_spec_path(self):
        from app.utils.word_cache import complete_preload, populate_word_cache_from_rows, reset_word_cache_for_tests

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
