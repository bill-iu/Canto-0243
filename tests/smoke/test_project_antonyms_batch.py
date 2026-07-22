"""專案自建反義：種子／過濾／抽樣／loader／build merge smoke。"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.domain.relation_pool.ranking import DERIVED_ANT_SOURCES, SOURCE_BASE_RANK
from app.models.word import Word, WordRelation
from ingest.project_antonyms import (
    PROJECT_ANT_MERGE_RANK,
    PROJECT_ANT_RUNTIME_RANK,
    PROJECT_ANT_SOURCE,
    ProjectAntonymsError,
    collect_project_ant_tuples,
    export_seed_literals,
    filter_proposals,
    pair_undirected_key,
    parse_project_antonyms_tsv,
    passes_quality_gate,
    sample_pairs,
    sample_size_for,
    syn_pairs_from_db,
    syn_pairs_from_tuples,
)
from ingest.word_relations_build import (
    _SOURCE_RANK,
    build_word_relations,
    collect_static_relation_tuples,
    merge_relation_tuples,
)
from tests.smoke.helpers import memory_sessionmaker
from scripts.project_antonyms import _read_pair_lines


def _batch_meta(
    *,
    batch_id: str = "batch-1",
    head: str = "大",
    tail: str = "小",
    verdict: str = "ok",
    sample_ok: int | None = None,
    sample_n: int = 1,
    removed_sample_fails: list | None = None,
) -> dict:
    """Minimal auditable batch object for fixtures."""
    if sample_ok is None:
        sample_ok = 1 if verdict == "ok" else 0
    verdicts = [
        {"head": head, "tail": tail, "verdict": verdict, "reasons": []}
        for _ in range(sample_n)
    ]
    if sample_n > 1 and sample_ok < sample_n:
        for i in range(sample_ok, sample_n):
            verdicts[i]["verdict"] = "fail"
    removed = list(removed_sample_fails or [])
    parent_n = sample_n if sample_n > 1 else 1 + len(removed)
    return {
        "batches": {
            batch_id: {
                "k": 500,
                "sample_seed": 1,
                "sample_n": sample_n,
                "sample_ok": sample_ok,
                "ok_rate_threshold": 0.85 if batch_id == "batch-20260713" else 0.90,
                "sample_parent_n": parent_n,
                "sample_parent_commit": "a" * 40,
                "sample_parent_tsv_sha256": "b" * 64,  # filled by _with_fixture_git_blob
                "removed_sample_fails": removed,
                "model_note": "test fixture",
                "model": "xai/grok-test",
                "model_provider": "xAI",
                "model_version": "grok-test",
                "model_params": {
                    "temperature": None,
                    "top_p": None,
                    "max_output_tokens": None,
                    "seed_k": 500,
                },
                "git_commit": "c" * 40,
                "db_sha256": "d" * 64,
                "essay_sha256": "e" * 64,
                "prompt_path": "data/syn_ant/project-antonyms-prompt.txt",
                "prompt_sha256": "f" * 64,
                "sample_verdicts": verdicts,
            }
        }
    }


def _fixture_parent_blob(meta: dict, *, accepted: list[tuple[str, str]] | None = None) -> bytes:
    batch_id, batch = next(iter(meta["batches"].items()))
    removed = [
        (str(r["head"]).strip(), str(r["tail"]).strip())
        for r in batch["removed_sample_fails"]
    ]
    if accepted is None:
        v0 = batch["sample_verdicts"][0]
        accepted_n = int(batch["sample_parent_n"]) - len(removed)
        accepted = [(v0["head"], v0["tail"])] * accepted_n
    pairs = list(accepted) + removed
    body = "head\ttail\trelation_type\tbatch_id\n" + "".join(
        f"{h}\t{t}\tant\t{batch_id}\n" for h, t in pairs
    )
    return body.encode("utf-8")


def _with_fixture_git_blob(meta: dict, *, accepted: list[tuple[str, str]] | None = None):
    """Patch git blob reader; stamp sample_parent_tsv_sha256 to match fixture blob."""
    blob = _fixture_parent_blob(meta, accepted=accepted)
    batch = next(iter(meta["batches"].values()))
    batch["sample_parent_tsv_sha256"] = __import__("hashlib").sha256(blob).hexdigest()
    return mock.patch("ingest.project_antonyms._read_git_blob", return_value=blob)


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

    def test_meta_rejects_below_quality_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            tsv = Path(tmp) / "p.tsv"
            tsv.write_text(
                "head\ttail\trelation_type\tbatch_id\n大\t小\tant\tbatch-1\n",
                encoding="utf-8",
            )
            # 42/50 < 85%
            meta = _batch_meta(sample_n=50, sample_ok=42, verdict="ok")
            with self.assertRaises(ProjectAntonymsError) as ctx:
                parse_project_antonyms_tsv(tsv, meta=meta)
            self.assertIn("quality gate", str(ctx.exception))

    def test_meta_ok_rate_threshold_required_and_campaign_90(self):
        from ingest.project_antonyms import validate_batch_meta_entry

        path = Path("fixture")
        base = _batch_meta()["batches"]["batch-1"]
        missing = dict(base)
        del missing["ok_rate_threshold"]
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_batch_meta_entry("batch-1", missing, path=path)
        self.assertIn("ok_rate_threshold", str(ctx.exception))

        # 45/50 = 0.90 passes campaign gate
        ok90 = _batch_meta(sample_n=50, sample_ok=45, verdict="ok")["batches"]["batch-1"]
        ok90["ok_rate_threshold"] = 0.90
        validate_batch_meta_entry("batch-1", ok90, path=path)
        legacy85 = _batch_meta(batch_id="batch-20260713")["batches"]["batch-20260713"]
        validate_batch_meta_entry("batch-20260713", legacy85, path=path)
        new85 = _batch_meta(batch_id="campaign-b02-20260713")["batches"]["campaign-b02-20260713"]
        new85["ok_rate_threshold"] = 0.85
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_batch_meta_entry("campaign-b02-20260713", new85, path=path)
        self.assertIn("must be 0.90", str(ctx.exception))
        # 44/50 = 0.88 fails 0.90
        bad90 = _batch_meta(sample_n=50, sample_ok=44, verdict="ok")["batches"]["batch-1"]
        bad90["ok_rate_threshold"] = 0.90
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_batch_meta_entry("batch-1", bad90, path=path)
        self.assertIn("quality gate", str(ctx.exception))

    def test_meta_rejects_weak_audit_fields(self):
        from ingest.project_antonyms import validate_batch_meta_entry

        base = _batch_meta()["batches"]["batch-1"]
        path = Path("meta-test")

        bad_model = dict(base, model="Cursor Agent/blind-draft")
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_batch_meta_entry("batch-1", bad_model, path=path)
        self.assertIn("auditable", str(ctx.exception))

        weak_params = dict(base, model_params={"temperature": None, "seed_k": 1})
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_batch_meta_entry("batch-1", weak_params, path=path)
        self.assertIn("generation", str(ctx.exception))

        weak_hash = dict(base, git_commit="x", db_sha256="x")
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_batch_meta_entry("batch-1", weak_hash, path=path)
        self.assertIn("40-hex", str(ctx.exception))

    def test_sample_parent_blob_filters_by_batch_id(self):
        """Multi-batch TSV: parent replay compares only this batch_id slice."""
        from ingest.project_antonyms import (
            ProjectAntPair,
            assert_sample_replayable,
            sample_pairs,
        )

        batch_id = "campaign-b01-20260713"
        parent = [("甲", "乙"), ("丙", "丁")]
        seed = 3
        sampled = sample_pairs(parent, seed=seed)
        self.assertEqual(len(sampled), 2)
        meta = _batch_meta(batch_id=batch_id, head=sampled[0][0], tail=sampled[0][1])
        batch = meta["batches"][batch_id]
        batch["sample_seed"] = seed
        batch["sample_n"] = 2
        batch["sample_ok"] = 2
        batch["sample_parent_n"] = 2
        batch["sample_verdicts"] = [
            {"head": h, "tail": t, "verdict": "ok", "reasons": []} for h, t in sampled
        ]
        batch["removed_sample_fails"] = []
        blob = (
            "head\ttail\trelation_type\tbatch_id\n"
            "舊\t新\tant\tbatch-20260713\n"
            + "".join(f"{h}\t{t}\tant\t{batch_id}\n" for h, t in parent)
        ).encode("utf-8")
        batch["sample_parent_tsv_sha256"] = __import__("hashlib").sha256(blob).hexdigest()
        accepted = [ProjectAntPair(head=h, tail=t, batch_id=batch_id) for h, t in parent]
        with mock.patch("ingest.project_antonyms._read_git_blob", return_value=blob):
            assert_sample_replayable(batch_id, batch, accepted, path=Path("multi-batch"))

    def test_fail_verdict_must_be_removed_from_accepted(self):
        """P1: sampled fail pairs cannot remain in the authoritative TSV."""
        with tempfile.TemporaryDirectory() as tmp:
            tsv = Path(tmp) / "p.tsv"
            tsv.write_text(
                "head\ttail\trelation_type\tbatch_id\n"
                "好\t壞\tant\tbatch-1\n"
                "大\t小\tant\tbatch-1\n",
                encoding="utf-8",
            )
            meta = _batch_meta(head="好", tail="壞")
            batch = meta["batches"]["batch-1"]
            batch["sample_n"] = 2
            batch["sample_ok"] = 1
            batch["sample_parent_n"] = 2
            batch["sample_seed"] = 1
            batch["sample_verdicts"] = [
                {"head": "好", "tail": "壞", "verdict": "ok", "reasons": []},
                {"head": "大", "tail": "小", "verdict": "fail", "reasons": ["B"]},
            ]
            batch["removed_sample_fails"] = []
            with mock.patch(
                "ingest.project_antonyms.passes_quality_gate", return_value=True
            ), _with_fixture_git_blob(meta, accepted=[("好", "壞"), ("大", "小")]):
                with self.assertRaises(ProjectAntonymsError) as ctx:
                    parse_project_antonyms_tsv(tsv, meta=meta)
            self.assertIn("removed_sample_fails", str(ctx.exception))

            batch["removed_sample_fails"] = [{"head": "大", "tail": "小", "reasons": ["B"]}]
            with mock.patch(
                "ingest.project_antonyms.passes_quality_gate", return_value=True
            ), _with_fixture_git_blob(meta, accepted=[("好", "壞")]):
                with self.assertRaises(ProjectAntonymsError) as ctx:
                    parse_project_antonyms_tsv(tsv, meta=meta)
            self.assertIn("still in accepted", str(ctx.exception))

    def test_proposal_parser_rejects_stripped_empty_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prop.tsv"
            for text in ("大\t小\t", "\t大\t小", "head\ttail\textra\n大\t小\n"):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ProjectAntonymsError):
                    _read_pair_lines(path)
            path.write_text("head\ttail\n大\t小\n", encoding="utf-8")
            self.assertEqual(_read_pair_lines(path), [("大", "小")])

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
                meta = _batch_meta(head="小", tail="大")
                with _with_fixture_git_blob(meta, accepted=[("小", "大")]):
                    meta_path.write_text(
                        json.dumps({"batches": meta["batches"]}, ensure_ascii=False),
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
                meta = _batch_meta(head="大", tail="小")
                with _with_fixture_git_blob(meta, accepted=[("大", "小")]):
                    meta_path.write_text(
                        json.dumps({"batches": meta["batches"]}, ensure_ascii=False),
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

    def test_fresh_empty_db_blocks_same_round_static_syn(self):
        """P0: empty DB still rejects project ant colliding with new static syn."""
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="大", code="0", jyutping="", length=1),
                Word(id=2, char="小", code="2", jyutping="", length=1),
            ])
            db.commit()
            self.assertEqual(syn_pairs_from_db(db), set())
            new_syn = syn_pairs_from_tuples(
                [(1, 2, "syn", 0.85, "cilin", None)],
                {1: "大", 2: "小"},
            )
            self.assertEqual(new_syn, {pair_undirected_key("大", "小")})
            with tempfile.TemporaryDirectory() as tmp:
                tsv = Path(tmp) / "project_antonyms.tsv"
                meta_path = Path(tmp) / "project_antonyms.meta.json"
                meta = _batch_meta(head="大", tail="小")
                with _with_fixture_git_blob(meta, accepted=[("大", "小")]):
                    meta_path.write_text(
                        json.dumps({"batches": meta["batches"]}, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    tsv.write_text(
                        "head\ttail\trelation_type\tbatch_id\n大\t小\tant\tbatch-1\n",
                        encoding="utf-8",
                    )
                    with self.assertRaises(ProjectAntonymsError) as ctx:
                        collect_project_ant_tuples(
                            db,
                            tsv_path=tsv,
                            meta_path=meta_path,
                            syn_pairs=new_syn,
                        )
                    self.assertIn("syn conflict", str(ctx.exception))
                    rows = collect_project_ant_tuples(
                        db, tsv_path=tsv, meta_path=meta_path, syn_pairs=set()
                    )
                self.assertEqual(len(rows), 1)

    def test_collect_static_passes_same_round_syn_union(self):
        """P0 wiring: collect_static_relation_tuples feeds new static syn into project."""
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="大", code="0", jyutping="", length=1),
                Word(id=2, char="小", code="2", jyutping="", length=1),
            ])
            db.commit()
            captured: dict = {}

            def capture_project(db, *, syn_pairs=None, **_k):
                captured["syn"] = set(syn_pairs or ())
                return []

            with mock.patch(
                "ingest.word_relations_build.load_manifest",
                return_value={},
            ), mock.patch(
                "ingest.word_relations_build.select_sources",
                return_value=[{"parser": "current_static", "paths": {}, "source_rank": 70}],
            ), mock.patch(
                "ingest.word_relations_build.StaticThesaurusPort",
            ), mock.patch(
                "ingest.word_relations_build.collect_guotong_flat_edges",
                return_value=[],
            ), mock.patch(
                "ingest.word_relations_build.normalize_edges",
                return_value=[],
            ), mock.patch(
                "ingest.word_relations_build.merge_staging_edges",
                return_value=[],
            ), mock.patch(
                "ingest.word_relations_build.load_compound_antonyms",
                return_value=[],
            ), mock.patch(
                "ingest.word_relations_build.collect_flat_relation_tuples",
                return_value=[(1, 2, "syn", 0.85, "guotong", None)],
            ), mock.patch(
                "ingest.word_relations_build.collect_compound_ant_tuples",
                return_value=[],
            ), mock.patch(
                "ingest.word_relations_build.collect_project_syn_tuples",
                return_value=[],
            ), mock.patch(
                "ingest.word_relations_build.collect_project_ant_tuples",
                side_effect=capture_project,
            ), mock.patch(
                "ingest.word_relations_build.cap_undirected_syn_tuples",
                side_effect=lambda rows: list(rows),
            ):
                collect_static_relation_tuples(db, replace_static=True)
            self.assertIn(pair_undirected_key("大", "小"), captured["syn"])

    def test_append_mode_includes_preserved_static_db_syn(self):
        """P1: --append keeps static DB syn, so they must join conflict validation."""
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="大", code="0", jyutping="", length=1),
                Word(id=2, char="小", code="2", jyutping="", length=1),
            ])
            db.add(
                WordRelation(
                    word_id=1, related_id=2, relation_type="syn", source="cilin", score=0.9
                )
            )
            db.commit()
            captured: dict = {}

            def capture_project(db, *, syn_pairs=None, **_k):
                captured["syn"] = set(syn_pairs or ())
                return []

            patches = dict(
                load_manifest=mock.Mock(return_value={}),
                select_sources=mock.Mock(
                    return_value=[{"parser": "current_static", "paths": {}, "source_rank": 70}]
                ),
                StaticThesaurusPort=mock.Mock(),
                collect_guotong_flat_edges=mock.Mock(return_value=[]),
                normalize_edges=mock.Mock(return_value=[]),
                merge_staging_edges=mock.Mock(return_value=[]),
                load_compound_antonyms=mock.Mock(return_value=[]),
                collect_flat_relation_tuples=mock.Mock(return_value=[]),
                collect_compound_ant_tuples=mock.Mock(return_value=[]),
                collect_project_syn_tuples=mock.Mock(return_value=[]),
                collect_project_ant_tuples=capture_project,
                cap_undirected_syn_tuples=lambda rows: list(rows),
            )
            with mock.patch.multiple("ingest.word_relations_build", **patches):
                collect_static_relation_tuples(db, replace_static=False)
            self.assertIn(pair_undirected_key("大", "小"), captured["syn"])

            with mock.patch.multiple("ingest.word_relations_build", **patches):
                collect_static_relation_tuples(db, replace_static=True)
            # Replace mode excludes preserved cilin DB syn (cleared later).
            self.assertNotIn(pair_undirected_key("大", "小"), captured["syn"])


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
            passes_quality_gate,
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
        batch_id = "batch-20260713"
        batch = (meta.get("batches") or {})[batch_id]
        self.assertEqual(len(batch["sample_verdicts"]), int(batch["sample_n"]))
        self.assertEqual(
            sum(1 for v in batch["sample_verdicts"] if v["verdict"] == "ok"),
            int(batch["sample_ok"]),
        )
        self.assertIn("final N=100", str(batch.get("sample_parent") or ""))
        self.assertEqual(
            batch.get("sample_parent_commit"),
            "c9ad32846dc3946342da1e4ea8d8704aa723ba11",
        )
        self.assertEqual(int(batch["sample_parent_n"]), 100)
        self.assertTrue(passes_quality_gate(int(batch["sample_ok"]), int(batch["sample_n"])))
        batch_pairs = [p for p in pairs if p.batch_id == batch_id]
        final_keys = {
            (p.head, p.tail) if p.head <= p.tail else (p.tail, p.head) for p in batch_pairs
        }
        ok_in_final = sum(
            1
            for v in batch["sample_verdicts"]
            if v["verdict"] == "ok"
            and (
                (v["head"], v["tail"])
                if v["head"] <= v["tail"]
                else (v["tail"], v["head"])
            )
            in final_keys
        )
        # Batch-gate ok rows may later be removed by campaign final audit.
        self.assertLessEqual(ok_in_final, int(batch["sample_ok"]))
        self.assertGreater(ok_in_final, 0)
        # Self-contained replay: accepted ∪ removed_sample_fails → same 50 verdicts
        from ingest.project_antonyms import assert_sample_replayable

        assert_sample_replayable(batch_id, batch, batch_pairs, path=DEFAULT_META)

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
            if int(n or 0) != len(pairs):
                self.skipTest(
                    f"lyrics.db project_ant stale ({n} != {len(pairs)}); "
                    "rebuild word relations"
                )
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
