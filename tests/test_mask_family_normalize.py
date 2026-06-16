"""查詢分派正規化 — normalize_to_match_spec（原 mask_family_normalize）。"""
from __future__ import annotations

import unittest

from app.services.query_parse import (
    EqualsQuery,
    HybridCodeQuery,
    HybridTailEqualsAliasQuery,
    MaskQuery,
    build_equals_match_spec,
    normalize_to_match_spec,
    parse_query,
)


class NormalizeToMatchSpecTests(unittest.TestCase):
    def test_alias_rewrites_to_hybrid_code(self):
        alias = parse_query("23就=")
        self.assertIsInstance(alias, HybridTailEqualsAliasQuery)
        spec = normalize_to_match_spec(alias)
        self.assertIsNotNone(spec)
        self.assertEqual(spec.width, 2)
        self.assertEqual(spec.code_prefix, "23")

    def test_equals_spec_literals(self):
        for q in ("香港=", "=香港", "2=我3", "34=我"):
            spec = build_equals_match_spec(q)
            self.assertIsNotNone(spec)
            self.assertTrue(spec.ref_literal)

    def test_mask_query_spec_width(self):
        spec = normalize_to_match_spec(MaskQuery(raw_q="門0"))
        self.assertEqual(spec.width, 2)
        self.assertTrue(spec.literal_priority)


if __name__ == "__main__":
    unittest.main()