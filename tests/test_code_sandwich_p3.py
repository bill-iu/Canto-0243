"""數字夾字 P3 — golden journey 代表查詢與尾韻回歸（ADR-0028）。"""
from __future__ import annotations

import unittest

from app.models.word import Word  # noqa: F401
from app.services.position_match.spec import get_equals_span
from app.services.query_dispatch import QueryEngine, SearchContext
from app.services.query_explain import explain_query
from app.services.query_parse import build_equals_match_spec, normalize_and_parse
from app.services.query_types import QueryKind
from tests.smoke.helpers import LYRICS_DB, lyrics_sessionmaker


class CodeSandwichGoldenParseTests(unittest.TestCase):
    def test_39起_parses_as_equals(self):
        parsed = normalize_and_parse("39起")
        self.assertEqual(parsed.kind, QueryKind.EQUALS)
        self.assertEqual(parsed.raw_q, "39起=")

    def test_39起_equals_span_tail_rhyme(self):
        spec = build_equals_match_spec("39起=")
        span = get_equals_span(spec)
        self.assertEqual(span.ref_literal, "起")
        self.assertEqual(span.dimension, "final")
        self.assertFalse(span.phoneme_anchor_only)
        from app.services.position_match.mask_adapter import code_digit_string_from_spec

        self.assertEqual(code_digit_string_from_spec(spec), "39")

    def test_explain_39起_labels_code_sandwich(self):
        result = explain_query("39起")
        self.assertEqual(result.kind, "equals")
        self.assertIn("數字夾字", result.summary or "")
        self.assertIn("起", result.summary or "")

    def test_explain_framed_equals_labels_initial_phoneme(self):
        result = explain_query("2=我3")
        self.assertEqual(result.kind, "equals")
        self.assertIn("同聲", result.summary or "")


@unittest.skipUnless(LYRICS_DB.is_file(), "lyrics.db required")
class CodeSandwichTailRhymeRegressionTests(unittest.TestCase):
    def test_39起_includes_飛起_and_飛機(self):
        Session = lyrics_sessionmaker()
        with Session() as db:
            result = QueryEngine().execute(
                SearchContext(
                    q="39起",
                    code=None,
                    char=None,
                    mode="m1",
                    limit=500,
                    offset=0,
                    db=db,
                )
            )
        words = [row["char"] for row in result.items]
        self.assertIn("飛起", words)
        self.assertIn("飛機", words)

    def test_9太2_m1_includes_解毒(self):
        """碼夾 phoneme_anchor_only：m1 變體池 >2000 時唔因 LIMIT 漏「解毒」。"""
        Session = lyrics_sessionmaker()
        with Session() as db:
            result = QueryEngine().execute(
                SearchContext(
                    q="9太=2",
                    code=None,
                    char=None,
                    mode="m1",
                    limit=100,
                    offset=0,
                    db=db,
                )
            )
        words = [row["char"] for row in result.items]
        self.assertIn("解毒", words)


if __name__ == "__main__":
    unittest.main()