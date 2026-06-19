"""詞庫勘誤 apply logic."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from ingest.lexicon_corrections import (
    DEFAULT_BATCH_N,
    LexiconCorrection,
    apply_one,
    apply_pending,
    check_status,
    load_corrections,
    save_corrections,
)


class LexiconCorrectionsTests(unittest.TestCase):
    def test_load_save_roundtrip(self):
        rows = [
            LexiconCorrection("行", "2", "hong6", "set_jyutping", "hang6", "note", "pending", ""),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.tsv"
            save_corrections(rows, path)
            loaded = load_corrections(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].char, "行")
            self.assertTrue(loaded[0].is_pending)

    def test_apply_set_jyutping(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        session.add(
            Word(
                char="行",
                code="2",
                jyutping="hong6",
                finals='["ong"]',
                initials='["h"]',
                length=1,
            )
        )
        session.commit()
        corr = LexiconCorrection("行", "2", "hong6", "set_jyutping", "hang6", "", "pending", "")
        apply_one(session, corr)
        session.commit()
        row = session.query(Word).filter(Word.char == "行").one()
        self.assertEqual(row.jyutping, "hang6")
        self.assertEqual(row.code, "2")

    def test_apply_set_code(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        session.add(
            Word(
                char="你",
                code="9",
                jyutping="nei5",
                finals='["ei"]',
                initials='["n"]',
                length=1,
            )
        )
        session.commit()
        corr = LexiconCorrection("你", "9", "nei5", "set_code", "4", "", "pending", "")
        apply_one(session, corr)
        session.commit()
        row = session.query(Word).filter(Word.char == "你").one()
        self.assertEqual(row.code, "4")

    def test_check_warns_at_batch_n(self):
        rows = [
            LexiconCorrection("x", "0", "a1", "delete", "", "", "pending", "")
            for _ in range(DEFAULT_BATCH_N)
        ]
        import io

        buf = io.StringIO()
        check_status(rows, batch_n=DEFAULT_BATCH_N, out=buf)
        self.assertIn("consider", buf.getvalue())

    def test_apply_pending_marks_applied(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        session.add(
            Word(char="行", code="9", jyutping="hong6", finals='["ong"]', length=1)
        )
        session.commit()
        rows = [
            LexiconCorrection("行", "9", "hong6", "delete", "", "", "pending", ""),
        ]
        updated, logs = apply_pending(session, rows, dry_run=False)
        session.commit()
        self.assertEqual(session.query(Word).count(), 0)
        self.assertEqual(updated[0].status, "applied")
        self.assertTrue(updated[0].applied_at)
        self.assertTrue(logs)


if __name__ == "__main__":
    unittest.main()
