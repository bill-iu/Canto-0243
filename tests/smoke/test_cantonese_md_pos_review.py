from __future__ import annotations

import csv
import unittest
from pathlib import Path

from ingest.project_pos import parse_project_pos_tsv

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "data" / "pos" / "audit" / "cantonese_md_xiehouyu_review.tsv"


class TestCantoneseMdPosReview(unittest.TestCase):
    def test_all_reviewed_terms_are_high_trust_xiehouyu(self) -> None:
        with REVIEW.open(encoding="utf-8", newline="") as handle:
            reviewed = list(csv.DictReader(handle, delimiter="\t"))
        self.assertEqual(len(reviewed), 241)
        self.assertEqual(len({row["literal"] for row in reviewed}), 241)
        self.assertEqual({row["family"] for row in reviewed}, {"xiehouyu"})
        self.assertTrue(all("explanation-reviewed" in row["evidence"] for row in reviewed))

        project = parse_project_pos_tsv()
        for row in reviewed:
            applied = project[row["literal"]]
            self.assertEqual(applied.family, "xiehouyu")
            self.assertEqual(applied.pos, frozenset(row["pos"].split(",")))
            self.assertEqual(applied.trust(), "high")


if __name__ == "__main__":
    unittest.main()
