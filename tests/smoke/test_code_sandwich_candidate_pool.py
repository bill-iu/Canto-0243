"""碼夾等號候選池不可被 2000 上限截斷（例：39起 含 飛起／飛機）。"""
from __future__ import annotations

import unittest

from app.models.word import Word  # noqa: F401
from app.services.query_dispatch import QueryEngine, SearchContext

from tests.smoke.helpers import LYRICS_DB, lyrics_sessionmaker


@unittest.skipUnless(LYRICS_DB.is_file(), "lyrics.db required")
class CodeSandwichCandidatePoolTests(unittest.TestCase):
    def test_39起_includes_tail_rhyme_matches_beyond_2000_bucket(self):
        Session = lyrics_sessionmaker()
        with Session() as db:
            result = QueryEngine().execute(
                SearchContext(
                    q="39起",
                    code=None,
                    char=None,
                    mode="m1",
                    limit=500,
                    offset=0,
                    db=db,
                )
            )
        words = [row["char"] for row in result.items]
        self.assertIn("飛起", words)
        self.assertIn("飛機", words)


if __name__ == "__main__":
    unittest.main()