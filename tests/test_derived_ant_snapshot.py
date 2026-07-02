"""衍生反義快照（CONTEXT § 詞林衍生反義快照、§ 反義端點鏡射快照）。"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word, WordRelation
from ingest.derived_ant_snapshot import (
    CILIN_DERIVED_SOURCE,
    DEFAULT_CILIN_SNAPSHOT,
    DEFAULT_MIRROR_SNAPSHOT,
    MIRROR_SOURCE,
    bake_derived_ant_snapshots,
    ingest_cilin_derived_ant_snapshot,
    ingest_mirror_derived_ant_snapshot,
    write_derived_ant_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]


class DerivedAntSnapshotTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine)()

    def test_write_and_ingest_roundtrip(self):
        db = self._session()
        db.add_all([
            Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
            Word(id=2, char="悲傷", code="22", jyutping="bei1 soeng1", length=2),
        ])
        db.add(
            WordRelation(
                word_id=1,
                related_id=2,
                relation_type="ant",
                score=0.75,
                source=CILIN_DERIVED_SOURCE,
            )
        )
        db.commit()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cilin.tsv"
            n = write_derived_ant_snapshot(db, path, source=CILIN_DERIVED_SOURCE)
            self.assertEqual(n, 1)

            db.query(WordRelation).delete()
            db.commit()
            buf = io.StringIO()
            with redirect_stderr(buf):
                stats = ingest_cilin_derived_ant_snapshot(db, path)
            self.assertEqual(stats["inserted"], 1)
            self.assertFalse(stats["missing"])
            self.assertEqual(
                db.query(WordRelation).filter(WordRelation.source == CILIN_DERIVED_SOURCE).count(),
                1,
            )

    def test_ingest_clears_source_before_replace(self):
        db = self._session()
        db.add_all([
            Word(id=1, char="大", code="2", jyutping="daai6", length=1),
            Word(id=2, char="細", code="2", jyutping="sai3", length=1),
            Word(id=3, char="高", code="2", jyutping="gou1", length=1),
        ])
        db.add(
            WordRelation(
                word_id=1,
                related_id=3,
                relation_type="ant",
                score=0.5,
                source=MIRROR_SOURCE,
            )
        )
        db.commit()

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mirror.tsv"
            path.write_text(
                "head\ttail\trelation_type\tscore\n大\t細\tant\t0.72\n",
                encoding="utf-8",
            )
            stats = ingest_mirror_derived_ant_snapshot(db, path)
            self.assertEqual(stats["cleared"], 1)
            self.assertEqual(stats["inserted"], 1)
            rel = db.query(WordRelation).filter(WordRelation.source == MIRROR_SOURCE).one()
            self.assertEqual({rel.word_id, rel.related_id}, {1, 2})

    def test_ingest_missing_file_warns_and_skips(self):
        db = self._session()
        missing = Path("/nonexistent/ant_cilin_exanded_pairs.tsv")
        buf = io.StringIO()
        with redirect_stderr(buf):
            stats = ingest_cilin_derived_ant_snapshot(db, missing)
        self.assertTrue(stats["missing"])
        self.assertEqual(stats["inserted"], 0)
        self.assertIn("missing", buf.getvalue().lower())

    def test_bake_export_only_writes_both_snapshots(self):
        db = self._session()
        db.add_all([
            Word(id=1, char="開心", code="22", jyutping="hoi1 sam1", length=2),
            Word(id=2, char="傷心", code="22", jyutping="soeng1 sam1", length=2),
            Word(id=3, char="愉快", code="22", jyutping="jyu4 faai3", length=2),
        ])
        db.add(
            WordRelation(
                word_id=1,
                related_id=2,
                relation_type="ant",
                score=0.75,
                source=CILIN_DERIVED_SOURCE,
            )
        )
        db.add(
            WordRelation(
                word_id=1,
                related_id=3,
                relation_type="ant",
                score=0.72,
                source=MIRROR_SOURCE,
            )
        )
        db.commit()

        with tempfile.TemporaryDirectory() as tmp:
            cilin_out = Path(tmp) / "cilin.tsv"
            mirror_out = Path(tmp) / "mirror.tsv"
            stats = bake_derived_ant_snapshots(
                db,
                cilin_path=cilin_out,
                mirror_path=mirror_out,
                export_only=True,
            )
            self.assertEqual(stats["cilin"]["exported"], 1)
            self.assertEqual(stats["mirror"]["exported"], 1)
            self.assertIn("開心", cilin_out.read_text(encoding="utf-8"))
            self.assertIn("愉快", mirror_out.read_text(encoding="utf-8"))

    def test_bake_live_expand_then_export(self):
        db = self._session()
        db.add_all([
            Word(id=1, char="快樂", code="22", jyutping="faai3 lok6", length=2),
            Word(id=2, char="愉快", code="22", jyutping="jyu4 faai3", length=2),
            Word(id=3, char="開心", code="22", jyutping="hoi1 sam1", length=2),
            Word(id=4, char="悲傷", code="22", jyutping="bei1 soeng1", length=2),
        ])
        db.add(WordRelation(word_id=1, related_id=4, relation_type="ant", score=0.9, source="antisem"))
        db.add(WordRelation(word_id=2, related_id=3, relation_type="syn", score=0.85, source="cilin"))
        db.add(WordRelation(word_id=4, related_id=2, relation_type="syn", score=0.85, source="cilin"))
        db.commit()

        with tempfile.TemporaryDirectory() as tmp:
            cilin_out = Path(tmp) / "cilin.tsv"
            mirror_out = Path(tmp) / "mirror.tsv"
            stats = bake_derived_ant_snapshots(
                db,
                cilin_path=cilin_out,
                mirror_path=mirror_out,
                export_only=False,
            )
            self.assertGreater(stats["cilin"]["expand"]["inserted"], 0)
            self.assertGreater(stats["cilin"]["exported"], 0)
            self.assertGreaterEqual(stats["mirror"]["exported"], 0)
            self.assertTrue(cilin_out.is_file())
            self.assertTrue(mirror_out.is_file())

    def test_bake_cli_registered(self):
        import subprocess

        proc = subprocess.run(
            [sys.executable, "-m", "ingest", "bake-derived-ant-snapshots", "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("bake-derived-ant-snapshots", proc.stdout)
        self.assertIn("--export-only", proc.stdout)

    def test_default_paths(self):
        self.assertEqual(DEFAULT_CILIN_SNAPSHOT.name, "ant_cilin_exanded_pairs.tsv")
        self.assertEqual(DEFAULT_MIRROR_SNAPSHOT.name, "ant_syn_mirror_pairs.tsv")


if __name__ == "__main__":
    unittest.main()
