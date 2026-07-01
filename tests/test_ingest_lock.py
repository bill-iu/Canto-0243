"""ingest singleton lock tests."""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from ingest.ingest_lock import IngestLockError, acquire_ingest_lock, release_ingest_lock


class IngestLockTests(unittest.TestCase):
    def test_second_acquire_raises_while_holder_alive(self):
        lock_dir = Path(self._testMethodName)
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

    def test_stale_lock_replaced_when_pid_dead(self):
        lock_dir = Path(self._testMethodName + "2")
        lock_dir.mkdir(exist_ok=True)
        try:
            stale = lock_dir / "build-db.lock"
            stale.write_text("999999\n", encoding="utf-8")
            with patch("ingest.ingest_lock._pid_alive", return_value=False):
                path = acquire_ingest_lock("build-db", lock_dir=lock_dir)
            self.assertEqual(path, stale)
            self.assertIn(str(os.getpid()), stale.read_text(encoding="utf-8"))
            release_ingest_lock(path)
        finally:
            for f in lock_dir.glob("*.lock"):
                f.unlink(missing_ok=True)
            lock_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
