"""#3 驗收：query_lexer／query_grammar 為公開入口；word_query_parser facade 已移除。"""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICES = REPO_ROOT / "app" / "services"
GRAMMAR_DIR = SERVICES / "query_grammar"
FACADE_PATH = SERVICES / "word_query_parser.py"
LEXER_PATH = SERVICES / "query_lexer.py"


class QueryGrammarModuleSmokeTests(unittest.TestCase):
    def test_equals_framed_shape(self):
        from app.services.query_grammar.equals import is_framed_equals_query

        self.assertTrue(is_framed_equals_query("香港="))

    def test_plus_canonical_normalize(self):
        from app.services.query_grammar.plus import normalize_canonical_plus_query

        self.assertEqual(normalize_canonical_plus_query("香0"), "+香0")

    def test_serial_phoneme_anchor(self):
        from app.services.query_grammar.serial import parse_serial_phoneme_anchor_query

        parsed = parse_serial_phoneme_anchor_query("4困=")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["constraint"], "final")

    def test_rhyme_anchor(self):
        from app.services.query_grammar.rhyme import parse_rhyme_anchor_query

        parsed = parse_rhyme_anchor_query("困=")
        self.assertIsNotNone(parsed)

    def test_wca_anchor(self):
        from app.services.query_grammar.wca import parse_wildcard_code_anchor_query

        parsed = parse_wildcard_code_anchor_query("?30人")
        self.assertIsNotNone(parsed)

    def test_mask_slots(self):
        from app.services.query_grammar.mask import parse_mask_query

        width, _codes, _literals = parse_mask_query("門0")
        self.assertEqual(width, 2)

    def test_relation_syntax(self):
        from app.services.query_grammar.relation import parse_relation_syntax

        parsed = parse_relation_syntax("~開心")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["word"], "開心")
        self.assertEqual(parsed["kind"], "syn")


class QueryGrammarIsolationTests(unittest.TestCase):
    def test_word_query_parser_facade_removed(self):
        self.assertFalse(FACADE_PATH.is_file())

    def test_lexer_does_not_import_removed_facade(self):
        source = LEXER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("word_query_parser", source)

    def test_grammar_modules_do_not_import_removed_facade(self):
        for path in sorted(GRAMMAR_DIR.glob("*.py")):
            if path.name == "__init__.py":
                continue
            source = path.read_text(encoding="utf-8")
            with self.subTest(module=path.name):
                self.assertNotIn("word_query_parser", source)

    def test_query_parse_does_not_import_removed_facade(self):
        source = (SERVICES / "query_parse.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                self.assertNotEqual(node.module, "app.services.word_query_parser")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotIn("word_query_parser", alias.name)


class QueryGrammarPublicEntryTests(unittest.TestCase):
    def test_lexer_normalize_is_importable(self):
        from app.services.query_lexer import normalize_search_query

        self.assertEqual(normalize_search_query("香0"), "+香0")

    def test_grammar_mask_is_importable(self):
        from app.services.query_grammar.mask import parse_mask_query

        width, _codes, _literals = parse_mask_query("門0")
        self.assertEqual(width, 2)


if __name__ == "__main__":
    unittest.main()
