"""專案自建反義：種子／過濾／抽樣／loader／build merge smoke。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.domain.relations.ranking import DERIVED_ANT_SOURCES, SOURCE_BASE_RANK
from app.models.word import Word, WordRelation
from ingest.project_antonyms import (
    PROJECT_ANT_MERGE_RANK,
    PROJECT_ANT_RUNTIME_RANK,
    PROJECT_ANT_SOURCE,
    ProjectAntonymsError,
    collect_project_ant_tuples,
    export_seed_literals,
    filter_proposals,
    parse_project_antonyms_tsv,
    passes_quality_gate,
    sample_pairs,
    sample_size_for,
)
from ingest.word_relations_build import _SOURCE_RANK, build_word_relations, merge_relation_tuples
from tests.smoke.helpers import memory_sessionmaker


def _batch_meta(
    *,
    batch_id: str = "batch-1",
    head: str = "大",
    tail: str = "小",
    verdict: str = "ok",
) -> dict:
    """Minimal auditable batch object for fixtures."""
    ok = 1 if verdict == "ok" else 0
    return {
        "batches": {
            batch_id: {
                "k": 500,
                "sample_seed": 1,
                "sample_n": 1,
                "sample_ok": ok,
                "model_note": "test fixture",
                "sample_verdicts": [
                    {"head": head, "tail": tail, "verdict": verdict, "reasons": []}
                ],
            }
        }
    }


class ProjectAntonymsBatchTests(unittest.TestCase):
    def test_seed_tie_break_and_k_short(self):
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="甲", code="3", jyutping="gaap3", length=1),
                Word(id=2, char="乙", code="3", jyutping="jyut3", length=1),
                Word(id=3, char="丙", code="3", jyutping="bing2", length=1),
                Word(id=4, char="近甲", code="33", jyutping="", length=2),
                Word(id=5, char="近乙", code="33", jyutping="", length=2),
                Word(id=6, char="近丙", code="33", jyutping="", length=2),
            ])
            db.add_all([
                WordRelation(word_id=1, related_id=4, relation_type="syn", source="cilin"),
                WordRelation(word_id=2, related_id=5, relation_type="syn", source="cilin"),
                WordRelation(word_id=3, related_id=6, relation_type="syn", source="cilin"),
            ])
            db.commit()
            freq = {"甲": 10, "乙": 10, "丙": 5, "近甲": 1, "近乙": 1, "近丙": 1}
            seeds = export_seed_literals(
                db,
                k=2,
                essay_freq=lambda ch: freq.get(ch, 0),
                membership={"甲", "乙", "丙", "近甲", "近乙", "近丙"},
            )
            self.assertEqual(seeds, ["乙", "甲"])

    def test_seed_includes_bridge_only_excludes_direct(self):
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="快樂", code="22", jyutping="", length=2),
                Word(id=2, char="開心", code="22", jyutping="", length=2),
                Word(id=3, char="悲傷", code="22", jyutping="", length=2),
                Word(id=4, char="痛苦", code="22", jyutping="", length=2),
                Word(id=5, char="愉快", code="22", jyutping="", length=2),
            ])
            db.add_all([
                WordRelation(word_id=1, related_id=2, relation_type="syn", source="cilin"),
                WordRelation(word_id=1, related_id=5, relation_type="syn", source="cilin"),
                WordRelation(
                    word_id=1, related_id=4, relation_type="ant", source="ant_syn_bridge"
                ),
                WordRelation(word_id=2, related_id=3, relation_type="ant", source="guotong"),
            ])
            db.commit()
            seeds = export_seed_literals(
                db,
                k=10,
                essay_freq=lambda ch: 1,
                membership={"快樂", "開心", "悲傷", "痛苦", "愉快"},
            )
            self.assertIn("快樂", seeds)
            self.assertNotIn("開心", seeds)
            self.assertTrue(all(s not in DERIVED_ANT_SOURCES for s in ("guotong", "manual")))

    def test_filter_rejects_and_caps(self):
        membership = {"大", "小", "多", "少", "外"}
        syn_pairs = {tuple(sorted(("大", "多")))}
        stats = filter_proposals(
            [
                ("大", "小"),
                ("大", "小"),
                ("小", "大"),
                ("大", "大"),
                ("大", "外"),
                ("大", "少"),
                ("大", "多"),
                ("外", "沒有"),
            ],
            membership=membership,
            syn_pairs=syn_pairs,
            max_proposals_per_head=2,
            max_accepted_per_head=5,
        )
        self.assertEqual(stats.accepted, [("大", "小"), ("大", "外")])
        reasons = {r["reason"] for r in stats.rejected}
        self.assertIn("duplicate_or_reverse", reasons)
        self.assertIn("self", reasons)
        self.assertIn("syn_conflict", reasons)
        self.assertIn("proposal_cap", reasons)
        self.assertIn("not_in_lexicon", reasons)

    def test_sample_size_formula_and_reproducible(self):
        self.assertEqual(sample_size_for(0), 0)
        self.assertEqual(sample_size_for(10), 10)
        self.assertEqual(sample_size_for(50), 50)
        self.assertEqual(sample_size_for(1000), 50)
        self.assertEqual(sample_size_for(2000), 100)
        pairs = [(f"h{i}", f"t{i}") for i in range(60)]
        a = sample_pairs(pairs, seed=42)
        b = sample_pairs(pairs, seed=42)
        c = sample_pairs(pairs, seed=7)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 50)
        self.assertNotEqual(a, c)

    def test_quality_gate_85(self):
        self.assertTrue(passes_quality_gate(43, 50))
        self.assertFalse(passes_quality_gate(42, 50))
        self.assertFalse(passes_quality_gate(0, 0))
        self.assertFalse(passes_quality_gate(51, 50))
        self.assertFalse(passes_quality_gate(-1, 50))


class ProjectAntonymsLoaderTests(unittest.TestCase):
    def test_fail_closed_empty_batch_and_unknown_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            tsv = Path(tmp) / "p.tsv"
            meta = Path(tmp) / "p.meta.json"
            meta.write_text(json.dumps({"batches": {"b1": {}}}), encoding="utf-8")
            tsv.write_text(
                "head\ttail\trelation_type\tbatch_id\n大\t小\tant\tb1\n",
                encoding="utf-8",
            )
            with self.assertRaises(ProjectAntonymsError):
                parse_project_antonyms_tsv(tsv, meta=json.loads(meta.read_text(encoding="utf-8")))
            tsv.write_text(
                "head\ttail\trelation_type\tbatch_id\n大\t小\tant\tmissing\n",
                encoding="utf-8",
            )
            with self.assertRaises(ProjectAntonymsError):
                parse_project_antonyms_tsv(
                    tsv, meta=_batch_meta(batch_id="batch-1")
                )

    def test_collect_canonical_single_row_both_ends(self):
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="大", code="0", jyutping="daai6", length=1),
                Word(id=2, char="小", code="2", jyutping="siu2", length=1),
            ])
            db.commit()
            with tempfile.TemporaryDirectory() as tmp:
                tsv = Path(tmp) / "project_antonyms.tsv"
                meta_path = Path(tmp) / "project_antonyms.meta.json"
                meta_path.write_text(
                    json.dumps(_batch_meta(head="小", tail="大"), ensure_ascii=False),
                    encoding="utf-8",
                )
                tsv.write_text(
                    "head\ttail\trelation_type\tbatch_id\n小\t大\tant\tbatch-1\n",
                    encoding="utf-8",
                )
                rows = collect_project_ant_tuples(db, tsv_path=tsv, meta_path=meta_path)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0][0], 1)
                self.assertEqual(rows[0][1], 2)
                self.assertEqual(rows[0][2], "ant")
                self.assertEqual(rows[0][4], PROJECT_ANT_SOURCE)
                self.assertEqual(rows[0][3], 0.85)


class ProjectAntonymsBuildRankTests(unittest.TestCase):
    def test_merge_project_beats_guotong_and_ranks_aligned(self):
        self.assertEqual(SOURCE_BASE_RANK.get("project_ant"), PROJECT_ANT_RUNTIME_RANK)
        self.assertEqual(_SOURCE_RANK.get("project_ant"), PROJECT_ANT_MERGE_RANK)
        self.assertLess(SOURCE_BASE_RANK["project_ant"], SOURCE_BASE_RANK["guotong"])
        self.assertLess(_SOURCE_RANK["project_ant"], _SOURCE_RANK["guotong"])
        merged = merge_relation_tuples([
            (1, 2, "ant", 0.85, "guotong", None),
            (1, 2, "ant", 0.85, "project_ant", None),
            (1, 2, "ant", 0.7, "ant_syn_bridge", None),
        ])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0][4], "project_ant")

    def test_project_not_in_derived_sources(self):
        self.assertNotIn(PROJECT_ANT_SOURCE, DERIVED_ANT_SOURCES)

    def test_collect_before_clear_on_failure(self):
        """P0: failed collect must not clear committed sources."""
        Session = memory_sessionmaker()
        with Session() as db:
            calls: list[str] = []

            def boom(*_a, **_k):
                calls.append("collect")
                raise ProjectAntonymsError("syn conflict")

            def clear(_db, source: str) -> int:
                calls.append(f"clear:{source}")
                return 0

            with mock.patch(
                "ingest.word_relations_build.collect_static_relation_tuples",
                side_effect=boom,
            ), mock.patch(
                "ingest.word_relations_build.clear_word_relations_source",
                side_effect=clear,
            ):
                with self.assertRaises(ProjectAntonymsError):
                    build_word_relations(db)
            self.assertEqual(calls, ["collect"])

    def test_syn_conflict_preserves_existing_rows(self):
        """P0: project ant conflicting with syn fails before clear/write."""
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="大", code="0", jyutping="", length=1),
                Word(id=2, char="小", code="2", jyutping="", length=1),
                Word(id=3, char="中", code="1", jyutping="", length=1),
            ])
            db.add_all([
                WordRelation(
                    word_id=1, related_id=2, relation_type="syn", source="cilin", score=0.9
                ),
                WordRelation(
                    word_id=1, related_id=3, relation_type="ant", source="guotong", score=0.85
                ),
            ])
            db.commit()
            before = {
                (r.word_id, r.related_id, r.relation_type, r.source)
                for r in db.query(WordRelation).all()
            }
            with tempfile.TemporaryDirectory() as tmp:
                tsv = Path(tmp) / "project_antonyms.tsv"
                meta_path = Path(tmp) / "project_antonyms.meta.json"
                meta_path.write_text(
                    json.dumps(_batch_meta(head="大", tail="小"), ensure_ascii=False),
                    encoding="utf-8",
                )
                tsv.write_text(
                    "head\ttail\trelation_type\tbatch_id\n大\t小\tant\tbatch-1\n",
                    encoding="utf-8",
                )
                with mock.patch(
                    "ingest.word_relations_build.collect_static_relation_tuples",
                    side_effect=lambda db, **_k: collect_project_ant_tuples(
                        db, tsv_path=tsv, meta_path=meta_path
                    ),
                ):
                    with self.assertRaises(ProjectAntonymsError):
                        build_word_relations(db)
            after = {
                (r.word_id, r.related_id, r.relation_type, r.source)
                for r in db.query(WordRelation).all()
            }
            self.assertEqual(before, after)

    def test_dual_build_write_path_idempotent(self):
        """WP-06: two build_word_relations passes leave the same relation fingerprint."""
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="大", code="0", jyutping="", length=1),
                Word(id=2, char="小", code="2", jyutping="", length=1),
            ])
            db.add(
                WordRelation(
                    word_id=1, related_id=2, relation_type="ant", source="guotong", score=0.85
                )
            )
            db.commit()
            stable = [(1, 2, "ant", 0.85, "project_ant", None)]

            def collect(_db, **_k):
                return list(stable)

            with mock.patch(
                "ingest.word_relations_build.collect_static_relation_tuples",
                side_effect=collect,
            ):
                build_word_relations(db)
                snap1 = sorted(
                    (r.word_id, r.related_id, r.relation_type, r.source, r.score)
                    for r in db.query(WordRelation).all()
                )
                build_word_relations(db)
                snap2 = sorted(
                    (r.word_id, r.related_id, r.relation_type, r.source, r.score)
                    for r in db.query(WordRelation).all()
                )
            self.assertEqual(snap1, snap2)
            self.assertEqual(len(snap1), 1)
            self.assertEqual(snap1[0][3], "project_ant")


class ProjectAntonymsLiveReportTests(unittest.TestCase):
    """Requires repo-root lyrics.db after build-word-relations (WP-06)."""

    def test_live_tsv_db_parity_and_seed_exit(self):
        from pathlib import Path

        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        from app.domain.relations.word_relation_queries import load_db_char_set
        from app.lexicon.essay_index import get_essay_frequency
        from ingest.project_antonyms import (
            DEFAULT_META,
            DEFAULT_TSV,
            collect_project_ant_tuples,
            export_seed_literals,
            load_meta,
            parse_project_antonyms_tsv,
            static_ant_heads_from_port,
        )

        db_path = Path(__file__).resolve().parents[2] / "lyrics.db"
        if not db_path.is_file():
            self.skipTest("lyrics.db missing")
        if not DEFAULT_TSV.is_file() or not DEFAULT_META.is_file():
            self.skipTest("project antonyms list missing")

        meta = load_meta(DEFAULT_META)
        pairs = parse_project_antonyms_tsv(DEFAULT_TSV, meta=meta)
        if not pairs:
            self.skipTest("empty project antonyms list")
        batch = next(iter((meta.get("batches") or {}).values()))
        self.assertEqual(len(batch["sample_verdicts"]), int(batch["sample_n"]))
        self.assertEqual(
            sum(1 for v in batch["sample_verdicts"] if v["verdict"] == "ok"),
            int(batch["sample_ok"]),
        )

        engine = create_engine(f"sqlite:///{db_path.as_posix()}")
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        with Session() as db:
            n = db.execute(
                text(
                    "SELECT COUNT(*) FROM word_relations "
                    "WHERE source=:s AND relation_type='ant'"
                ),
                {"s": PROJECT_ANT_SOURCE},
            ).scalar()
            self.assertEqual(int(n or 0), len(pairs))
            t1 = collect_project_ant_tuples(db)
            t2 = collect_project_ant_tuples(db)
            self.assertEqual(t1, t2)
            membership = load_db_char_set(db)
            static_heads = static_ant_heads_from_port()
            seeds = set(
                export_seed_literals(
                    db,
                    k=500,
                    essay_freq=get_essay_frequency,
                    membership=membership,
                    static_ant_heads=static_heads,
                )
            )
            for p in pairs:
                self.assertNotIn(p.head, seeds)


if __name__ == "__main__":
    unittest.main()
