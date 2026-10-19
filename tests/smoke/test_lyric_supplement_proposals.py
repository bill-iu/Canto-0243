"""Song coverage, phrase boundaries, source evidence and reviewed reading corrections."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stderr, redirect_stdout
from pathlib import Path

from app.lexicon.candidates import LexiconCandidate
from app.lexicon.corrections import load_corrections
from app.utils.jyutping_codec import get_0243_code
from ingest.lexicon_overlay import apply_lexicon_overlay
from ingest.lexicon_sources import ingest_lexicon_json
from scripts.propose_lexicon_supplement import DEFAULT_CURATED
from scripts.propose_lyric_supplement import collect_ngrams, main, propose_lyric_gaps, read_phrases

ROOT = Path(__file__).resolve().parents[2]
BATCH = "2026-10-19-b03"


def review_rows(suffix):
    path = ROOT / f"data/lexicon/reviews/{BATCH}-{suffix}.tsv"
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")), delimiter="\t"))


class LyricSupplementTests(unittest.TestCase):
    def test_song_coverage_is_not_chorus_frequency_and_melisma_is_not_a_syllable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            header = "**kern\t**text\t**jyutping\n"
            phrase = "{4c\t春\tceon1\n8d\t.\t.\n4e}\t日\tjat6\n"
            (root / "A.krn").write_text(header + phrase * 3 + "4r\t.\t.\n{4c\t海\thoi2\n4d}\t邊\tbin1\n*-\t*-\t*-\n", encoding="utf-8")
            (root / "B.krn").write_text(header + phrase + "*-\t*-\t*-\n", encoding="utf-8")
            entries, summary = collect_ngrams(root)
            rows = propose_lyric_gaps(entries, set())
            self.assertEqual([row["char"] for row in rows], ["春日"])
            self.assertEqual((rows[0]["song_count"], rows[0]["occurrences"]), (2, 4))
            self.assertEqual(json.loads(rows[0]["corpus_readings"]), {"ceon1 jat6": 4})
            self.assertEqual(len(rows[0]["evidence"].split(";")), 2)
            self.assertEqual((rows[0]["verdict"], rows[0]["jyutping"]), ("pending", ""))
            self.assertNotIn("日海", entries)
            self.assertEqual(propose_lyric_gaps(entries, {"春日"}), [])
            self.assertEqual(summary["song_count"], 2)

    def test_missing_or_changing_spines_fail_instead_of_misaligning_readings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.krn"
            for text in ("4c\t春\tceon1\n", "**kern\t**text\t**jyutping\n*^\t*\t*\n"):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    list(read_phrases(path))

    def test_cli_preserves_database_and_existing_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db_path, curated, output = root / "words.db", root / "curated.json", root / "review"
            with closing(sqlite3.connect(db_path)) as db:
                with db:
                    db.execute("CREATE TABLE words (char TEXT)")
            curated.write_text("[]", encoding="utf-8")
            (root / "A.krn").write_text("**kern\t**text\t**jyutping\n{4c\t春\tceon1\n4d}\t日\tjat6\n", encoding="utf-8")
            before = hashlib.sha256(db_path.read_bytes()).hexdigest()
            args = ["--corpus-dir", str(root), "--db", str(db_path), "--curated", str(curated), "--min-songs", "1", "--output-dir", str(output)]
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(args), 0)
            original = (output / "gaps.tsv").read_bytes()
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(args)
            self.assertEqual((output / "gaps.tsv").read_bytes(), original)
            self.assertEqual(hashlib.sha256(db_path.read_bytes()).hexdigest(), before)

    def test_reviewed_corpus_entries_have_pinned_traceable_evidence(self):
        meta = json.loads((ROOT / f"data/lexicon/reviews/{BATCH}.meta.json").read_text(encoding="utf-8"))
        reviewed = review_rows("supplement")
        admitted = {(r.char, r.jyutping) for r in ingest_lexicon_json(DEFAULT_CURATED, source_id="curated")}
        self.assertEqual(sum(row["verdict"] == "accept" for row in reviewed), 199)
        corpus_rows = [row for row in reviewed if row["verdict"] == "accept" and row["evidence"].startswith("cantopop:")]
        self.assertEqual(len(corpus_rows), 168)
        for row in reviewed:
            if row["verdict"] in {"accept", "repair"}:
                self.assertIn((row["char"], row["jyutping"]), admitted)
            if row["evidence"].startswith("cantopop:"):
                prefix, revision, location = row["evidence"].split(":", 2)
                self.assertEqual(revision, meta["upstream_commit"])
                self.assertIn(Path(location.split("#")[0]).name, meta["input_sha256"])
            if row in corpus_rows:
                self.assertGreaterEqual(int(row["song_count"]), 2)

    def test_overlay_removes_only_confirmed_readings_and_keeps_supported_variants(self):
        reviewed = review_rows("readings")
        rejected = [row for row in reviewed if row["verdict"] == "delete"]
        self.assertEqual(len(rejected), 11)
        replacements = [LexiconCandidate(row["char"], row["replacement"], get_0243_code(row["replacement"]), ("curated",)) for row in rejected]
        old = [LexiconCandidate(row["char"], row["jyutping"], get_0243_code(row["jyutping"]), ("kaifang",)) for row in rejected]
        supported = [("自己", "zi6 gei1"), ("今日", "gam1 mat6"), ("把握", "baang2 ak1"), ("爸爸", "baa4 baa1")]
        variants = [LexiconCandidate(word, reading, get_0243_code(reading), ("words_hk",)) for word, reading in supported]
        result = apply_lexicon_overlay(old + replacements + variants, load_corrections())
        self.assertTrue(all((row.char, row.jyutping) not in {(r["char"], r["jyutping"]) for r in rejected} for row in result))
        self.assertTrue(set(supported).issubset({(row.char, row.jyutping) for row in result}))
        self.assertTrue({(row["char"], row["replacement"]) for row in rejected}.issubset({(row.char, row.jyutping) for row in result}))


if __name__ == "__main__":
    unittest.main()
