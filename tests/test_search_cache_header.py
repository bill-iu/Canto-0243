"""X-Search-Cache header on position-type queries."""

import unittest

from fastapi.testclient import TestClient

from app.utils.word_cache import complete_preload, populate_word_cache_from_rows, reset_word_cache_for_tests
from main import app


class TestSearchCacheHeader(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()

    def tearDown(self):
        reset_word_cache_for_tests()

    def test_rhyme_anchor_reports_fallback_when_cache_not_ready(self):
        client = TestClient(app)
        with client as c:
            # Need DB - TestClient uses real app DB
            res = c.get("/words/search/", params={"q": "?就=", "mode": "m1", "limit": 5})
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.headers.get("X-Search-Cache"), "fallback")

    def test_rhyme_anchor_reports_ready_when_cache_loaded(self):
        from app.database import SessionLocal
        from app.models.word import Word

        db = SessionLocal()
        try:
            rows = (
                db.query(
                    Word.char,
                    Word.code,
                    Word.jyutping,
                    Word.finals,
                    Word.initials,
                    Word.length,
                )
                .filter(Word.length <= 3)
                .limit(500)
                .all()
            )
        finally:
            db.close()
        populate_word_cache_from_rows(rows)
        complete_preload()

        client = TestClient(app)
        res = client.get("/words/search/", params={"q": "?就=", "mode": "m1", "limit": 5})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("X-Search-Cache"), "ready")


if __name__ == "__main__":
    unittest.main()
