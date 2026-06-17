"""Architecture #B — 查詢正規化與 parse 合併入口。"""
from __future__ import annotations

import unittest
from pathlib import Path

from app.services.query_parse import (
    CompoundSynQuery,
    MaskQuery,
    RelationLookupQuery,
    normalize_and_parse,
    normalize_query,
)


class NormalizeAndParseTests(unittest.TestCase):
    def test_normalize_query_maps_fullwidth_relation_operators(self):
        self.assertEqual(normalize_query(" ～開心 "), "~開心")

    def test_normalize_and_parse_classifies_relation_after_normalization(self):
        parsed = normalize_and_parse("～開心")
        self.assertIsInstance(parsed, RelationLookupQuery)
        self.assertEqual(parsed.relation_kind, "syn")
        self.assertEqual(parsed.word, "開心")

    def test_normalize_and_parse_classifies_mask_after_normalization(self):
        parsed = normalize_and_parse("香？？")
        self.assertIsInstance(parsed, MaskQuery)

    def test_normalize_and_parse_matches_chained_normalize_search_query(self):
        parsed = normalize_and_parse("~～")
        self.assertIsInstance(parsed, CompoundSynQuery)


class QueryDispatchParseSeamTests(unittest.TestCase):
    def test_query_dispatch_does_not_import_word_query_parser(self):
        source = (
            Path(__file__).resolve().parents[1]
            / "app"
            / "services"
            / "query_dispatch.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("word_query_parser", source)


if __name__ == "__main__":
    unittest.main()
