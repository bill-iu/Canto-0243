"""接縫：query_parse 瘦 orchestrator；型別在 query_types。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PARSE_PATH = REPO_ROOT / "app" / "services" / "query_parse.py"
TYPES_PATH = REPO_ROOT / "app" / "services" / "query_types.py"


class TestQueryParseTypesSeam(unittest.TestCase):
    def test_types_live_in_query_types_module(self):
        self.assertTrue(TYPES_PATH.is_file())
        types_src = TYPES_PATH.read_text(encoding="utf-8")
        self.assertIn("class QueryKind", types_src)
        self.assertIn("class MaskQuery", types_src)

    def test_query_parse_does_not_define_query_kind(self):
        src = PARSE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("class QueryKind", src)
        self.assertIn("from app.services.query_types import", src)


if __name__ == "__main__":
    unittest.main()
