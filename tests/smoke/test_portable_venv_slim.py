"""C11-A: portable venv denylist slim."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.portable_venv_slim import count_files, slim_portable_venv, win_lib_ignore


class PortableVenvSlimTests(unittest.TestCase):
    def test_win_lib_ignore(self) -> None:
        skipped = win_lib_ignore(
            "Lib",
            ["os.py", "idlelib", "test", "encodings", "ensurepip", "turtledemo"],
        )
        self.assertEqual(
            set(skipped), {"idlelib", "test", "ensurepip", "turtledemo"}
        )

    def test_slim_removes_junk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "venv"
            keep = root / "Lib" / "encodings"
            keep.mkdir(parents=True)
            (keep / "utf_8.py").write_text("# keep\n", encoding="utf-8")
            junk = root / "Lib" / "idlelib"
            junk.mkdir(parents=True)
            (junk / "foo.py").write_text("# junk\n", encoding="utf-8")
            tests = root / "Lib" / "site-packages" / "pkg" / "tests"
            tests.mkdir(parents=True)
            (tests / "t.py").write_text("# junk\n", encoding="utf-8")
            pyc = keep / "__pycache__"
            pyc.mkdir()
            (pyc / "utf_8.cpython-311.pyc").write_bytes(b"\0")

            before = count_files(root)
            stats = slim_portable_venv(root)
            self.assertGreater(stats["venv_files_removed"], 0)
            self.assertFalse(junk.exists())
            self.assertFalse(tests.exists())
            self.assertTrue((keep / "utf_8.py").is_file())
            self.assertEqual(stats["venv_files_after"], count_files(root))
            self.assertLess(stats["venv_files_after"], before)


if __name__ == "__main__":
    unittest.main()
