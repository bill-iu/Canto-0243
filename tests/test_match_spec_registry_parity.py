"""QueryKind → MatchSpec registry parity（Phase 1 驗收）。"""
from __future__ import annotations

import unittest

from app.services.query_match_spec_registry import MATCH_SPEC_BUILDERS, build_match_spec_for_parsed
from app.services.position_match.spec import get_equals_span
from app.services.query_parse import QueryKind, normalize_and_parse, parse_query
from app.services.query_lexer import normalize_search_query


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class MatchSpecRegistryParityTests(unittest.TestCase):
    def test_every_builder_kind_has_representative_query(self):
        missing = set(MATCH_SPEC_BUILDERS) - {
            QueryKind.EQUALS,
            QueryKind.PREFIX_WILDCARD_EQUALS,
            QueryKind.SERIAL_PHONEME,
            QueryKind.PLUS_ANCHOR,
            QueryKind.LITERAL_REF,
            QueryKind.WILDCARD_CODE_ANCHOR,
            QueryKind.CODE_REF_MIDDLE_RHYME,
            QueryKind.RHYME_ANCHOR,
            QueryKind.TRIPLE_RHYME_ANCHOR,
            QueryKind.JYUTPING_ANCHOR,
            QueryKind.HYBRID_CODE,
            QueryKind.MASK,
            QueryKind.COMPOUND_SYN,
            QueryKind.COMPOUND_DOUBLED_SYLLABLE,
            QueryKind.COMPOUND_ANT,
            QueryKind.PARTIAL_RHYME_MASK,
            QueryKind.PARTIAL_INITIAL_MASK,
        }
        self.assertEqual(missing, set())

    def test_representative_queries(self):
        cases = [
            ("香港=", {"width": 2, "ref_literal": "香港", "whole_word": True}),
            ("?困潦倒=", {"width": 4, "prefix_wildcard": True}),
            ("04困=49倒=", {"width": 4, "anchor_kinds": {"final_anchor"}, "anchor_count": 2}),
            ("23+就", {"width": 3, "code_prefix": "23"}),
            ("23@就", {"width": 2, "mask": "?就"}),
            ("?30人", {"width": 3}),
            ("?3人=?", {"width": 3}),
            ("就=", {"width": 1, "anchor": "就"}),
            ("?+港=?", {"width": 3, "anchor": "港"}),
            ("?yut?", {"width": 3, "jyutping_slot": True}),
            ("3m4", {"width": 2, "dual_phoneme": True}),
            ("23就", {"width": 2, "hybrid_ref": "就"}),
            ("門0", {"width": 2, "literal_priority": True}),
            ("33~~你", {"width": 2, "compound_kind": "syn", "code_prefix": "33"}),
            ("$$", {"width": 2, "compound_kind": "doubled_syllable"}),
            ("33!!你", {"width": 2, "compound_kind": "ant", "code_prefix": "33"}),
            ("349~與~你", {"width": 3, "compound_kind": "syn", "code_prefix": "349", "connective": "與"}),
            ("!與!", {"width": 3, "compound_kind": "ant", "connective": "與"}),
            ("窮?潦倒=", {"width": 4, "partial_rhyme_mask": True, "anchor_count": 3}),
            ("=窮?潦倒", {"width": 4, "partial_initial_mask": True, "anchor_count": 3}),
            ("?=困潦倒", {"width": 4, "prefix_wildcard": True}),
        ]
        for q, expected in cases:
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
                if "connective" in expected:
                    self.assertEqual(spec.extra.get("connective"), expected["connective"])
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
                    self.assertIn("dual_initial_spec", spec.extra)
                    self.assertIn("dual_final_spec", spec.extra)
                if expected.get("partial_rhyme_mask"):
                    self.assertTrue(spec.extra.get("partial_rhyme_mask"))
                if expected.get("partial_initial_mask"):
                    self.assertTrue(spec.extra.get("partial_initial_mask"))

    def test_alias_rewrite_before_registry(self):
        from app.services.query_parse import HybridTailEqualsAliasQuery, normalize_to_match_spec

        spec = normalize_to_match_spec(
            HybridTailEqualsAliasQuery(raw_q="23就=", hybrid_q="23就")
        )
        self.assertIsNotNone(spec)
        self.assertEqual(spec.hybrid_ref_chars, "就")


if __name__ == "__main__":
    unittest.main()
