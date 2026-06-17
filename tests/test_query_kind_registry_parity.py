"""QueryKind 元資料 ↔ route ↔ MatchSpec builder parity。"""
from __future__ import annotations

import unittest

from app.services.query_kind_registry import (
    MASK_FAMILY_KINDS,
    MATCH_SPEC_KINDS,
    QUERY_KIND_META,
    RouteKind,
    route_kind_for,
    uses_match_spec,
)
from app.services.query_match_spec_registry import MATCH_SPEC_BUILDERS
from app.services.query_parse import (
    CompoundAntQuery,
    CompoundSynQuery,
    HybridTailEqualsAliasQuery,
    QueryKind,
    normalize_and_parse,
)


class QueryKindRegistryParityTests(unittest.TestCase):
    def test_every_query_kind_has_meta(self):
        for kind in QueryKind:
            self.assertIn(kind, QUERY_KIND_META, msg=f"missing meta for {kind}")

    def test_match_spec_builders_match_meta(self):
        self.assertEqual(set(MATCH_SPEC_BUILDERS), set(MATCH_SPEC_KINDS))

    def test_mask_family_route_kinds(self):
        for kind in MASK_FAMILY_KINDS:
            self.assertEqual(route_kind_for(kind), RouteKind.MASK_FAMILY)

    def test_uses_match_spec_aligns_with_meta(self):
        self.assertTrue(
            uses_match_spec(CompoundSynQuery(code_prefix="33", rhyme_char="你"))
        )
        self.assertTrue(
            uses_match_spec(HybridTailEqualsAliasQuery(raw_q="23就=", hybrid_q="23就"))
        )
        self.assertFalse(uses_match_spec(normalize_and_parse("開心")))

    def test_hybrid_tail_alias_in_mask_family_not_builder(self):
        self.assertIn(QueryKind.HYBRID_TAIL_EQUALS_ALIAS, MASK_FAMILY_KINDS)
        self.assertNotIn(QueryKind.HYBRID_TAIL_EQUALS_ALIAS, MATCH_SPEC_KINDS)


if __name__ == "__main__":
    unittest.main()
