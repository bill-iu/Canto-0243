"""Reading cleanup removes reviewed errors without treating normal tone changes as errors."""
from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.lexicon.candidates import LexiconCandidate
from app.lexicon.corrections import load_corrections
from app.services.query_dispatch import QueryEngine, SearchContext
from app.utils.jyutping_codec import get_0243_code
from app.utils.word_cache import reset_word_cache_for_tests
from ingest.lexicon_build import persist_lexicon_candidates
from ingest.lexicon_overlay import apply_lexicon_overlay
from ingest.lexicon_sources import ingest_lexicon_json
from scripts.audit_lexicon_readings import audit_rows, main
from scripts.propose_lexicon_supplement import DEFAULT_CURATED


class LexiconReadingAuditTests(unittest.TestCase):
    def test_audit_flags_candidates_but_preserves_word_tone_changes_and_mixed_codes(self):
        rows = [
            ("善良", "sin5 loeng4", "50", 2),
            ("善良", "sin6 loeng4", "20", 32),
            ("圖書館", "tou4 syu1 gun2", "439", 0),
            ("爸爸", "baa4 baa1", "03", 32),
            ("AA制", "ei1 ei1 zai3", "??4", 32),
            ("𡁻牡丹", "ziu6 maau5 daan1", "253", 0),
        ]
        readings = {"善": {"sin6"}, "良": {"loeng4"}, "爸": {"baa1"}}
        findings, summary = audit_rows(rows, readings)
        self.assertEqual(summary["scanned_rows"], 6)
        self.assertEqual(summary["non_han_or_mixed_rows"], 1)
        self.assertEqual(summary["code_mismatch"], 1)
        self.assertEqual(summary["unlisted_word_syllable"], 2)
        self.assertEqual({row["char"] for row in findings}, {"善良", "圖書館", "爸爸"})
        self.assertTrue(all(row["verdict"] == "pending" for row in findings))
        self.assertIn(("爸爸", "baa4 baa1", "03", 32), rows)

    def test_audit_cli_preserves_database_and_existing_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, reference, output = root / "words.db", root / "char.csv", root / "audit"
            with closing(sqlite3.connect(db_path)) as db:
                with db:
                    db.execute("CREATE TABLE words (char TEXT, jyutping TEXT, code TEXT, source_flags INTEGER)")
                    db.execute("INSERT INTO words VALUES ('善良', 'sin5 loeng4', '50', 2)")
            reference.write_text("char,jyutping\n善,sin6\n良,loeng4\n", encoding="utf-8")
            before = hashlib.sha256(db_path.read_bytes()).hexdigest()
            args = ["--db", str(db_path), "--char-reference", str(reference), "--output-dir", str(output)]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["db_sha256"], before)
            original = (output / "findings.tsv").read_bytes()
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(args)
            self.assertEqual((output / "findings.tsv").read_bytes(), original)
            self.assertEqual(hashlib.sha256(db_path.read_bytes()).hexdigest(), before)

    def test_reviewed_deletions_remove_reported_false_tone_matches(self):
        reviewed = [row for row in load_corrections() if row.note.startswith("2026-10-19 全庫讀音審核")]
        targets = {(row.char, row.old_jyutping) for row in reviewed}
        self.assertIn(("善良", "sin5 loeng4"), targets)
        self.assertIn(("圖書館", "tou5 syu1 gun2"), targets)
        old_rows = [LexiconCandidate(row.char, row.old_jyutping, get_0243_code(row.old_jyutping), ("kaifang",)) for row in reviewed]
        correct = [
            LexiconCandidate("善良", "sin6 loeng4", "20", ("words_hk",)),
            LexiconCandidate("圖書館", "tou4 syu1 gun2", "039", ("words_hk",)),
            LexiconCandidate("爸爸", "baa4 baa1", "03", ("words_hk",)),
            LexiconCandidate("條件", "tiu4 gin2", "09", ("words_hk",)),
        ]
        candidates = apply_lexicon_overlay(old_rows + correct, load_corrections())
        self.assertEqual(candidates, correct)
        engine = create_engine("sqlite:///:memory:")
        reset_word_cache_for_tests()
        try:
            Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["words"]])
            with Session(engine) as db:
                persist_lexicon_candidates(db, candidates)
                db.commit()
                for mode in ("m1", "m2", "m3"):
                    for query, word, expected in (("40", "善良", False), ("439", "圖書館", False), ("20", "善良", True), ("039", "圖書館", True)):
                        with self.subTest(mode=mode, query=query):
                            result = QueryEngine().execute(SearchContext(query, None, None, mode, 1000, 0, db))
                            self.assertEqual(any(row["char"] == word for row in result.items), expected)
        finally:
            reset_word_cache_for_tests()
            engine.dispose()

    def test_curated_codes_and_contextual_readings_are_consistent(self):
        rows = json.loads(DEFAULT_CURATED.read_text(encoding="utf-8"))
        for row in rows:
            with self.subTest(row["char"]):
                self.assertEqual(row["code"], get_0243_code(row["jyutping"]))
        readings = {row.char: row.jyutping for row in ingest_lexicon_json(DEFAULT_CURATED, source_id="curated")}
        for word, reading in {
            "因為愛": "jan1 wai6 oi3", "數字化": "sou3 zi6 faa3",
            "社會保障": "se5 wui2 bou2 zoeng3", "違法行為": "wai4 faat3 hang4 wai4",
            "成班人": "seng4 baan1 jan4", "一生中": "jat1 sang1 zung1",
            "救人": "gau3 jan4", "稍等": "saau2 dang2",
        }.items():
            self.assertEqual(readings[word], reading)


if __name__ == "__main__":
    unittest.main()
