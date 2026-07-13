"""WP-07 campaign Top-5000 freeze + no-natural contract smoke."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.models.word import Word, WordRelation
from ingest.project_antonyms import ProjectAntonymsError
from ingest.project_antonyms_campaign import (
    CAMPAIGN_BASELINE_COMMIT,
    CAMPAIGN_BATCH_SIZE,
    CAMPAIGN_K,
    NO_NATURAL_REASONS,
    CampaignHead,
    assert_first_batch_matches_seeds,
    assert_no_terminal_conflict,
    build_campaign_meta,
    chars_with_direct_ant_excluding_project,
    ensure_no_natural_tsv,
    parse_campaign_manifest,
    parse_no_natural_tsv,
    rank_campaign_heads,
    render_manifest_tsv,
    write_campaign_manifest,
    write_empty_no_natural_tsv,
)
from tests.smoke.helpers import memory_sessionmaker


class CampaignFreezeTests(unittest.TestCase):
    def test_exclude_project_ant_keeps_seedable(self):
        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(id=1, char="甲", code="3", jyutping="", length=1),
                Word(id=2, char="近甲", code="33", jyutping="", length=2),
                Word(id=3, char="反甲", code="33", jyutping="", length=2),
            ])
            db.add_all([
                WordRelation(word_id=1, related_id=2, relation_type="syn", source="cilin"),
                WordRelation(
                    word_id=1, related_id=3, relation_type="ant", source="project_ant"
                ),
            ])
            db.commit()
            # With project_ant excluded, 甲 still has no *non-project* direct ant.
            directs = chars_with_direct_ant_excluding_project(db)
            self.assertNotIn("甲", directs)
            heads = rank_campaign_heads(
                db,
                k=10,
                essay_freq=lambda ch: 10 if ch == "甲" else 1,
                membership={"甲", "近甲", "反甲"},
                static_ant_heads=set(),
            )
            self.assertEqual(heads[0].head, "甲")

    def test_manifest_byte_stable_and_batch_slots(self):
        heads = [
            CampaignHead(
                rank=i,
                head=f"h{i:04d}",
                essay_frequency=10000 - i,
                batch_index=(i - 1) // CAMPAIGN_BATCH_SIZE + 1,
            )
            for i in range(1, CAMPAIGN_K + 1)
        ]
        text1 = render_manifest_tsv(heads)
        text2 = render_manifest_tsv(heads)
        self.assertEqual(text1, text2)
        self.assertEqual(heads[0].batch_index, 1)
        self.assertEqual(heads[499].batch_index, 1)
        self.assertEqual(heads[500].batch_index, 2)
        self.assertEqual(heads[-1].batch_index, 10)

    def test_first_batch_seed_parity_helper(self):
        heads = [
            CampaignHead(rank=i, head=f"s{i}", essay_frequency=1, batch_index=1)
            for i in range(1, 6)
        ]
        assert_first_batch_matches_seeds(heads, [f"s{i}" for i in range(1, 6)])
        with self.assertRaises(ProjectAntonymsError):
            assert_first_batch_matches_seeds(heads, ["nope"])

    def _synthetic_heads(self):
        _d = "零一二三四五六七八九"

        def _head(i: int) -> str:
            return "詞" + "".join(_d[int(c)] for c in f"{i:04d}")

        heads = [
            CampaignHead(
                rank=i,
                head=_head(i),
                essay_frequency=1000 - i,
                batch_index=(i - 1) // CAMPAIGN_BATCH_SIZE + 1,
            )
            for i in range(1, CAMPAIGN_K + 1)
        ]
        return heads, _head

    def test_write_parse_roundtrip_and_bad_sha(self):
        heads, _head = self._synthetic_heads()
        with tempfile.TemporaryDirectory() as tmp:
            tsv = Path(tmp) / "m.tsv"
            meta_path = Path(tmp) / "m.meta.json"
            db = Path(tmp) / "x.db"
            db.write_bytes(b"sqlite")
            essay = Path(tmp) / "essay.txt"
            essay.write_text("a", encoding="utf-8")
            ant = Path(tmp) / "ant.txt"
            ant.write_text("b", encoding="utf-8")
            with mock.patch(
                "ingest.project_antonyms_campaign._git_rev_parse",
                return_value="a" * 40,
            ):
                meta = build_campaign_meta(
                    heads=heads,
                    db_path=db,
                    essay_path=essay,
                    thesaurus_ant_path=ant,
                    baseline_commit=CAMPAIGN_BASELINE_COMMIT,
                )
            write_campaign_manifest(heads, meta, tsv_path=tsv, meta_path=meta_path)
            parsed = parse_campaign_manifest(tsv, meta_path=meta_path)
            self.assertEqual(len(parsed), CAMPAIGN_K)
            self.assertEqual(parsed[0].head, _head(1))
            meta_obj = json.loads(meta_path.read_text(encoding="utf-8"))
            meta_obj["manifest_sha256"] = "0" * 64
            meta_path.write_text(json.dumps(meta_obj), encoding="utf-8")
            with self.assertRaises(ProjectAntonymsError) as ctx:
                parse_campaign_manifest(tsv, meta_path=meta_path)
            self.assertIn("manifest_sha256", str(ctx.exception))

    def test_meta_fingerprints_fail_closed(self):
        heads, _ = self._synthetic_heads()
        with tempfile.TemporaryDirectory() as tmp:
            tsv = Path(tmp) / "m.tsv"
            meta_path = Path(tmp) / "m.meta.json"
            db = Path(tmp) / "x.db"
            db.write_bytes(b"sqlite")
            essay = Path(tmp) / "essay.txt"
            essay.write_text("a", encoding="utf-8")
            ant = Path(tmp) / "ant.txt"
            ant.write_text("b", encoding="utf-8")
            with mock.patch(
                "ingest.project_antonyms_campaign._git_rev_parse",
                return_value="a" * 40,
            ):
                meta = build_campaign_meta(
                    heads=heads,
                    db_path=db,
                    essay_path=essay,
                    thesaurus_ant_path=ant,
                    baseline_commit=CAMPAIGN_BASELINE_COMMIT,
                )
            write_campaign_manifest(heads, meta, tsv_path=tsv, meta_path=meta_path)

            cases = [
                ("baseline_commit", "c" * 40, "baseline_commit"),
                ("freeze_git_commit", "not-a-sha", "freeze_git_commit"),
                ("batch_size", 499, "batch_size"),
                ("batch_count", 9, "batch_count"),
                ("exclude_sources", ["project_ant"], "exclude_sources"),
                ("db_sha256", "deadbeef", "db_sha256"),
                ("essay_sha256", None, "essay_sha256"),
                ("thesaurus_ant_sha256", "0" * 63, "thesaurus_ant_sha256"),
                ("batch_counts", {"1": 500}, "batch_counts"),
            ]
            for field, value, needle in cases:
                write_campaign_manifest(heads, meta, tsv_path=tsv, meta_path=meta_path)
                meta_obj = json.loads(meta_path.read_text(encoding="utf-8"))
                meta_obj[field] = value
                meta_path.write_text(
                    json.dumps(meta_obj, ensure_ascii=False), encoding="utf-8"
                )
                with self.assertRaises(ProjectAntonymsError, msg=field) as ctx:
                    parse_campaign_manifest(tsv, meta_path=meta_path)
                self.assertIn(needle, str(ctx.exception), msg=field)

            write_campaign_manifest(heads, meta, tsv_path=tsv, meta_path=meta_path)
            meta_obj = json.loads(meta_path.read_text(encoding="utf-8"))
            meta_obj["batch_counts"]["3"] = 499
            meta_path.write_text(json.dumps(meta_obj), encoding="utf-8")
            with self.assertRaises(ProjectAntonymsError) as ctx:
                parse_campaign_manifest(tsv, meta_path=meta_path)
            self.assertIn("batch_counts", str(ctx.exception))


class NoNaturalContractTests(unittest.TestCase):
    def test_empty_and_bad_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nn.tsv"
            write_empty_no_natural_tsv(path)
            self.assertEqual(parse_no_natural_tsv(path), [])
            path.write_text(
                "head\treason\tbatch_id\n開心\tnot_a_reason\tb1\n",
                encoding="utf-8",
            )
            with self.assertRaises(ProjectAntonymsError) as ctx:
                parse_no_natural_tsv(path, campaign_heads={"開心"})
            self.assertIn("unknown reason", str(ctx.exception))
            reason = next(iter(NO_NATURAL_REASONS))
            path.write_text(
                f"head\treason\tbatch_id\n開心\t{reason}\tb1\n",
                encoding="utf-8",
            )
            rows = parse_no_natural_tsv(path, campaign_heads={"開心"})
            self.assertEqual(rows, [("開心", reason, "b1")])
            with self.assertRaises(ProjectAntonymsError):
                parse_no_natural_tsv(path, campaign_heads={"別的"})

    def test_ensure_no_natural_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nn.tsv"
            self.assertTrue(ensure_no_natural_tsv(path))
            reason = next(iter(NO_NATURAL_REASONS))
            kept = f"head\treason\tbatch_id\n開心\t{reason}\tb1\n"
            path.write_text(kept, encoding="utf-8")
            self.assertFalse(ensure_no_natural_tsv(path))
            self.assertEqual(path.read_text(encoding="utf-8"), kept)
            # freeze path: repeated ensure must preserve reviewed rows
            self.assertFalse(ensure_no_natural_tsv(path))
            self.assertEqual(path.read_text(encoding="utf-8"), kept)

    def test_terminal_conflict_fail_closed(self):
        assert_no_terminal_conflict(
            accepted_heads={"開心"}, no_natural_heads={"憂愁"}
        )
        with self.assertRaises(ProjectAntonymsError) as ctx:
            assert_no_terminal_conflict(
                accepted_heads={"開心", "快樂"},
                no_natural_heads={"開心"},
            )
        self.assertIn("conflict", str(ctx.exception))


class CampaignProgressTests(unittest.TestCase):
    def _heads(self, k: int = 20, batch_size: int = 10):
        _d = "零一二三四五六七八九"

        def _h(i: int) -> str:
            return "標" + "".join(_d[int(c)] for c in f"{i:04d}")

        return [
            CampaignHead(
                rank=i,
                head=_h(i),
                essay_frequency=100 - i,
                batch_index=(i - 1) // batch_size + 1,
            )
            for i in range(1, k + 1)
        ]

    def test_full_resolved_and_require_complete(self):
        from ingest.project_antonyms_campaign import (
            assert_campaign_complete,
            compute_campaign_progress,
        )

        heads = self._heads()
        accepted = {h.head for h in heads[:12]}
        no_nat = {h.head for h in heads[12:]}
        progress = compute_campaign_progress(
            heads,
            accepted_heads=accepted,
            no_natural_heads=no_nat,
            unresolved_sample_n=5,
        )
        self.assertTrue(progress["complete"])
        self.assertEqual(progress["resolved"], 20)
        self.assertEqual(progress["unresolved"], 0)
        self.assertEqual(progress["batches"][0]["accepted_covered"], 10)
        self.assertEqual(progress["batches"][1]["no_natural"], 8)
        assert_campaign_complete(progress)

    def test_miss_one_ok_until_require_complete(self):
        from ingest.project_antonyms_campaign import (
            assert_campaign_complete,
            compute_campaign_progress,
        )

        heads = self._heads()
        accepted = {h.head for h in heads[:10]}
        no_nat = {h.head for h in heads[10:-1]}
        progress = compute_campaign_progress(
            heads,
            accepted_heads=accepted,
            no_natural_heads=no_nat,
            unresolved_sample_n=5,
        )
        self.assertFalse(progress["complete"])
        self.assertEqual(progress["unresolved"], 1)
        self.assertEqual(progress["batches"][1]["unresolved_sample"], [heads[-1].head])
        with self.assertRaises(ProjectAntonymsError) as ctx:
            assert_campaign_complete(progress)
        self.assertIn("incomplete", str(ctx.exception))

    def test_conflict_and_out_of_manifest_fail(self):
        from ingest.project_antonyms_campaign import compute_campaign_progress

        heads = self._heads()
        with self.assertRaises(ProjectAntonymsError) as ctx:
            compute_campaign_progress(
                heads,
                accepted_heads={heads[0].head},
                no_natural_heads={heads[0].head},
            )
        self.assertIn("conflict", str(ctx.exception))
        with self.assertRaises(ProjectAntonymsError) as ctx:
            compute_campaign_progress(
                heads,
                accepted_heads=set(),
                no_natural_heads={"庫外字"},
            )
        self.assertIn("outside campaign", str(ctx.exception))

    def test_rejects_negative_unresolved_sample(self):
        from ingest.project_antonyms_campaign import compute_campaign_progress

        heads = self._heads(k=4, batch_size=2)
        with self.assertRaises(ProjectAntonymsError):
            compute_campaign_progress(
                heads,
                accepted_heads=set(),
                no_natural_heads=set(),
                unresolved_sample_n=-1,
            )

    def test_unresolved_heads_for_batch(self):
        from ingest.project_antonyms_campaign import unresolved_heads_for_batch

        heads = self._heads(k=20, batch_size=10)
        accepted = {heads[0].head, heads[10].head}
        no_nat = {heads[1].head}
        b1 = unresolved_heads_for_batch(
            heads,
            batch_index=1,
            accepted_heads=accepted,
            no_natural_heads=no_nat,
        )
        self.assertEqual(len(b1), 8)
        self.assertNotIn(heads[0].head, b1)
        self.assertNotIn(heads[1].head, b1)

    def test_no_natural_sample_replay_and_gate(self):
        from ingest.project_antonyms_campaign import (
            NO_NATURAL_REASONS,
            assert_no_natural_sample_replayable,
            sample_no_natural_rows,
            validate_no_natural_batch_meta,
            validate_no_natural_ledger,
        )

        reason = next(iter(NO_NATURAL_REASONS))
        # Build parent of 60 heads so sample_size_for = 50
        parent = [(f"詞{i:02d}", reason, "campaign-b01-20260713") for i in range(60)]
        # Use CJK-only heads
        _d = "零一二三四五六七八九"
        parent = [
            (
                "無" + "".join(_d[int(c)] for c in f"{i:02d}"),
                reason,
                "campaign-b01-20260713",
            )
            for i in range(60)
        ]
        seed = 7
        sampled = sample_no_natural_rows(parent, seed=seed)
        self.assertEqual(len(sampled), 50)
        # Mark last sampled as fail and remove from accepted rows
        fail_h, fail_r, _ = sampled[-1]
        kept = [r for r in parent if r[0] != fail_h]
        verdicts = [
            {"head": h, "reason": r, "verdict": "ok"} for h, r, _ in sampled[:-1]
        ] + [{"head": fail_h, "reason": fail_r, "verdict": "fail"}]
        entry = {
            "sample_seed": seed,
            "sample_n": 50,
            "sample_ok": 49,
            "ok_rate_threshold": 0.90,
            "sample_parent_n": 60,
            "removed_sample_fails": [{"head": fail_h, "reason": fail_r}],
            "sample_verdicts": verdicts,
            "git_commit": "a" * 40,
        }
        path = Path("nn-meta")
        validate_no_natural_batch_meta("campaign-b01-20260713", entry, path=path)
        weak = dict(entry)
        weak["ok_rate_threshold"] = 0.85
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_no_natural_batch_meta("campaign-b01-20260713", weak, path=path)
        self.assertIn("must be 0.90", str(ctx.exception))
        assert_no_natural_sample_replayable(
            "campaign-b01-20260713", entry, kept, path=path
        )
        # Still in TSV → fail
        with self.assertRaises(ProjectAntonymsError):
            assert_no_natural_sample_replayable(
                "campaign-b01-20260713", entry, parent, path=path
            )

        # Reason amendment: fail stays in TSV with corrected reason
        other = next(r for r in NO_NATURAL_REASONS if r != reason)
        amended_kept = [
            (h, other if h == fail_h else r, b) for h, r, b in parent
        ]
        amend_entry = dict(entry)
        amend_entry["removed_sample_fails"] = []
        amend_entry["reason_amendments"] = [
            {"head": fail_h, "from_reason": fail_r, "to_reason": other}
        ]
        assert_no_natural_sample_replayable(
            "campaign-b01-20260713", amend_entry, amended_kept, path=path
        )

        with tempfile.TemporaryDirectory() as tmp:
            tsv = Path(tmp) / "nn.tsv"
            meta_path = Path(tmp) / "nn.meta.json"
            lines = ["head\treason\tbatch_id"] + [
                f"{h}\t{r}\t{b}" for h, r, b in kept
            ]
            tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")
            meta_path.write_text(
                json.dumps(
                    {"batches": {"campaign-b01-20260713": entry}},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            campaign = {h for h, _, _ in kept} | {fail_h}
            rows = validate_no_natural_ledger(
                tsv_path=tsv, meta_path=meta_path, campaign_heads=campaign
            )
            self.assertEqual(len(rows), 59)
            bad_meta_path = Path(tmp) / "bad.meta.json"
            bad_meta_path.write_text(
                json.dumps({"batches": {"unused": {}}}), encoding="utf-8"
            )
            empty_tsv = Path(tmp) / "empty.tsv"
            empty_tsv.write_text("head\treason\tbatch_id\n", encoding="utf-8")
            with self.assertRaises(ProjectAntonymsError):
                validate_no_natural_ledger(
                    tsv_path=empty_tsv,
                    meta_path=bad_meta_path,
                    campaign_heads=set(),
                )

    def test_stratified_final_audit_sample_and_gate(self):
        from ingest.project_antonyms_campaign import (
            FINAL_AUDIT_OK_RATE_THRESHOLD,
            assert_campaign_complete,
            compute_campaign_progress,
            head_to_batch_index,
            stratified_sample_accepted,
            stratified_sample_no_natural,
            validate_final_audit_meta,
        )
        from ingest.project_antonyms import pair_undirected_key

        # Parametric tiny campaign: batch1=60 heads, batch2=10, batch3=60.
        heads: list[CampaignHead] = []
        rank = 0
        for i in range(60):
            rank += 1
            heads.append(
                CampaignHead(
                    rank=rank, head=f"甲{i:02d}", essay_frequency=200 - i, batch_index=1
                )
            )
        for i in range(10):
            rank += 1
            heads.append(
                CampaignHead(
                    rank=rank, head=f"乙{i:02d}", essay_frequency=100 - i, batch_index=2
                )
            )
        for i in range(60):
            rank += 1
            heads.append(
                CampaignHead(
                    rank=rank, head=f"丙{i:02d}", essay_frequency=50 - i, batch_index=3
                )
            )
        # Extra unresolved head in batch 3
        rank += 1
        heads.append(
            CampaignHead(rank=rank, head="未決頭", essay_frequency=1, batch_index=3)
        )
        head_batch = head_to_batch_index(heads)
        pairs = [(f"甲{i:02d}", f"尾甲{i:02d}") for i in range(60)]
        pairs += [(f"乙{i:02d}", f"尾乙{i:02d}") for i in range(10)]
        # batch 3 has no accepted pairs → skip
        seed = 11
        accepted = stratified_sample_accepted(pairs, head_batch, seed=seed, batch_count=3)
        self.assertEqual(accepted["status"], "ok")
        self.assertEqual(len(accepted["strata"]), 2)
        self.assertEqual(accepted["strata"][0]["batch_index"], 1)
        self.assertEqual(accepted["strata"][0]["parent_n"], 60)
        self.assertEqual(accepted["strata"][0]["sample_n"], 50)
        self.assertEqual(accepted["strata"][1]["batch_index"], 2)
        self.assertEqual(accepted["strata"][1]["parent_n"], 10)
        self.assertEqual(accepted["strata"][1]["sample_n"], 10)
        self.assertEqual(accepted["sample_n"], 60)

        # Empty no-natural → skipped_empty
        empty_nn = stratified_sample_no_natural([], head_batch, seed=seed, batch_count=3)
        self.assertEqual(empty_nn["status"], "skipped_empty")

        reason = next(iter(NO_NATURAL_REASONS))
        nn_rows = [(f"丙{i:02d}", reason, "b3") for i in range(60)]
        no_nat = stratified_sample_no_natural(
            nn_rows, head_batch, seed=seed, batch_count=3
        )
        self.assertEqual(no_nat["status"], "ok")
        self.assertEqual(len(no_nat["strata"]), 1)
        self.assertEqual(no_nat["strata"][0]["batch_index"], 3)
        self.assertEqual(no_nat["sample_n"], 50)

        fail_h, fail_t = accepted["sampled"][-1]
        fail_key = pair_undirected_key(fail_h, fail_t)
        kept_pairs = [p for p in pairs if pair_undirected_key(*p) != fail_key]
        verdicts_acc = [
            {"head": h, "tail": t, "verdict": "ok"} for h, t in accepted["sampled"][:-1]
        ] + [{"head": fail_h, "tail": fail_t, "verdict": "fail"}]
        accepted_entry = {
            "status": "ok",
            "sample_seed": seed,
            "sample_n": accepted["sample_n"],
            "sample_ok": accepted["sample_n"] - 1,
            "sample_parent_n": accepted["sample_parent_n"],
            "strata": accepted["strata"],
            "sample_verdicts": verdicts_acc,
            "removed_sample_fails": [{"head": fail_h, "tail": fail_t}],
        }
        nn_verdicts = [
            {"head": h, "reason": r, "verdict": "ok"} for h, r, _ in no_nat["sampled"]
        ]
        no_nat_entry = {
            "status": "ok",
            "sample_seed": seed,
            "sample_n": no_nat["sample_n"],
            "sample_ok": no_nat["sample_n"],
            "sample_parent_n": no_nat["sample_parent_n"],
            "strata": no_nat["strata"],
            "sample_verdicts": nn_verdicts,
            "removed_sample_fails": [],
        }
        meta = {
            "manifest_sha256": "b" * 64,
            "ok_rate_threshold": FINAL_AUDIT_OK_RATE_THRESHOLD,
            "git_commit": "c" * 40,
            "accepted": accepted_entry,
            "no_natural": no_nat_entry,
        }
        validate_final_audit_meta(
            meta,
            path=Path("final-audit"),
            manifest_sha256="b" * 64,
            accepted_pairs=kept_pairs,
            no_natural_rows=nn_rows,
            heads=heads,
        )

        # Replay mismatch
        bad = json.loads(json.dumps(meta))
        bad["accepted"]["sample_verdicts"][0]["head"] = "錯頭"
        with self.assertRaises(ProjectAntonymsError):
            validate_final_audit_meta(
                bad,
                path=Path("final-audit"),
                manifest_sha256="b" * 64,
                accepted_pairs=kept_pairs,
                no_natural_rows=nn_rows,
                heads=heads,
            )

        # 90% gate fail: only 50/60 ok
        low = json.loads(json.dumps(meta))
        low["accepted"]["sample_ok"] = 50
        for row in low["accepted"]["sample_verdicts"][50:]:
            row["verdict"] = "fail"
            low["accepted"]["removed_sample_fails"].append(
                {"head": row["head"], "tail": row["tail"]}
            )
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_final_audit_meta(
                low,
                path=Path("final-audit"),
                manifest_sha256="b" * 64,
                accepted_pairs=kept_pairs,
                no_natural_rows=nn_rows,
                heads=heads,
            )
        self.assertIn("quality gate failed", str(ctx.exception))

        # require-complete fails while unresolved
        progress = compute_campaign_progress(
            heads,
            accepted_heads={h for h, _ in pairs},
            no_natural_heads={h for h, _, _ in nn_rows},
            unresolved_sample_n=0,
        )
        self.assertFalse(progress["complete"])
        with self.assertRaises(ProjectAntonymsError):
            assert_campaign_complete(progress)

        # Both empty → skipped_empty ok
        empty_meta = {
            "manifest_sha256": "b" * 64,
            "ok_rate_threshold": FINAL_AUDIT_OK_RATE_THRESHOLD,
            "git_commit": "c" * 40,
            "accepted": {
                "status": "skipped_empty",
                "sample_seed": seed,
                "sample_n": 0,
                "sample_ok": 0,
                "sample_parent_n": 0,
                "strata": [],
                "sample_verdicts": [],
                "removed_sample_fails": [],
            },
            "no_natural": {
                "status": "skipped_empty",
                "sample_seed": seed,
                "sample_n": 0,
                "sample_ok": 0,
                "sample_parent_n": 0,
                "strata": [],
                "sample_verdicts": [],
                "removed_sample_fails": [],
            },
        }
        validate_final_audit_meta(
            empty_meta,
            path=Path("final-audit"),
            manifest_sha256="b" * 64,
            accepted_pairs=[],
            no_natural_rows=[],
            heads=heads,
        )

        bad_empty = json.loads(json.dumps(empty_meta))
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_final_audit_meta(
                bad_empty,
                path=Path("final-audit"),
                manifest_sha256="b" * 64,
                accepted_pairs=kept_pairs,
                no_natural_rows=[],
                heads=heads,
            )
        self.assertIn("skipped_empty", str(ctx.exception))

        bad_empty_nn = json.loads(json.dumps(empty_meta))
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_final_audit_meta(
                bad_empty_nn,
                path=Path("final-audit"),
                manifest_sha256="b" * 64,
                accepted_pairs=[],
                no_natural_rows=nn_rows,
                heads=heads,
            )
        self.assertIn("skipped_empty", str(ctx.exception))

        missing_threshold = json.loads(json.dumps(empty_meta))
        del missing_threshold["ok_rate_threshold"]
        with self.assertRaises(ProjectAntonymsError) as ctx:
            validate_final_audit_meta(
                missing_threshold,
                path=Path("final-audit"),
                manifest_sha256="b" * 64,
                accepted_pairs=[],
                no_natural_rows=[],
                heads=heads,
            )
        self.assertIn("ok_rate_threshold", str(ctx.exception))


class CampaignLiveFreezeTests(unittest.TestCase):
    def test_live_manifest_present_and_first500_matches_reference(self):
        from ingest.project_antonyms_campaign import (
            DEFAULT_MANIFEST_META,
            DEFAULT_MANIFEST_TSV,
            DEFAULT_NO_NATURAL_TSV,
            accepted_coverage_heads,
            compute_campaign_progress,
        )
        from ingest.project_antonyms import DEFAULT_TSV

        if not DEFAULT_MANIFEST_TSV.is_file():
            self.skipTest("campaign manifest missing")
        heads = parse_campaign_manifest(DEFAULT_MANIFEST_TSV, meta_path=DEFAULT_MANIFEST_META)
        self.assertEqual(len(heads), CAMPAIGN_K)
        ref = Path(
            r"C:/Users/User/AppData/Local/Temp/canto-0243-project-antonyms/batch-20260713/seeds.txt"
        )
        if ref.is_file():
            seeds = [
                ln.strip()
                for ln in ref.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
            assert_first_batch_matches_seeds(heads, seeds)
        no_nat = parse_no_natural_tsv(
            DEFAULT_NO_NATURAL_TSV, campaign_heads={h.head for h in heads}
        )
        progress = compute_campaign_progress(
            heads,
            accepted_heads=accepted_coverage_heads(DEFAULT_TSV),
            no_natural_heads={h for h, _, _ in no_nat},
            unresolved_sample_n=3,
        )
        self.assertEqual(progress["k"], CAMPAIGN_K)
        self.assertFalse(progress["complete"])
        self.assertGreater(progress["accepted_covered"], 0)
        self.assertEqual(progress["unresolved"] + progress["resolved"], CAMPAIGN_K)


if __name__ == "__main__":
    unittest.main()
