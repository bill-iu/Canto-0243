"""Guide fixture inject — 窮困潦倒 等須入 words，否則指南 6 條零結果。"""

from __future__ import annotations

import os
import unittest

os.environ.setdefault("READINESS_GATE_ENFORCE", "0")

from app.database import SessionLocal
from app.models.word import Word
from app.services.query_dispatch import search_words
from scripts.guide_probe_readiness import ensure_guide_fixture_words, warm_guide_probe_readiness


ZERO_RESULT_REGRESSIONS = (
    "04困=49倒=",
    "04^困49^倒",
    "?4困=4潦=9倒=",
    "窮困?倒=",
    "^窮困?倒",
    "?^困潦倒",
)


class GuideFixtureZeroResultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.db = SessionLocal()
        warm_guide_probe_readiness(cls.db)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()

    def test_fixture_word_present(self) -> None:
        self.assertTrue(
            self.db.query(Word.id).filter(Word.char == "窮困潦倒").first(),
            "窮困潦倒 must be in words after guide warm",
        )

    def test_ensure_idempotent(self) -> None:
        self.assertEqual(ensure_guide_fixture_words(self.db), 0)

    def test_former_zero_result_queries_hit(self) -> None:
        for q in ZERO_RESULT_REGRESSIONS:
            with self.subTest(q=q):
                items = search_words(
                    q=q, code=None, char=None, mode="m1", limit=1, offset=0, db=self.db
                )
                self.assertTrue(items, f"{q!r} returned 0")


if __name__ == "__main__":
    unittest.main()
