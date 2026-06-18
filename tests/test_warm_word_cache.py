"""Portable 詞庫快取預暖 — 公開 CLI 行為。"""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.utils.word_cache import (
    complete_preload,
    get_word_cache_stats,
    is_word_cache_ready,
    reset_word_cache_for_tests,
    try_restore_word_cache_from_disk,
)
from scripts.warm_word_cache import warm_word_cache


def _memory_db_path(tmp: Path) -> Path:
    db_path = tmp / "lyrics.db"
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    session.add(
        Word(
            char="香港",
            code="33",
            jyutping="hoeng1 gong2",
            finals='["oeng","ong"]',
            initials='["h","g"]',
            length=2,
        )
    )
    session.commit()
    session.close()
    engine.dispose()
    return db_path


class WarmWordCacheTests(unittest.TestCase):
    def setUp(self):
        reset_word_cache_for_tests()
        self._prev_disk = os.environ.get("WORD_CACHE_DISK")
        os.environ["WORD_CACHE_DISK"] = "1"

    def tearDown(self):
        reset_word_cache_for_tests()
        if self._prev_disk is None:
            os.environ.pop("WORD_CACHE_DISK", None)
        else:
            os.environ["WORD_CACHE_DISK"] = self._prev_disk

    def test_warm_writes_snapshot_restorable_after_db_moves(self):
        """預暖快照綁內容唔綁路徑 — Portable 解壓後仍可還原。"""
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            root_a = Path(tmp_a)
            root_b = Path(tmp_b)
            _memory_db_path(root_a)
            cache_path = warm_word_cache(root=root_a)
            self.assertTrue(cache_path.is_file())

            shutil.copy2(root_a / "lyrics.db", root_b / "lyrics.db")
            shutil.copytree(root_a / ".cache", root_b / ".cache")

            reset_word_cache_for_tests()
            self.assertTrue(try_restore_word_cache_from_disk(db_path=root_b / "lyrics.db"))
            complete_preload()
            self.assertTrue(is_word_cache_ready())
            self.assertEqual(get_word_cache_stats()["total_entries"], 1)


if __name__ == "__main__":
    unittest.main()
