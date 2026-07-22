"""local_launch must not follow venv python symlinks (PyApp / uv)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.launch.local_launch import _python_exe


class TestPythonExeKeepsVenvSymlink(unittest.TestCase):
    def test_absolute_does_not_follow_symlink(self) -> None:
        if sys.platform == "win32":
            self.skipTest("venv symlink layout is unix-like")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist = root / "dist" / "bin"
            venv_bin = root / "venv" / "bin"
            dist.mkdir(parents=True)
            venv_bin.mkdir(parents=True)
            real = dist / "python3.11"
            real.write_text("#!/bin/sh\n", encoding="utf-8")
            real.chmod(0o755)
            link = venv_bin / "python"
            link.symlink_to(real)

            got = _python_exe(link)
            self.assertEqual(got, link.absolute())
            self.assertNotEqual(got, real.resolve())
            # Child spawn must still use the venv path (has pyvenv.cfg parent).
            self.assertEqual(got.parent.name, "bin")
            self.assertEqual(got.parent.parent.name, "venv")

    def test_relative_path_made_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)
            fake = cwd / "python"
            fake.write_text("x", encoding="utf-8")
            with mock.patch.object(Path, "cwd", return_value=cwd):
                # pass relative name as string
                got = _python_exe("python")
            self.assertTrue(got.is_absolute())
            self.assertEqual(got.name, "python")

    def test_default_is_sys_executable_absolute(self) -> None:
        got = _python_exe(None)
        self.assertTrue(got.is_absolute())
        self.assertEqual(got.name, Path(sys.executable).name)


if __name__ == "__main__":
    unittest.main()
