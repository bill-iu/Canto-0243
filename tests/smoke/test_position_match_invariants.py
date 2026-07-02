"""position_match 底層 invariant — equals span / mask 邊界。"""
from __future__ import annotations

import unittest

from app.services.position_match.spec import get_equals_span
from app.services.query_match_spec_registry import build_match_spec_for_parsed
from app.services.query_lexer import normalize_search_query
from app.services.query_parse import build_equals_match_spec, parse_query


def _span(spec):
    span = get_equals_span(spec)
    assert span is not None
    return span


class PositionMatchInvariantTests(unittest.TestCase):
    def test_whole_word_equals_span(self):
        spec = build_equals_match_spec("香港=")
        span = _span(spec)
        self.assertEqual(span.ref_literal, "香港")
        self.assertTrue(span.whole_word)
        self.assertEqual(spec.width, 2)

    def test_code_sandwich_initial_anchor(self):
        spec = build_equals_match_spec("2=我3")
        span = _span(spec)
        self.assertEqual(span.ref_literal, "我")
        self.assertEqual(span.dimension, "initial")
        self.assertTrue(span.phoneme_anchor_only)
        self.assertEqual(spec.code_prefix, "23")

    def test_prefix_wildcard_equals_flag(self):
        parsed = parse_query(normalize_search_query("?困潦倒="))
        spec = build_match_spec_for_parsed(parsed)
        self.assertIsNotNone(spec)
        self.assertTrue(spec.extra.get("prefix_wildcard_equals"))

    def test_left_code_only_equals_start_pos(self):
        spec = build_equals_match_spec("34=我")
        span = _span(spec)
        self.assertEqual(span.ref_literal, "我")
        self.assertEqual(span.start_pos, 1)


if __name__ == "__main__":
    unittest.main()
