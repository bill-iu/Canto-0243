"""Payload root SSOT (P4#2 / ADR-0068)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.payload_root import (
    bind_payload_root,
    clear_payload_root_cache,
    get_payload_root,
    resolve_payload_root,
)


class PayloadRootTests(unittest.TestCase):
    def setUp(self) -> None:
        self._old = os.environ.get("CANTO_PAYLOAD_ROOT")
        os.environ.pop("CANTO_PAYLOAD_ROOT", None)
        clear_payload_root_cache()

    def tearDown(self) -> None:
        clear_payload_root_cache()
        if self._old is None:
            os.environ.pop("CANTO_PAYLOAD_ROOT", None)
        else:
            os.environ["CANTO_PAYLOAD_ROOT"] = self._old

    def test_env_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            os.environ["CANTO_PAYLOAD_ROOT"] = str(root)
            clear_payload_root_cache()
            self.assertEqual(resolve_payload_root(), root)
            self.assertEqual(get_payload_root(), root)

    def test_cwd_with_lyrics_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            (root / "lyrics.db").write_bytes(b"")
            with mock.patch("app.payload_root.Path.cwd", return_value=root):
                clear_payload_root_cache()
                # no env
                os.environ.pop("CANTO_PAYLOAD_ROOT", None)
                self.assertEqual(resolve_payload_root(), root)

    def test_bind_sets_env_and_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            bound = bind_payload_root(root)
            self.assertEqual(bound, root)
            self.assertEqual(os.environ.get("CANTO_PAYLOAD_ROOT"), str(root))
            self.assertEqual(get_payload_root(), root)

    def test_desktop_entry_has_no_local_resolve(self) -> None:
        source = Path("app/desktop_entry.py").read_text(encoding="utf-8")
        self.assertNotIn("def resolve_payload_root", source)
        self.assertIn("bind_payload_root", source)
        self.assertIn("from app.payload_root import", source)
        # No forked PYAPP → sys.executable.parent path policy
        self.assertNotIn('os.environ.get("PYAPP")', source)
        self.assertNotIn("sys.executable).resolve().parent", source)

    def test_single_python_resolve_definition(self) -> None:
        """Only app/payload_root.py defines resolve_payload_root."""
        hits = []
        for path in Path("app").rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "def resolve_payload_root" in text:
                hits.append(str(path).replace("\\", "/"))
        self.assertEqual(hits, ["app/payload_root.py"])


if __name__ == "__main__":
    unittest.main()
