"""詞庫收錄決策 + ingest lock smoke。"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app.domain.lexicon.admission import AdmissionSource, resolve_admission
from app.lexicon.static_index import LexiconEntry
from ingest.ingest_lock import IngestLockError, acquire_ingest_lock, release_ingest_lock


class FakeLexiconPort:
    def __init__(self, *, rime_by_char=None, word_by_text=None):
        self._rime = rime_by_char or {}
        self._word = word_by_text or {}

    def ensure_loaded(self) -> None:
        pass

    def get_rime_char_entries(self, char: str):
        return list(self._rime.get(char, []))

    def get_word_lexicon_entries(self, text: str):
        return list(self._word.get(text, []))


class LexiconSmokeTests(unittest.TestCase):
    def test_multi_char_lexicon_admission(self):
        port = FakeLexiconPort(
            word_by_text={
                "香港": [LexiconEntry(char="香港", jyutping="hoeng1 gong2", code="12")],
            }
        )
        result = resolve_admission("香港", lexicon=port)
        self.assertEqual(result.source, AdmissionSource.MULTI_CHAR_LEXICON)
        self.assertTrue(result.can_inject)

    def test_garbage_literal_cannot_inject(self):
        port = FakeLexiconPort()
        with patch(
            "app.domain.lexicon.admission.compose_lexicon_entries_from_rime",
            return_value=[],
        ):
            result = resolve_admission("走你好", lexicon=port)
        self.assertEqual(result.source, AdmissionSource.NONE)
        self.assertFalse(result.can_inject)

    def test_ingest_lock_rejects_live_holder(self):
        lock_dir = Path("ingest_lock_smoke")
        lock_dir.mkdir(exist_ok=True)
        try:
            stale = lock_dir / "build-db.lock"
            stale.write_text("12345\n", encoding="utf-8")
            with patch("ingest.ingest_lock._pid_alive", return_value=True):
                with self.assertRaises(IngestLockError):
                    acquire_ingest_lock("build-db", lock_dir=lock_dir)
        finally:
            for f in lock_dir.glob("*.lock"):
                f.unlink(missing_ok=True)
            lock_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
