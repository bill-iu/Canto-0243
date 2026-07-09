"""ADR-0038 C1: phoneme open-time contract + migrate."""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.domain.lexicon.phoneme_codec import encode_phoneme_list
from ingest.lexicon_meta import (
    ensure_phoneme_storage_contract,
    phoneme_storage_contract_ok,
    samples_legacy_json_phoneme,
    write_phoneme_vocab_meta,
)


def _tmp_db() -> Path:
    fd, name = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return Path(name)


def _seed_json_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE words (
              id INTEGER PRIMARY KEY,
              char TEXT,
              initials TEXT,
              finals TEXT,
              length INTEGER
            )
            """
        )
        conn.execute(
            "INSERT INTO words(char, initials, finals, length) VALUES (?,?,?,?)",
            ("香港", json.dumps(["h", "g"]), json.dumps(["oeng", "ong"]), 2),
        )
        conn.commit()
    finally:
        conn.close()


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except PermissionError:
        pass


class PhonemeContractTests(unittest.TestCase):
    def test_detect_legacy_json(self):
        path = _tmp_db()
        try:
            _seed_json_db(path)
            self.assertTrue(samples_legacy_json_phoneme(path))
            self.assertFalse(phoneme_storage_contract_ok(path))
        finally:
            _safe_unlink(path)

    def test_auto_migrate(self):
        path = _tmp_db()
        try:
            _seed_json_db(path)
            status = ensure_phoneme_storage_contract(path, allow_migrate=True)
            self.assertEqual(status, "migrated")
            self.assertTrue(phoneme_storage_contract_ok(path))
            conn = sqlite3.connect(path)
            try:
                fin = conn.execute("SELECT finals FROM words WHERE char='香港'").fetchone()[0]
            finally:
                conn.close()
            self.assertEqual(fin, encode_phoneme_list(["oeng", "ong"], "final"))
            self.assertFalse(str(fin).startswith("["))
        finally:
            _safe_unlink(path)

    def test_ok_when_meta_and_compact(self):
        path = _tmp_db()
        try:
            conn = sqlite3.connect(path)
            try:
                conn.execute(
                    "CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, initials TEXT, finals TEXT)"
                )
                conn.execute(
                    "INSERT INTO words(char, initials, finals) VALUES (?,?,?)",
                    (
                        "香港",
                        encode_phoneme_list(["h", "g"], "initial"),
                        encode_phoneme_list(["oeng", "ong"], "final"),
                    ),
                )
                conn.commit()
            finally:
                conn.close()
            write_phoneme_vocab_meta(path)
            self.assertEqual(ensure_phoneme_storage_contract(path, allow_migrate=False), "ok")
        finally:
            _safe_unlink(path)


if __name__ == "__main__":
    unittest.main()
