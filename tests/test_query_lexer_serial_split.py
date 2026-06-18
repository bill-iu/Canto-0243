"""#3 試點：query_lexer + query_grammar.serial 公開行為（TDD 垂直切片）。"""
from __future__ import annotations

import unittest


class QueryLexerCoreTests(unittest.TestCase):
    def test_middle_rhyme_triple_inserts_plus_connector(self):
        from app.services.query_lexer import normalize_search_query_core

        self.assertEqual(normalize_search_query_core("?港=?"), "?+港=?")


class QueryGrammarSerialTests(unittest.TestCase):
    def test_four_syllable_serial_rhyme_parse(self):
        from app.services.query_grammar.serial import parse_serial_phoneme_anchor_query

        parsed = parse_serial_phoneme_anchor_query("04困=49倒=")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["width"], 4)
        self.assertEqual(len(parsed["anchors"]), 2)

    def test_prefix_wildcard_equals_shape(self):
        from app.services.query_grammar.serial import parse_prefix_wildcard_equals_query

        parsed = parse_prefix_wildcard_equals_query("?困潦倒=")
        self.assertEqual(parsed["width"], 4)
        self.assertEqual(parsed["ref_literal"], "困潦倒")


class QueryParserFacadeTests(unittest.TestCase):
    def test_normalize_search_query_end_to_end_via_facade(self):
        from app.services.query_lexer import normalize_search_query

        self.assertEqual(normalize_search_query(" 23&就 "), "23+就")

    def test_normalize_search_query_via_lexer_module(self):
        from app.services.query_lexer import normalize_search_query

        self.assertEqual(normalize_search_query("香0"), "+香0")

    def test_serial_parse_via_facade(self):
        from app.services.query_grammar.serial import parse_serial_phoneme_anchor_query

        parsed = parse_serial_phoneme_anchor_query("4困=")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["constraint"], "final")


class QueryGrammarPlusEqualsTests(unittest.TestCase):
    def test_framed_equals_via_equals_stub(self):
        from app.services.query_grammar.equals import is_framed_equals_query

        self.assertTrue(is_framed_equals_query("香港="))
        self.assertTrue(is_framed_equals_query("2=我3"))

    def test_plus_head_literal_normalize(self):
        from app.services.query_grammar.plus import normalize_canonical_plus_query

        self.assertEqual(normalize_canonical_plus_query("香0"), "+香0")

    def test_mask_from_canonical_plus(self):
        from app.services.query_grammar.plus import mask_from_canonical_plus_query

        self.assertEqual(mask_from_canonical_plus_query("+門0"), "門0")

    def test_grammar_modules_do_not_import_word_query_parser(self):
        from pathlib import Path

        grammar_dir = Path(__file__).resolve().parents[1] / "app" / "services" / "query_grammar"
        for path in grammar_dir.glob("*.py"):
            if path.name == "__init__.py":
                continue
            source = path.read_text(encoding="utf-8")
            with self.subTest(module=path.name):
                self.assertNotIn("from app.services.word_query_parser", source)
                self.assertNotIn("import app.services.word_query_parser", source)
