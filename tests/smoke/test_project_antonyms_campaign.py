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


class CampaignLiveFreezeTests(unittest.TestCase):
    def test_live_manifest_present_and_first500_matches_reference(self):
        from ingest.project_antonyms_campaign import (
            DEFAULT_MANIFEST_META,
            DEFAULT_MANIFEST_TSV,
            DEFAULT_NO_NATURAL_TSV,
        )

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
        parse_no_natural_tsv(DEFAULT_NO_NATURAL_TSV, campaign_heads={h.head for h in heads})


if __name__ == "__main__":
    unittest.main()
