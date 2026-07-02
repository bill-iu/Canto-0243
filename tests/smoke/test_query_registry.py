"""QueryKind / MatchSpec registry parity — 2 parametrized smoke tests."""
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
from app.services.query_match_spec_registry import MATCH_SPEC_BUILDERS, build_match_spec_for_parsed
from app.services.position_match.spec import get_equals_span
from app.services.query_parse import (
    CompoundAntQuery,
    CompoundSynQuery,
    HybridTailEqualsAliasQuery,
    QueryKind,
    normalize_and_parse,
    parse_query,
)
from app.services.query_lexer import normalize_search_query

from tests.smoke.golden_queries import (
    BUILDER_KINDS_WITH_REPRESENTATIVE_QUERY,
    MATCH_SPEC_REPRESENTATIVE_CASES,
)


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class QueryRegistrySmokeTests(unittest.TestCase):
    def test_query_kind_registry_complete(self):
        for kind in QueryKind:
            self.assertIn(kind, QUERY_KIND_META, msg=f"missing meta for {kind}")
        self.assertEqual(set(MATCH_SPEC_BUILDERS), set(MATCH_SPEC_KINDS))
        for kind in MASK_FAMILY_KINDS:
            self.assertEqual(route_kind_for(kind), RouteKind.MASK_FAMILY)
        self.assertTrue(
            uses_match_spec(CompoundSynQuery(code_prefix="33", rhyme_char="你"))
        )
        self.assertTrue(
            uses_match_spec(HybridTailEqualsAliasQuery(raw_q="23就=", hybrid_q="23就"))
        )
        self.assertFalse(uses_match_spec(normalize_and_parse("開心")))
        self.assertIn(QueryKind.HYBRID_TAIL_EQUALS_ALIAS, MASK_FAMILY_KINDS)
        self.assertNotIn(QueryKind.HYBRID_TAIL_EQUALS_ALIAS, MATCH_SPEC_KINDS)
        missing = set(MATCH_SPEC_BUILDERS) - {
            getattr(QueryKind, name) for name in BUILDER_KINDS_WITH_REPRESENTATIVE_QUERY
        }
        self.assertEqual(missing, set())

    def test_match_spec_representative_queries(self):
        for q, expected in MATCH_SPEC_REPRESENTATIVE_CASES:
            with self.subTest(q=q):
                parsed = _parse(q)
                spec = build_match_spec_for_parsed(parsed)
                self.assertIsNotNone(spec, msg=f"no spec for {q!r}")
                self.assertEqual(spec.width, expected["width"])
                if "ref_literal" in expected:
                    span = get_equals_span(spec)
                    self.assertIsNotNone(span)
                    self.assertEqual(span.ref_literal, expected["ref_literal"])
                if expected.get("whole_word"):
                    span = get_equals_span(spec)
                    self.assertIsNotNone(span)
                    self.assertTrue(span.whole_word)
                if expected.get("prefix_wildcard"):
                    self.assertTrue(spec.extra.get("prefix_wildcard_equals"))
                if "code_prefix" in expected:
                    self.assertEqual(spec.code_prefix, expected["code_prefix"])
                if "mask" in expected:
                    self.assertEqual(spec.mask, expected["mask"])
                if "compound_kind" in expected:
                    self.assertEqual(spec.compound_kind, expected["compound_kind"])
                if "hybrid_ref" in expected:
                    self.assertEqual(spec.hybrid_ref_chars, expected["hybrid_ref"])
                if expected.get("literal_priority"):
                    self.assertTrue(spec.literal_priority)
                if "anchor" in expected:
                    anchors = [s for s in spec.slots if s.kind.endswith("_anchor")]
                    self.assertTrue(any(s.value == expected["anchor"] for s in anchors))
                if "anchor_count" in expected:
                    anchors = [s for s in spec.slots if s.kind.endswith("_anchor")]
                    self.assertEqual(len(anchors), expected["anchor_count"])
                if expected.get("jyutping_slot"):
                    kinds = {s.kind for s in spec.slots}
                    self.assertTrue(
                        kinds & {"rhyme_letters", "syllable_letters", "initial_letters"}
                    )
                if expected.get("dual_phoneme"):
                    self.assertTrue(spec.extra.get("dual_phoneme"))
                if expected.get("partial_rhyme_mask"):
                    self.assertTrue(spec.extra.get("partial_rhyme_mask"))
                if expected.get("partial_initial_mask"):
                    self.assertTrue(spec.extra.get("partial_initial_mask"))


if __name__ == "__main__":
    unittest.main()
