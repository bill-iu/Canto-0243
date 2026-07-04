"""Regression: guide examples that once returned 0 results (scripts/check_guide_examples.py)."""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("READINESS_GATE_ENFORCE", "0")

from app.database import SessionLocal
from app.services.query_dispatch import search_words


GUIDE_ZERO_CASES = (
    "?4困=4潦=9倒=",
    "!你",
    "33!開心",
    "!與!",
    "~與~",
)


class GuideExampleQueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = SessionLocal()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()

    def test_guide_examples_return_results(self) -> None:
        for q in GUIDE_ZERO_CASES:
            with self.subTest(q=q):
                items = search_words(q=q, mode="m1", limit=5, offset=0, db=self.db)
                self.assertTrue(items, f"expected results for {q!r}")


if __name__ == "__main__":
    unittest.main()