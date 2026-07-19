"""韻／聲錨冷路徑須用語意完整候選宇宙（ADR-0046 §4／CONTEXT）。"""
from __future__ import annotations

import unittest

from tests.smoke.helpers import LYRICS_DB, lyrics_sessionmaker


@unittest.skipUnless(LYRICS_DB.is_file(), "lyrics.db required")
class RhymeAnchorColdBucketTests(unittest.TestCase):
    def test_就_equals_includes_literal_and_late_rhyme_when_cache_cold(self):
        """cache 未暖時唔因 LIMIT 2000 漏「就」／「后」（char 序喺截斷之後）。"""
        from app.services.query_dispatch import QueryEngine, SearchContext
        from app.utils.word_cache import is_word_cache_ready, reset_word_cache_for_tests

        reset_word_cache_for_tests()
        self.assertFalse(is_word_cache_ready())

        Session = lyrics_sessionmaker()
        with Session() as db:
            result = QueryEngine().execute(
                SearchContext(
                    q="就=",
                    code=None,
                    char=None,
                    mode="m1",
                    limit=5000,
                    offset=0,
                    db=db,
                )
            )
        words = {row["char"] for row in result.items}
        self.assertIn("就", words)
        self.assertIn("后", words)
        self.assertGreaterEqual(len(words), 500)


if __name__ == "__main__":
    unittest.main()
