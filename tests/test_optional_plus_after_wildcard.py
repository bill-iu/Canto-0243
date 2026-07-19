"""A1 / P→W: ?錨 ≡ ?+錨 (2 slots); bare 就= / =就 stay 1-slot."""

from __future__ import annotations

import unittest

from app.services.query_lexer import normalize_search_query
from app.services.query_match_spec_registry import build_match_spec_for_parsed
from app.services.query_parse import parse_query


def _width(q: str) -> int:
    normalized = normalize_search_query(q)
    spec = build_match_spec_for_parsed(parse_query(normalized, mode="m1"))
    assert spec is not None
    return spec.width


class OptionalPlusAfterWildcardTests(unittest.TestCase):
    def test_rhyme_wildcard_keeps_two_slots(self) -> None:
        self.assertEqual(normalize_search_query("?就="), "?就=")
        self.assertEqual(_width("?就="), 2)
        self.assertEqual(_width("?+就="), 2)
        self.assertEqual(_width("就="), 1)

    def test_initial_wildcard_keeps_two_slots(self) -> None:
        self.assertEqual(normalize_search_query("?=就"), "?=就")
        self.assertEqual(_width("?=就"), 2)
        self.assertEqual(_width("?+=就"), 2)
        self.assertEqual(_width("=就"), 1)

    def test_jyutping_optional_plus(self) -> None:
        self.assertEqual(_width("?hon"), 2)
        self.assertEqual(_width("?+hon"), 2)

    def test_code_abut_plus_still_lengthens(self) -> None:
        # 無前置 ? 時 + 仍分詞長（唔喺呢單測 parse 成敗，只鎖 normalize 唔亂刪）
        self.assertEqual(normalize_search_query("23+o"), "23+o")
        self.assertNotEqual(normalize_search_query("23o"), "23+o")


if __name__ == "__main__":
    unittest.main()
