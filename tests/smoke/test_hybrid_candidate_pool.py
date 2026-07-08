"""碼夾 hybrid 候選池不可被 2000 上限截斷（例：39起 含 飛起／飛機）。"""
from __future__ import annotations

import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.word import Word  # noqa: F401
from app.services.query_dispatch import QueryEngine, SearchContext

REPO_ROOT = Path(__file__).resolve().parents[2]
LYRICS_DB = REPO_ROOT / "lyrics.db"


@unittest.skipUnless(LYRICS_DB.is_file(), "lyrics.db required")
class HybridCandidatePoolTests(unittest.TestCase):
    def test_39起_includes_tail_rhyme_matches_beyond_2000_bucket(self):
        engine = create_engine(f"sqlite:///{LYRICS_DB.as_posix()}")
        Session = sessionmaker(bind=engine)
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