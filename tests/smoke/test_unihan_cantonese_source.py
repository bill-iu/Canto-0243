from __future__ import annotations

import json
import unittest
from pathlib import Path

from ingest.lexicon_sources import ingest_lexicon_json

ROOT = Path(__file__).resolve().parents[2]


class TestUnihanCantoneseSource(unittest.TestCase):
    def test_snapshot_is_pinned_membership_intersection(self) -> None:
        meta = json.loads(
            (ROOT / "data" / "lexicon" / "unihan_cantonese.manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(meta["unicode_version"], "17.0.0")
        self.assertEqual(meta["membership_policy"], "intersection_with_existing_single_han_literals")
        self.assertEqual(len(meta["archive_sha256"]), 64)
        self.assertGreater(meta["n_reading_rows"], 20_000)

    def test_property_level_provenance_and_extension_b(self) -> None:
        rows = ingest_lexicon_json(
            ROOT / "data" / "lexicon" / "unihan_cantonese.json", source_id="unihan"
        )
        readings = {row.jyutping: row for row in rows if row.char == "𡁻"}
        self.assertEqual(set(readings), {"ziu1", "ziu6"})
        self.assertIn("unihan-kcantonese", readings["ziu1"].sources)
        self.assertIn("unihan-kcheungbauer", readings["ziu6"].sources)


if __name__ == "__main__":
    unittest.main()
