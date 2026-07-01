"""bake-syn-bridge: embedding run → git-tracked TSV snapshot."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation
from ingest.bridge_snapshot import (
    DEFAULT_SNAPSHOT,
    ingest_bridge_snapshot,
    write_bridge_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]


class BakeSynBridgeTests(unittest.TestCase):
    def test_write_bridge_snapshot_exports_ant_syn_bridge_rows(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        session.add_all(
            [
                Word(id=1, char="快", code="2", jyutping="faai3", length=1),
                Word(id=2, char="慢", code="2", jyutping="maan6", length=1),
            ]
        )
        session.add(
            WordRelation(
                word_id=1,
                related_id=2,
                relation_type="ant",
                score=0.88,
                source="ant_syn_bridge",
            )
        )
        session.commit()

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "bridge.tsv"
            n = write_bridge_snapshot(session, out)
            self.assertEqual(n, 1)
            text = out.read_text(encoding="utf-8")
            self.assertIn("快", text)
            self.assertIn("慢", text)

            session.query(WordRelation).delete()
            session.commit()
            inserted = ingest_bridge_snapshot(session, out)
            self.assertEqual(inserted["inserted"], 1)

    def test_bake_syn_bridge_cli_is_registered(self):
        import subprocess

        proc = subprocess.run(
            [sys_executable(), "-m", "ingest", "bake-syn-bridge", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("bake-syn-bridge", proc.stdout)
        self.assertIn("--export-only", proc.stdout)


def sys_executable() -> str:
    import sys

    return sys.executable


if __name__ == "__main__":
    unittest.main()
