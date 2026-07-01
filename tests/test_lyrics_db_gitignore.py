"""lyrics.db git tracking policy (CONTEXT § 詞條庫測試快照)."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def _git_check_ignore(*paths: str) -> set[str]:
    ignored: set[str] = set()
    for path in paths:
        proc = subprocess.run(
            ["git", "check-ignore", "-q", path],
            cwd=REPO,
            check=False,
        )
        if proc.returncode == 0:
            ignored.add(path)
    return ignored


class LyricsDbGitignoreTests(unittest.TestCase):
    def test_root_lyrics_db_is_gitignored(self):
        ignored = _git_check_ignore("lyrics.db")
        self.assertIn("lyrics.db", ignored)

    def test_fixture_lyrics_db_is_not_gitignored(self):
        ignored = _git_check_ignore("tests/fixtures/lyrics.db")
        self.assertNotIn("tests/fixtures/lyrics.db", ignored)

    def test_fixture_lyrics_db_exists_with_words(self):
        import sqlite3

        path = REPO / "tests" / "fixtures" / "lyrics.db"
        self.assertTrue(path.is_file(), "run build-db fixture generator or commit tests/fixtures/lyrics.db")
        with sqlite3.connect(path) as conn:
            n = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
        self.assertGreater(n, 0)


if __name__ == "__main__":
    unittest.main()
