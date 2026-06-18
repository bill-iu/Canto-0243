"""查詢語法正規化 — 全形標點與半形運算符等價。"""

from __future__ import annotations

import unittest

from app.services.query_parse import (
    CompoundAntQuery,
    CompoundSynQuery,
    MaskQuery,
    RelationLookupQuery,
    parse_query,
)
from app.services.word_query_parser import normalize_query_syntax, normalize_search_query


class NormalizeQuerySyntaxTests(unittest.TestCase):
    def test_double_operators_before_single(self):
        self.assertEqual(normalize_query_syntax("～～"), "~~")
        self.assertEqual(normalize_query_syntax("！！"), "!!")
        self.assertEqual(normalize_query_syntax("~～"), "~~")
        self.assertEqual(normalize_query_syntax("！!"), "!!")

    def test_relation_and_wildcard_singles(self):
        self.assertEqual(normalize_query_syntax("～開心"), "~開心")
        self.assertEqual(normalize_query_syntax("！你"), "!你")
        self.assertEqual(normalize_query_syntax("香？？"),"香??")

    def test_search_query_chains_code_tail(self):
        self.assertEqual(normalize_search_query(" 33～～你 "), "33~~你")
        self.assertEqual(normalize_search_query("23&就"), "23+就")
        self.assertEqual(normalize_search_query("2＊香=0"), "2+香=0")
        self.assertEqual(normalize_search_query("23＋就"), "23+就")
        self.assertEqual(normalize_search_query("?hon"), "?+hon")


class FullwidthParseGoldenTests(unittest.TestCase):
    def _parse(self, q: str):
        return parse_query(normalize_search_query(q))

    def test_fullwidth_syn_lookup(self):
        parsed = self._parse("～開心")
        self.assertIsInstance(parsed, RelationLookupQuery)
        self.assertEqual(parsed.relation_kind, "syn")
        self.assertEqual(parsed.word, "開心")

    def test_fullwidth_ant_lookup(self):
        parsed = self._parse("！你")
        self.assertIsInstance(parsed, RelationLookupQuery)
        self.assertEqual(parsed.relation_kind, "ant")
        self.assertEqual(parsed.word, "你")

    def test_mixed_double_compound_syn(self):
        parsed = self._parse("~～")
        self.assertIsInstance(parsed, CompoundSynQuery)

    def test_fullwidth_compound_ant(self):
        parsed = self._parse("！！")
        self.assertIsInstance(parsed, CompoundAntQuery)

    def test_fullwidth_mask_wildcard(self):
        parsed = self._parse("香？？")
        self.assertIsInstance(parsed, MaskQuery)


if __name__ == "__main__":
    unittest.main()
