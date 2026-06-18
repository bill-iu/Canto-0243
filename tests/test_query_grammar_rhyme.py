"""#3 rhyme.py — 公開行為（TDD 垂直切片）。"""
from __future__ import annotations

import unittest


class RhymeBlocksStarNormalizeTests(unittest.TestCase):
    def test_rhyme_anchor_shape_blocks_star_insertion(self):
        from app.services.query_grammar import rhyme as rhyme_grammar

        self.assertTrue(rhyme_grammar.blocks_star_normalize("23就="))
        self.assertFalse(rhyme_grammar.blocks_star_normalize("香0"))


class RhymeParseTests(unittest.TestCase):
    def test_single_syllable_final_anchor(self):
        from app.services.query_grammar.rhyme import parse_rhyme_anchor_query

        parsed = parse_rhyme_anchor_query("就=")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["constraint"], "final")
        self.assertEqual(parsed["width"], 1)

    def test_triple_middle_rhyme_after_normalize(self):
        from app.services.query_grammar.rhyme import parse_triple_rhyme_anchor_query
        from app.services.query_lexer import normalize_search_query

        q = normalize_search_query("?港=?")
        parsed = parse_triple_rhyme_anchor_query(q)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["width"], 3)
        self.assertEqual(parsed["anchor"], "港")


class RhymeStarIntegrationTests(unittest.TestCase):
    def test_normalize_leaves_rhyme_query_unchanged(self):
        from app.services.query_lexer import normalize_search_query

        self.assertEqual(normalize_search_query("就="), "就=")

    def test_parse_via_facade(self):
        from app.services.query_grammar.rhyme import parse_rhyme_anchor_query

        parsed = parse_rhyme_anchor_query("=就")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["constraint"], "initial")
