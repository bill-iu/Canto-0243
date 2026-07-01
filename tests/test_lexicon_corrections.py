"""詞庫勘誤 apply logic."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.lexicon.corrections import LexiconCorrection, load_corrections, save_corrections
from app.models.word import Word
from ingest.lexicon_corrections import apply_one, apply_pending, check_status


class LexiconCorrectionsTests(unittest.TestCase):
    def test_load_save_roundtrip(self):
        rows = [
            LexiconCorrection(
                char="行",
                old_jyutping="hong6",
                old_code="2",
                action="set_jyutping",
                value="hang6",
                note="note",
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.tsv"
            save_corrections(rows, path)
            loaded = load_corrections(path)
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].char, "行")
            self.assertEqual(loaded[0].old_jyutping, "hong6")

    def test_load_legacy_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.tsv"
            path.write_text(
                "char\tcode\tjyutping\taction\tvalue\tnote\tstatus\tapplied_at\n"
                "你\t9\tnei9\tset_jyutping\tnei5\tlegacy\tapplied\t2026-01-01\n",
                encoding="utf-8",
            )
            loaded = load_corrections(path)
            self.assertEqual(loaded[0].old_jyutping, "nei9")
            self.assertEqual(loaded[0].old_code, "9")

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
        corr = LexiconCorrection(
            char="行", old_jyutping="hong6", old_code="2", action="set_jyutping", value="hang6"
        )
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
        corr = LexiconCorrection(
            char="你", old_jyutping="nei5", old_code="9", action="set_code", value="4"
        )
        apply_one(session, corr)
        session.commit()
        row = session.query(Word).filter(Word.char == "你").one()
        self.assertEqual(row.code, "4")

    def test_check_lists_rows(self):
        rows = [
            LexiconCorrection(char="x", old_jyutping="a1", old_code="0", action="delete"),
        ]
        import io

        buf = io.StringIO()
        check_status(rows, out=buf)
        self.assertIn("1 row", buf.getvalue())

    def test_apply_pending_deletes_row(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        session = sessionmaker(bind=engine)()
        session.add(Word(char="行", code="9", jyutping="hong6", finals='["ong"]', length=1))
        session.commit()
        rows = [
            LexiconCorrection(char="行", old_jyutping="hong6", old_code="9", action="delete"),
        ]
        _, logs = apply_pending(session, rows, dry_run=False)
        session.commit()
        self.assertEqual(session.query(Word).count(), 0)
        self.assertTrue(logs)


if __name__ == "__main__":
    unittest.main()
