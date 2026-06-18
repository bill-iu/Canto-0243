"""mask_adapter — 執行期比對與 position_match seam。"""
from __future__ import annotations

import unittest
from pathlib import Path

from app.services.position_match.mask_adapter import (
    matches_mask_literal_chars,
    required_codes_from_spec,
)
from app.services.position_match.spec import MatchSpec, SlotConstraint
from app.services.query_match_spec_registry import build_match_spec_for_parsed
from app.services.query_parse import parse_query
from app.services.query_lexer import normalize_search_query
from app.services.query_grammar.mask import parse_mask_query

REPO_ROOT = Path(__file__).resolve().parents[1]
POSITION_MATCH_DIR = REPO_ROOT / "app" / "services" / "position_match"


class MaskAdapterTests(unittest.TestCase):
    def test_matches_mask_literal_chars(self):
        self.assertTrue(matches_mask_literal_chars("門口", "門?"))
        self.assertFalse(matches_mask_literal_chars("門前", "門口"))

    def test_required_codes_from_spec_matches_parse_mask_query(self):
        parsed = parse_query(normalize_search_query("門0"))
        spec = build_match_spec_for_parsed(parsed)
        self.assertIsNotNone(spec)
        _, parser_codes, _ = parse_mask_query(spec.mask)
        self.assertEqual(required_codes_from_spec(spec), parser_codes)


class PositionMatchParserSeamTests(unittest.TestCase):
    def test_position_match_modules_do_not_import_word_query_parser(self):
        for path in POSITION_MATCH_DIR.glob("*.py"):
            if path.name == "__init__.py":
                continue
            source = path.read_text(encoding="utf-8")
            with self.subTest(module=path.name):
                self.assertNotIn("from app.services.word_query_parser", source)
                self.assertNotIn("import app.services.word_query_parser", source)


if __name__ == "__main__":
    unittest.main()
