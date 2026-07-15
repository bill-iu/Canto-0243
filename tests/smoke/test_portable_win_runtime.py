"""Windows portable runtime materialize + pyvenv home patch (#66)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from portable_win_runtime import (  # noqa: E402
    materialize_windows_python_home,
    patch_windows_pyvenv_home,
    windows_python_home,
)


def _write_cfg(venv: Path, home: Path) -> None:
    (venv / "pyvenv.cfg").write_text(
        f"home = {home}\ninclude-system-site-packages = false\nversion = 3.11.0\n",
        encoding="utf-8",
    )


@unittest.skipUnless(sys.platform == "win32", "Windows portable materialize")
class PortableWinRuntimeTests(unittest.TestCase):
    def test_materialize_copies_python_exe_and_rewrites_home(self) -> None:
        base = Path(sys.base_prefix)
        if not (base / "python.exe").is_file():
            self.skipTest(f"no python.exe under base_prefix={base}")

        with tempfile.TemporaryDirectory() as tmp:
            venv = Path(tmp) / "venv"
            venv.mkdir()
            (venv / "Scripts").mkdir()
            _write_cfg(venv, base)

            materialize_windows_python_home(venv)

            py_home = windows_python_home(venv)
            self.assertTrue((py_home / "python.exe").is_file())
            self.assertTrue((py_home / "Lib").is_dir() or (py_home / "DLLs").is_dir())
            cfg = (venv / "pyvenv.cfg").read_text(encoding="utf-8")
            self.assertIn(f"home = {py_home.resolve()}", cfg)
            self.assertNotIn(str(base), cfg.splitlines()[0])

    def test_patch_rewrites_stale_build_machine_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            venv = root / "venv"
            py_home = windows_python_home(venv)
            py_home.mkdir(parents=True)
            (py_home / "python.exe").write_bytes(b"fake")
            _write_cfg(venv, Path(r"C:\Users\User\AppData\Roaming\uv\python\cpython-fake"))

            self.assertTrue(patch_windows_pyvenv_home(root))
            line = (venv / "pyvenv.cfg").read_text(encoding="utf-8").splitlines()[0]
            self.assertEqual(line, f"home = {py_home.resolve()}")
            self.assertNotIn("AppData\\Roaming\\uv", line)

    def test_patch_noop_without_python_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            venv = root / "venv"
            venv.mkdir()
            _write_cfg(venv, Path(r"C:\missing"))
            self.assertFalse(patch_windows_pyvenv_home(root))


class PortableWinRuntimeSeamTests(unittest.TestCase):
    """Source seams available on all CI hosts."""

    def test_module_documents_redirector_requirement(self) -> None:
        text = (SCRIPTS / "portable_win_runtime.py").read_text(encoding="utf-8")
        self.assertIn("python-home", text)
        self.assertIn("redirector", text)
        self.assertIn("python.exe", text)


if __name__ == "__main__":
    unittest.main()
