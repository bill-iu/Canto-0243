"""缺字型正規化模組 — 查詢分派層 ParsedQuery → MatchSpec。"""
from __future__ import annotations

import unittest

from app.services.mask_family_normalize import (
    build_equals_match_spec,
    build_mask_family_match_spec,
    normalize_mask_family_parsed,
)
from app.services.query_parse import (
    EqualsQuery,
    HybridCodeQuery,
    HybridTailEqualsAliasQuery,
    MaskQuery,
    parse_query,
)


class MaskFamilyNormalizeTests(unittest.TestCase):
    def test_alias_rewrites_to_hybrid_code(self):
        alias = parse_query("23就=")
        self.assertIsInstance(alias, HybridTailEqualsAliasQuery)
        normalized = normalize_mask_family_parsed(alias)
        self.assertIsInstance(normalized, HybridCodeQuery)
        self.assertEqual(normalized.raw_q, "23就")

    def test_equals_spec_matches_position_match_reexport(self):
        from app.services.position_match import build_equals_match_spec as legacy

        for q in ("香港=", "=香港", "2=我3", "34=我"):
            self.assertEqual(
                build_equals_match_spec(q).ref_literal,
                legacy(q).ref_literal,
            )

    def test_mask_query_spec_width(self):
        spec = build_mask_family_match_spec(MaskQuery(raw_q="門0"))
        self.assertEqual(spec.width, 2)
        self.assertTrue(spec.literal_priority)


if __name__ == "__main__":
    unittest.main()
