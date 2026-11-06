"""Deferred lexical senses and exact old-reading repairs survive normal ingest."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import unittest

from app.lexicon.candidates import LexiconCandidate
from app.lexicon.corrections import load_corrections
from app.utils.jyutping_codec import get_0243_code
from app.utils.trad_chinese import to_traditional
from ingest.lexicon_overlay import apply_lexicon_overlay
from ingest.lexicon_sources import ingest_lexicon_json

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "data/lexicon"
BATCH = "2026-11-06-written-context01"


def tsv(path):
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


class WrittenContextFollowupTests(unittest.TestCase):
    def test_exact_start_reading_repairs_keep_words_and_other_valid_senses(self):
        review = tsv(BASE / "reviews" / f"{BATCH}-existing-rows.tsv")
        readings = [r for r in review if r["action"] != "rename_literal"]
        self.assertEqual(Counter(r["action"] for r in readings), {"delete": 7, "set_jyutping": 2})
        candidates = []
        expected = set()
        for row in readings:
            candidates.append(LexiconCandidate(row["char"], row["old_jyutping"], row["old_code"], ("kaifang",)))
            correct = row["new_char"], row["new_jyutping"], row["new_code"]
            if row["action"] == "delete":
                candidates.append(LexiconCandidate(*correct, ("rime_words",)))
            expected.add(correct)
        # The audit concerns nine exact imported readings, not every 始 syllable.
        for literal, reading in [("始", "si2"), ("未始", "mei6 ci3"), ("病", "beng6"), ("冰", "bing1")]:
            code = get_0243_code(reading)
            candidates.append(LexiconCandidate(literal, reading, code, ("fixture",)))
            expected.add((literal, reading, code))
        corrected = apply_lexicon_overlay(candidates, load_corrections(BASE / "lexicon_corrections.tsv"))
        self.assertEqual({(r.char, r.jyutping, r.code) for r in corrected}, expected)
        self.assertEqual(len(corrected), len(expected))
        self.assertEqual({r.char for r in corrected}, {r.char for r in candidates})
        for r in corrected:
            if r.char in {"初始", "由而家開始"}:
                self.assertEqual(r.sources, ("kaifang",))

    def test_normalization_distinguishes_rowing_from_already_traditional_strokes(self):
        cases = {
            "划不来": "划不來", "划不來": "划不來", "劃不來": "划不來",
            "划动": "划動", "划動": "划動", "劃動": "劃動",
            "划进": "划進", "划進": "划進", "劃進": "劃進",
            "划进来": "划進來", "划進來": "划進來", "劃進來": "劃進來",
            "划进去": "划進去", "划進去": "划進去", "劃進去": "劃進去",
            "划过来": "划過來", "划過來": "划過來", "劃過來": "劃過來",
            "划过去": "划過去", "划過去": "划過去", "劃過去": "劃過去",
            "計劃": "計劃", "規劃": "規劃", "劃線": "劃線", "劃分": "劃分",
        }
        for original, expected in cases.items():
            with self.subTest(original=original):
                self.assertEqual(to_traditional(original), expected)
                self.assertEqual(to_traditional(to_traditional(original)), expected)

    def test_deferred_promotions_have_source_codes_and_independent_frequency(self):
        meta = json.loads((BASE / "reviews" / f"{BATCH}.meta.json").read_text(encoding="utf-8"))
        review_path = BASE / "reviews" / f"{BATCH}-supplement.tsv"
        review = tsv(review_path)
        self.assertEqual(meta["newly_reviewed_candidates"], 0)
        self.assertEqual(meta["revisited_candidates"], 7)
        self.assertEqual(hashlib.sha256(review_path.read_bytes()).hexdigest(), meta["review_tsv_sha256"])
        curated = json.loads((BASE / "curated_lexicon.json").read_text(encoding="utf-8"))
        prefix = json.dumps(curated[:meta["input_curated_rows"]], ensure_ascii=False, indent=2) + "\n"
        self.assertEqual(hashlib.sha256(prefix.encode()).hexdigest(), meta["input_curated_sha256"])
        added = [r for r in curated if r.get("batch") == BATCH]
        self.assertEqual(len(added), 15)
        self.assertEqual(len({r["char"] for r in added}), 7)
        self.assertEqual({(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in review},
                         {(r["char"], r["jyutping"], r["code"], r["evidence"]) for r in added})
        actual = {(r.char, r.jyutping, r.code) for r in ingest_lexicon_json(BASE / "curated_lexicon.json", source_id="curated")}
        usage = {r["char"]: r for r in tsv(BASE / "word_usage.tsv")}
        for row in added:
            self.assertIn((row["char"], row["jyutping"], row["code"]), actual)
            self.assertEqual(row["code"], get_0243_code(row["jyutping"]))
            self.assertGreater(int(usage[row["char"]]["essay_frequency"]), 0)
        # Correct spelling recovers an existing observation, without fabricating it.
        self.assertEqual(usage["划不來"]["essay_frequency"], "694")
        self.assertEqual((usage["划不來"]["subtitle_count"], usage["划不來"]["subtitle_channels"]), ("14", "4"))
        self.assertNotIn("劃不來", usage)


if __name__ == "__main__":
    unittest.main()
