"""ADR-0062: rhyme `=` / initial `^` — normalize aliases + dual-mark reject."""

from __future__ import annotations

import unittest

from app.services.position_match.spec import get_equals_span
from app.services.query_grammar.equals import build_equals_match_spec
from app.services.query_lexer import normalize_search_query
from app.services.query_match_spec_registry import build_match_spec_for_parsed
from app.services.query_parse import parse_query
from app.services.query_types import QueryKind, UnmatchedQuery


def _spec(q: str):
    nq = normalize_search_query(q)
    return build_match_spec_for_parsed(parse_query(nq, mode="m1"))


class InitialCaretSyntaxTests(unittest.TestCase):
    def test_normalize_left_equals_to_caret(self) -> None:
        self.assertEqual(normalize_search_query("=就"), "^就")
        self.assertEqual(normalize_search_query("?=就"), "?^就")
        self.assertEqual(normalize_search_query("?+=就"), "?+^就")
        self.assertEqual(normalize_search_query("2=我3"), "2^我3")
        self.assertEqual(normalize_search_query("04=困49=倒"), "04^困49^倒")
        self.assertEqual(normalize_search_query("=香港"), "^香港")
        self.assertEqual(normalize_search_query("?=困潦倒"), "?^困潦倒")

    def test_normalize_preserves_rhyme_equals(self) -> None:
        self.assertEqual(normalize_search_query("就="), "就=")
        self.assertEqual(normalize_search_query("香港="), "香港=")
        self.assertEqual(normalize_search_query("04困=49倒="), "04困=49倒=")
        self.assertEqual(normalize_search_query("23就"), "23就=")

    def test_caret_and_legacy_same_spec(self) -> None:
        for old, new in (
            ("=就", "^就"),
            ("?=就", "?^就"),
            ("2=我3", "2^我3"),
            ("04=困49=倒", "04^困49^倒"),
            ("=香港", "^香港"),
        ):
            a, b = _spec(old), _spec(new)
            self.assertIsNotNone(a)
            self.assertIsNotNone(b)
            self.assertEqual(a.width, b.width)
            self.assertEqual(
                [(s.pos, s.kind, s.value) for s in (a.slots or [])],
                [(s.pos, s.kind, s.value) for s in (b.slots or [])],
            )
            sa, sb = get_equals_span(a), get_equals_span(b)
            if sa or sb:
                self.assertEqual(sa and sa.dimension, sb and sb.dimension)
                self.assertEqual(sa and sa.ref_literal, sb and sb.ref_literal)

    def test_framed_caret_initial_dimension(self) -> None:
        spec = build_equals_match_spec("2^我3")
        self.assertIsNotNone(spec)
        span = get_equals_span(spec)
        self.assertEqual(span.dimension, "initial")
        legacy = build_equals_match_spec("2=我3")
        self.assertEqual(get_equals_span(legacy).dimension, "initial")

    def test_dual_mark_rejected(self) -> None:
        for q in ("^香=", "^香港=", "04困=49^倒"):
            nq = normalize_search_query(q)
            parsed = parse_query(nq, mode="m1")
            self.assertIsInstance(parsed, UnmatchedQuery)
            self.assertIn("^", parsed.hint or "")

    def test_pure_literal_still_lookup(self) -> None:
        parsed = parse_query(normalize_search_query("香港"), mode="m1")
        self.assertEqual(parsed.kind, QueryKind.WORD_LOOKUP)
        extension_b = parse_query(normalize_search_query("牛𡁻牡丹"), mode="m1")
        self.assertEqual(extension_b.kind, QueryKind.WORD_LOOKUP)
        self.assertEqual(normalize_search_query("0253牛𡁻牡丹"), "0253牛𡁻牡丹=")
        extension_b_equals = parse_query(normalize_search_query("牛𡁻牡丹="), mode="m1")
        self.assertEqual(extension_b_equals.kind, QueryKind.EQUALS)


if __name__ == "__main__":
    unittest.main()
