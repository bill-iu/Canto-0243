"""Word familiarity must affect the full candidate pool before pagination."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.domain.lexicon.ranking import authoritative_reading_sort_key, heteronym_sort_key, search_result_sort_key
from app.lexicon.word_usage import WordUsage, load_word_usage, reset_word_usage_for_tests
from app.models.word import Word
from app.services.query_dispatch import QueryEngine, SearchContext
from app.utils.word_cache import reset_word_cache_for_tests
from app.utils.trad_chinese import to_traditional
from ingest.lexicon_layer_cache import fingerprint_source
from ingest.lexicon_sources import ingest_lexicon_json

HEADER = "char\tusage_rank\tsubtitle_channels\taction\n"


class WordUsageTests(unittest.TestCase):
    def tearDown(self):
        reset_word_usage_for_tests()
        reset_word_cache_for_tests()

    def test_curated_words_have_complete_traceable_familiarity_grades(self):
        root = Path(__file__).resolve().parents[2] / "data/lexicon"
        meta = json.loads((root / "word_usage.meta.json").read_text(encoding="utf-8"))
        for field, name in (("curated_sha256", "curated_lexicon.json"),
                            ("output_sha256", "word_usage.tsv"),
                            ("judgments_sha256", "word_usage_judgments.tsv")):
            self.assertEqual(meta[field], hashlib.sha256((root / name).read_bytes()).hexdigest())
        curated = {to_traditional(r["char"]) for r in json.loads((root / "curated_lexicon.json").read_text(encoding="utf-8"))}
        with (root / "word_usage.tsv").open(encoding="utf-8", newline="") as handle:
            rows = {r["char"]: r for r in csv.DictReader(handle, delimiter="\t")}
        self.assertEqual(meta["pending_curated_literals"], 0)
        self.assertTrue(curated.issubset(rows))
        self.assertFalse(any(r["basis"] == "pending" for r in rows.values()))
        with (root / "word_usage_judgments.tsv").open(encoding="utf-8", newline="") as handle:
            judgments = {r["char"]: r for r in csv.DictReader(handle, delimiter="\t")}
        for char in curated:
            row = rows[char]
            if row["basis"] == "ai-context":
                self.assertEqual(row["usage_rank"], judgments[char]["usage_rank"])
                self.assertEqual(row["note"], judgments[char]["note"])
            else:
                self.assertTrue(int(row["essay_frequency"]) > 0 or int(row["subtitle_count"] or 0) > 0)
            if row["action"] == "withdraw_curated":
                self.assertEqual(row["basis"], "ai-context")
                self.assertEqual(judgments[char]["usage_rank"], "3")

    def test_invalid_or_conflicting_grades_fail_clearly(self):
        for body in ("bad\n", HEADER+"詞\t4\t0\tkeep\n", HEADER+"詞\t1\t-1\tkeep\n",
                     HEADER+"詞\t3\t0\tkeep\n", HEADER+"詞\t1\t0\twithdraw_curated\n",
                     HEADER+"詞\t1\t0\tkeep\n詞\t2\t0\tkeep\n"):
            with self.subTest(body=body), TemporaryDirectory() as folder:
                path = Path(folder)/"word_usage.tsv"
                path.write_text(body, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_word_usage(path)
                reset_word_usage_for_tests()

    def test_explicit_withdrawal_applies_only_to_curated_source_and_invalidates_cache(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/"curated_lexicon.json"
            source.write_text('[{"char":"乳間股腳","jyutping":"jyu5 gaan1 gu2 goek3"},{"char":"迎風起","jyutping":"jing4 fung1 hei2"}]', encoding="utf-8")
            usage = root/"word_usage.tsv"
            usage.write_text(HEADER+"乳間股腳\t3\t0\twithdraw_curated\n迎風起\t1\t0\tkeep\n", encoding="utf-8")
            self.assertEqual([r.char for r in ingest_lexicon_json(source, source_id="curated")], ["迎風起"])
            self.assertEqual(len(ingest_lexicon_json(source, source_id="other")), 2)
            config = {"id":"curated", "parser":"lexicon_json", "raw_path":str(source), "word_usage_path":str(usage)}
            before = fingerprint_source(config, repo_root=root)
            usage.write_text(HEADER+"乳間股腳\t2\t0\tkeep\n", encoding="utf-8")
            self.assertNotEqual(before, fingerprint_source(config, repo_root=root))

    def test_word_usage_is_independent_of_reading_preference(self):
        usage = {"日常":WordUsage(0, 0, False), "冷語":WordUsage(2, 5, False)}
        rows = [SimpleNamespace(char="冷語", jyutping="laang5 jyu5"), SimpleNamespace(char="日常", jyutping="jat6 soeng4")]
        with patch("app.lexicon.word_usage.load_word_usage", return_value=usage), patch("app.domain.lexicon.ranking.get_essay_frequency", return_value=9999):
            self.assertEqual(sorted(rows, key=search_result_sort_key)[0].char, "日常")
            self.assertEqual(sorted(rows, key=heteronym_sort_key)[0].char, "日常")
            # For the same word, word frequency cannot override its pronunciation.
            same = [SimpleNamespace(char="日常", jyutping="bad1"), SimpleNamespace(char="日常", jyutping="jat6 soeng4")]
            with patch("app.domain.lexicon.ranking.pron_rank_sort_value_for_word", side_effect=lambda c,j: 0 if j=="jat6 soeng4" else 1):
                self.assertEqual(sorted(same, key=authoritative_reading_sort_key)[0].jyutping, "jat6 soeng4")

    def test_same_grade_keeps_essay_before_mandarin_subtitle_distribution(self):
        usage = {"但係": WordUsage(0, 0, False), "但是": WordUsage(0, 1255, False)}
        rows = [SimpleNamespace(char="但是", jyutping="daan6 si6"), SimpleNamespace(char="但係", jyutping="daan6 hai6")]
        with patch("app.lexicon.word_usage.load_word_usage", return_value=usage), patch("app.domain.lexicon.ranking.get_essay_frequency", side_effect=lambda c: 20000 if c == "但係" else 8720):
            self.assertEqual(sorted(rows, key=search_result_sort_key)[0].char, "但係")
            self.assertEqual(sorted(rows, key=heteronym_sort_key)[0].char, "但係")

    def test_first_200_are_ranked_from_full_pool_before_paging(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["words"]])
        cold = ["古語甲"+chr(0x4e00+i) for i in range(205)]
        common = "事發經過"
        usage = {c:WordUsage(2,0,False) for c in cold}
        usage[common] = WordUsage(0,0,False)
        try:
            with Session(engine) as db:
                for char in cold+[common]:
                    db.add(Word(char=char, jyutping="si6 faat3 ging1 gwo3", code="2434", length=4))
                db.commit()
                with patch("app.lexicon.word_usage.load_word_usage", return_value=usage), patch("app.domain.lexicon.ranking.get_essay_frequency", side_effect=lambda c: 5000 if c in cold else 0):
                    for mode in ("m1", "m2", "m3"):
                        reset_word_cache_for_tests()
                        first = QueryEngine().execute(SearchContext("2434",None,None,mode,200,0,db))
                        second = QueryEngine().execute(SearchContext("2434",None,None,mode,200,200,db))
                        self.assertEqual(first.items[0]["char"], common)
                        self.assertEqual(len(first.items),200)
                        self.assertEqual(len(second.items),6)
                        self.assertTrue({r["char"] for r in first.items}.isdisjoint({r["char"] for r in second.items}))
        finally:
            engine.dispose()
