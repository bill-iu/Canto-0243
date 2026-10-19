"""Corpus gaps stay proposals; reviewed expressions work through normal ingest/search."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stderr
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.lexicon.candidates import LexiconCandidate
from app.services.query_dispatch import QueryEngine, SearchContext
from app.utils.han import is_han_char
from app.utils.jyutping_codec import get_0243_code
from app.utils.trad_chinese import to_traditional
from app.utils.word_cache import reset_word_cache_for_tests
from ingest.lexicon_build import persist_lexicon_candidates
from ingest.lexicon_sources import ingest_source
from ingest.lexicon_validate import is_valid_word_lexicon_reading
from ingest.syn_ant_manifest import load_manifest
from scripts.propose_lexicon_supplement import (
    DEFAULT_CURATED,
    DEFAULT_ESSAY,
    load_known_literals,
    main,
    propose_gaps,
)

ROOT = Path(__file__).resolve().parents[2]


class LexiconSupplementProposalTests(unittest.TestCase):
    def test_gaps_fold_variants_filter_noise_and_never_invent_readings(self):
        with tempfile.TemporaryDirectory() as directory:
            essay = Path(directory) / "essay.txt"
            essay.write_text(
                "随风飘\t20\n隨風飄\t15\n向前走\t20\n回頭看\t99\n"
                "𡁻牡丹\t12\n半句，\t100\n123\t100\nCall鐘\t100\n"
                "長過範圍的七字句\t100\n短詞\t100\n太罕見\t1\n壞頻率\tx\n",
                encoding="utf-8",
            )
            rows = propose_gaps(essay, {"回头看"}, limit=3)
        self.assertEqual([row["char"] for row in rows], ["向前走", "隨風飄", "𡁻牡丹"])
        self.assertEqual(rows[1]["source_literal"], "随风飘")
        self.assertEqual(rows[1]["essay_frequency"], 20)  # not 20 + 15
        self.assertTrue(all(row["verdict"] == "pending" and row["jyutping"] == "" for row in rows))

    def test_cli_is_read_only_and_does_not_overwrite_review_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, essay, curated, output = [root / name for name in ("words.db", "essay.txt", "curated.json", "review.tsv")]
            with closing(sqlite3.connect(db_path)) as db:
                with db:
                    db.execute("CREATE TABLE words (char TEXT)")
                    db.execute("INSERT INTO words VALUES ('向前走')")
            essay.write_text("向前走\t50\n隨風飄\t40\n夜未央\t30\n", encoding="utf-8")
            curated.write_text('[{"char": "隨風飄"}]', encoding="utf-8")
            before = hashlib.sha256(db_path.read_bytes()).digest()
            args = ["--db", str(db_path), "--essay", str(essay), "--curated", str(curated), "--output", str(output)]
            self.assertEqual(main(args), 0)
            with output.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream, delimiter="\t"))
            self.assertEqual([row["char"] for row in rows], ["夜未央"])
            original_output = output.read_bytes()
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(args)
            self.assertEqual(output.read_bytes(), original_output)
            self.assertEqual(hashlib.sha256(db_path.read_bytes()).digest(), before)
            curated.write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_known_literals(db_path, curated)
            absent = root / "absent.db"
            with self.assertRaises(sqlite3.OperationalError):
                load_known_literals(absent, curated)
            self.assertFalse(absent.exists())

    def test_invalid_ranges_fail_before_writing_output(self):
        for options in ({"min_length": 1}, {"max_length": 2}, {"min_frequency": 0}, {"limit": 0}):
            with self.subTest(options), self.assertRaises(ValueError):
                propose_gaps(Path("absent-essay.txt"), set(), **options)

    def test_reviewed_batch_has_evidence_and_valid_six_tone_readings(self):
        rows = json.loads(DEFAULT_CURATED.read_text(encoding="utf-8"))
        batch = [row for row in rows if row.get("evidence")]
        essay_literals = {line.split()[0] for line in DEFAULT_ESSAY.read_text(encoding="utf-8-sig").splitlines() if line.split()}
        corpus_reviews = {
            (row["char"], row["jyutping"], row["evidence"])
            for path in (ROOT / "data/lexicon/reviews").glob("*-supplement.tsv")
            for row in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")), delimiter="\t")
            if row["verdict"] in {"accept", "repair"}
        }
        self.assertEqual(len({(row["char"], row["jyutping"]) for row in rows}), len(rows))
        self.assertEqual({row["category"] for row in batch}, {"general", "lyric", "spoken"})
        for row in batch:
            with self.subTest(row["char"]):
                self.assertTrue(all(is_han_char(char) for char in row["char"]))
                self.assertTrue(is_valid_word_lexicon_reading(row["char"], row["jyutping"]))
                self.assertEqual(row["code"], get_0243_code(row["jyutping"]))
                self.assertEqual(len(row["char"]), len(row["code"]))
                if row["evidence"].startswith("essay:"):
                    source_literal = row["evidence"].removeprefix("essay:")
                    self.assertIn(source_literal, essay_literals)
                    self.assertEqual(to_traditional(source_literal), row["char"])
                elif row["evidence"].startswith("cantopop:"):
                    self.assertIn((row["char"], row["jyutping"], row["evidence"]), corpus_reviews)
                else:
                    self.assertEqual((row["char"], row["evidence"]), ("迎風起", "user:2026-10-19"))

    def test_normal_curated_source_makes_missing_phrase_searchable_in_correct_modes(self):
        sources = load_manifest(ROOT / "data/lexicon/sources.yaml")
        source = next(row for row in sources if row["id"] == "curated")
        self.assertTrue(source["enabled_by_default"])
        candidates = ingest_source(source)
        self.assertIn(("迎風起", "jing4 fung1 hei2", "039"), [(row.char, row.jyutping, row.code) for row in candidates])
        candidates.append(LexiconCandidate("起", "hei2", "9", ("rime",)))
        engine = create_engine("sqlite:///:memory:")
        reset_word_cache_for_tests()
        try:
            Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["words"]])
            with Session(engine) as db:
                persist_lexicon_candidates(db, candidates)
                db.commit()
                for mode in ("m1", "m2", "m3"):
                    for query in ("033起", "039起"):
                        with self.subTest(mode=mode, query=query):
                            result = QueryEngine().execute(SearchContext(query, None, None, mode, 1000, 0, db))
                            found = any(row["char"] == "迎風起" for row in result.items)
                            self.assertEqual(found, mode == "m1" or query == "039起")
        finally:
            reset_word_cache_for_tests()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
