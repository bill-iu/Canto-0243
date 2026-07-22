"""C11 phase 2 / ADR-0067: venv.pack round-trip."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.portable_venv_pack import (
    PACK_NAME,
    ensure_portable_venv,
    marker_path,
    pack_portable_venv,
)


def _fake_win_venv(venv: Path) -> None:
    scripts = venv / "Scripts"
    home = venv / "python-home"
    scripts.mkdir(parents=True)
    home.mkdir(parents=True)
    (scripts / "python.exe").write_bytes(b"MZ-fake")
    (home / "python.exe").write_bytes(b"MZ-fake")
    lib = venv / "Lib" / "encodings"
    lib.mkdir(parents=True)
    (lib / "utf_8.py").write_text("# keep\n", encoding="utf-8")
    (venv / "pyvenv.cfg").write_text("home = X:\\build\n", encoding="utf-8")
    (venv / "portable-venv-slim.json").write_text(
        json.dumps({"venv_files_before": 10, "venv_files_after": 4}) + "\n",
        encoding="utf-8",
    )


class PortableVenvPackTests(unittest.TestCase):
    def test_pack_then_ensure_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            venv = root / "venv"
            _fake_win_venv(venv)
            meta = pack_portable_venv(root)
            self.assertTrue((root / PACK_NAME).is_file())
            self.assertFalse(venv.exists())
            self.assertTrue((root / "portable-venv-slim.json").is_file())
            self.assertEqual(meta["venv_unpacked_file_count"], 5)

            status = ensure_portable_venv(root)
            self.assertEqual(status, "extracted")
            self.assertTrue((venv / "Scripts" / "python.exe").is_file())
            self.assertTrue((venv / "python-home" / "python.exe").is_file())
            self.assertTrue(marker_path(root).is_file())
            self.assertFalse((root / PACK_NAME).is_file())  # deleted after ok

            # idempotent
            self.assertEqual(ensure_portable_venv(root), "ready")

    def test_pack_meta_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _fake_win_venv(root / "venv")
            pack_portable_venv(root)
            meta = json.loads((root / "portable-venv-pack.json").read_text(encoding="utf-8"))
            self.assertIn("venv_pack_sha256", meta)
            self.assertEqual(meta["pack_name"], PACK_NAME)


if __name__ == "__main__":
    unittest.main()
