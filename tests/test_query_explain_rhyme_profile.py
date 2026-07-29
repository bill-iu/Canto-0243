"""Portable explain API / explain_query rhyme_profile (ADR-0078 E1)."""
from __future__ import annotations

import unittest

from app.services.query_explain import explain_query


class ExplainRhymeProfileTests(unittest.TestCase):
    def test_exact_no_suffix(self) -> None:
        r = explain_query("就=", "m1", rhyme_profile="exact")
        self.assertIsNotNone(r.summary)
        self.assertNotIn("通韻", r.summary or "")
        self.assertNotIn("腹韻", r.summary or "")

    def test_tong_suffix_on_rhyme(self) -> None:
        r = explain_query("就=", "m1", rhyme_profile="tong")
        self.assertIsNotNone(r.summary)
        self.assertIn("（通韻）", r.summary or "")

    def test_nucleus_suffix(self) -> None:
        r = explain_query("香港=", "m1", rhyme_profile="nucleus")
        self.assertIsNotNone(r.summary)
        self.assertIn("（腹韻）", r.summary or "")

    def test_no_rhyme_no_suffix(self) -> None:
        r = explain_query("23", "m1", rhyme_profile="tong")
        self.assertIsNotNone(r.summary)
        self.assertNotIn("通韻", r.summary or "")

    def test_lookup_no_suffix(self) -> None:
        r = explain_query("香港", "m1", rhyme_profile="coda")
        self.assertEqual(r.summary, "查詢詞條「香港」")


if __name__ == "__main__":
    unittest.main()
