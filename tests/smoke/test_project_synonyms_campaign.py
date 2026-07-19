"""專案自建近義 campaign freeze／清單契約 smoke。"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ingest.project_synonyms import (
    PROJECT_SYN_SOURCE,
    TSV_HEADER,
    ensure_empty_list,
    parse_project_synonyms_tsv,
)
from ingest.project_synonyms_campaign import (
    TOP5000_SYN_SPEC,
    get_syn_campaign_spec,
)


class ProjectSynonymsCampaignTests(unittest.TestCase):
    def test_spec_ids(self) -> None:
        self.assertEqual(get_syn_campaign_spec("syn_top5000").campaign_id, "syn_top5000")
        self.assertEqual(get_syn_campaign_spec("syn_len4").batch_size, 500)

    def test_ensure_and_parse_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tsv = Path(tmp) / "project_synonyms.tsv"
            meta = Path(tmp) / "project_synonyms.meta.json"
            ensure_empty_list(tsv, meta)
            self.assertEqual(
                tsv.read_text(encoding="utf-8").splitlines()[0],
                "\t".join(TSV_HEADER),
            )
            pairs = parse_project_synonyms_tsv(tsv, require_file=True)
            self.assertEqual(pairs, [])

    def test_source_id(self) -> None:
        self.assertEqual(PROJECT_SYN_SOURCE, "project_syn")

    def test_frozen_manifest_matches_meta_if_present(self) -> None:
        """若 repo 已 freeze，manifest 列數須等於 meta.k（freeze 後再入帳唔改 manifest）。"""
        import json

        if not TOP5000_SYN_SPEC.manifest_tsv.is_file():
            self.skipTest("syn_top5000 manifest not frozen yet")
        meta = json.loads(TOP5000_SYN_SPEC.manifest_meta.read_text(encoding="utf-8"))
        lines = [
            ln
            for ln in TOP5000_SYN_SPEC.manifest_tsv.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("rank")
        ]
        self.assertEqual(len(lines), int(meta["k"]))
        self.assertEqual(lines[0].split("\t")[1], "係")


if __name__ == "__main__":
    unittest.main()
