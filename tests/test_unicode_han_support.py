from __future__ import annotations

import unittest

from app.domain.relations.valid_term import is_valid_term
from app.services.query_parse import normalize_and_parse
from app.services.query_types import QueryKind
from app.utils.han import contains_han, is_han_char, is_han_text
from ingest.lexicon_validate import normalize_lexicon_candidate


class TestUnicodeHanSupport(unittest.TestCase):
    def test_extension_b_is_han(self) -> None:
        self.assertTrue(is_han_char("𡁻"))
        self.assertTrue(contains_han("牛𡁻牡丹"))
        self.assertTrue(is_han_text("牛𡁻牡丹"))
        self.assertTrue(is_valid_term("牛𡁻牡丹"))

    def test_extension_b_lexicon_reading_and_lookup(self) -> None:
        self.assertEqual(
            normalize_lexicon_candidate("牛𡁻牡丹", "ngau4 ziu6 maau5 daan1"),
            ("牛𡁻牡丹", "ngau4 ziu6 maau5 daan1", "0253"),
        )
        self.assertEqual(normalize_and_parse("牛𡁻牡丹").kind, QueryKind.WORD_LOOKUP)

    def test_non_han_is_not_admitted_as_han(self) -> None:
        self.assertFalse(is_han_char("A"))
        self.assertFalse(is_han_text("牛A"))

    def test_length_limit_counts_han_slots_not_punctuation(self) -> None:
        self.assertTrue(is_valid_term("多你一個唔多，少你一個唔少"))


if __name__ == "__main__":
    unittest.main()
