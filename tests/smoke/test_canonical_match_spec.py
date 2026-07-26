"""Legacy MatchSpec adapter parity for the canonical compiler seam."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.services.position_match.canonical import (
    canonical_match_spec_to_json,
    canonicalize_legacy_match_spec,
)
from app.services.query_match_spec_registry import build_match_spec_for_parsed
from app.services.query_parse import normalize_and_parse


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "contracts" / "match-spec-cases.json"


class CanonicalMatchSpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = json.loads(CASES.read_text(encoding="utf-8"))

    def test_legacy_adapter_matches_shared_corpus(self) -> None:
        for item in self.doc["cases"]:
            with self.subTest(item["id"]):
                parsed = normalize_and_parse(item["query"], mode=item["mode"])
                spec = build_match_spec_for_parsed(parsed)
                self.assertIsNotNone(spec, item["id"])
                got = canonical_match_spec_to_json(canonicalize_legacy_match_spec(spec))
                self.assertEqual(got, item["expected"])

    def test_lookup_is_not_in_match_spec_corpus(self) -> None:
        queries = {item["query"] for item in self.doc["cases"]}
        self.assertNotIn("香港", queries)
        self.assertNotIn("事業", queries)


if __name__ == "__main__":
    unittest.main()
