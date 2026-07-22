"""碼夾等號 P1 — normalize、分派、equals MatchSpec（ADR-0028）。"""
from __future__ import annotations

import unittest

from app.services.position_match.spec import SlotConstraint, get_equals_span
from app.services.query_lexer import normalize_search_query
from app.services.query_match_spec_registry import build_match_spec_for_parsed
from app.services.query_parse import build_equals_match_spec, normalize_and_parse
from app.services.query_types import QueryKind


class CodeSandwichNormalizeTests(unittest.TestCase):
    def test_23就_appends_tail_equals(self):
        self.assertEqual(normalize_search_query("23就"), "23就=")

    def test_32就起_appends_tail_equals(self):
        self.assertEqual(normalize_search_query("32就起"), "32就起=")

    def test_skips_when_equals_present(self):
        self.assertEqual(normalize_search_query("2=我3"), "2^我3")
        self.assertEqual(normalize_search_query("2^我3"), "2^我3")
        self.assertEqual(normalize_search_query("23就="), "23就=")


class CodeSandwichDispatchTests(unittest.TestCase):
    def test_23就_parses_as_equals(self):
        parsed = normalize_and_parse("23就")
        self.assertEqual(parsed.kind, QueryKind.EQUALS)
        self.assertEqual(parsed.raw_q, "23就=")

    def test_23就_equals_not_serial(self):
        parsed = normalize_and_parse("23就=")
        self.assertEqual(parsed.kind, QueryKind.EQUALS)

    def test_multi_anchor_serial_unchanged(self):
        parsed = normalize_and_parse("04困=49倒=")
        self.assertEqual(parsed.kind, QueryKind.SERIAL_PHONEME)


class CodeSandwichEqualsSpecTests(unittest.TestCase):
    def test_23就_equals_span_and_code_digits(self):
        spec = build_equals_match_spec("23就=")
        self.assertIsNotNone(spec)
        span = get_equals_span(spec)
        self.assertIsNotNone(span)
        self.assertEqual(span.ref_literal, "就")
        self.assertEqual(span.dimension, "final")
        self.assertFalse(span.phoneme_anchor_only)
        self.assertEqual(spec.width, 2)
        from app.services.position_match.mask_adapter import code_digit_string_from_spec

        self.assertEqual(code_digit_string_from_spec(spec), "23")
        digits = [s for s in spec.slots if s.kind == "code_digit"]
        self.assertEqual(digits, [
            SlotConstraint(pos=0, kind="code_digit", value="2"),
            SlotConstraint(pos=1, kind="code_digit", value="3"),
        ])

    def test_normalized_23就_builds_same_spec(self):
        from app.services.position_match.mask_adapter import code_digit_string_from_spec

        q = normalize_search_query("23就")
        direct = build_equals_match_spec(q)
        parsed = normalize_and_parse("23就")
        via_parsed = build_match_spec_for_parsed(parsed)
        self.assertEqual(direct.width, via_parsed.width)
        self.assertEqual(
            code_digit_string_from_spec(direct),
            code_digit_string_from_spec(via_parsed),
        )
        self.assertEqual(
            get_equals_span(direct).ref_literal,
            get_equals_span(via_parsed).ref_literal,
        )


if __name__ == "__main__":
    unittest.main()