"""探針暖機契約 — 對齊就緒閘解鎖（scripts/guide_probe_readiness.py）。"""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DB = REPO_ROOT / "tests" / "fixtures" / "lyrics.db"

os.environ["READINESS_GATE_ENFORCE"] = "0"

from app.services.query_dispatch import search_words  # noqa: E402
from app.utils.word_cache import is_word_cache_ready, reset_word_cache_for_tests  # noqa: E402
from scripts.guide_probe_readiness import (  # noqa: E402
    READINESS_PROBE_QUERY,
    warm_guide_probe_readiness,
)


class GuideProbeReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not FIXTURE_DB.is_file():
            raise unittest.SkipTest(f"missing fixture db: {FIXTURE_DB}")
        engine = create_engine(f"sqlite:///{FIXTURE_DB.as_posix()}")
        cls.db = sessionmaker(bind=engine)()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()

    def setUp(self) -> None:
        reset_word_cache_for_tests()

    def tearDown(self) -> None:
        reset_word_cache_for_tests()

    def test_warm_enables_word_cache_and_readiness_probe(self) -> None:
        self.assertFalse(is_word_cache_ready())
        warm_guide_probe_readiness(self.db)
        self.assertTrue(is_word_cache_ready())
        items = search_words(
            q=READINESS_PROBE_QUERY,
            mode="m1",
            limit=5,
            offset=0,
            db=self.db,
        )
        self.assertTrue(items)


if __name__ == "__main__":
    unittest.main()