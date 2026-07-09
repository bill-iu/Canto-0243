"""Phase C PR1: mask_family only via MatchSpec → execute_match_spec family (grill C1)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY_DISPATCH = REPO / "app" / "services" / "query_dispatch.py"
TS_DISPATCH = REPO / "client" / "src" / "db" / "query" / "dispatch.ts"


class PhaseCMatchSpecSeams(unittest.TestCase):
    def test_all_match_spec_kinds_route_mask_family(self):
        from app.services.query_kind_registry import (
            MATCH_SPEC_KINDS,
            RouteKind,
            route_kind_for,
        )

        for kind in MATCH_SPEC_KINDS:
            with self.subTest(kind=kind):
                self.assertEqual(route_kind_for(kind), RouteKind.MASK_FAMILY)

    def test_python_dispatch_mask_family_only_match_spec_pipeline(self):
        src = PY_DISPATCH.read_text(encoding="utf-8")
        self.assertIn("build_match_spec_for_parsed", src)
        self.assertIn("execute_match_spec", src)
        self.assertIn("_mask_family_search_result", src)
        # single entry — no parallel per-kind executors
        self.assertEqual(src.count("def _mask_family_search_result"), 1)
        forbidden = (
            "def execute_equals_query",
            "def run_equals_query",
            "def execute_mask_query",
            "def execute_rhyme_anchor",
            "def execute_plus_anchor",
            "execute_mask_family_search",
        )
        for sym in forbidden:
            with self.subTest(sym=sym):
                self.assertNotIn(sym, src)

    def test_python_mask_family_body_order(self):
        """Normalize then execute — no SQL between them in the thin helper."""
        src = PY_DISPATCH.read_text(encoding="utf-8")
        m = re.search(
            r"def _mask_family_search_result\(.*?\n(.*?)(?=\nclass |\ndef |\Z)",
            src,
            re.S,
        )
        self.assertIsNotNone(m)
        body = m.group(1)
        i_norm = body.find("build_match_spec_for_parsed")
        i_exec = body.find("execute_match_spec")
        self.assertGreaterEqual(i_norm, 0)
        self.assertGreater(i_exec, i_norm)

    def test_ts_dispatch_mask_family_single_entry(self):
        src = TS_DISPATCH.read_text(encoding="utf-8")
        self.assertIn("case RouteKind.MASK_FAMILY", src)
        self.assertIn("executeMaskFamilySearchResult", src)
        self.assertIn("normalizeToMatchSpec", src)
        # must use engine family (execute or filter)
        self.assertTrue(
            "executeMatchSpec" in src or "filterMatchSpecRows" in src,
            msg="TS mask path must call executeMatchSpec or filterMatchSpecRows",
        )
        self.assertEqual(src.count("async function executeMaskFamilySearchResult"), 1)
        forbidden = (
            "executeEqualsQuery",
            "runEqualsQuery",
            "executeMaskQuery",
            "executeRhymeAnchorQuery",
            "executePlusAnchorQuery",
            "executeSerialPhonemeQuery",
        )
        for sym in forbidden:
            with self.subTest(sym=sym):
                self.assertNotIn(sym, src)

    def test_ts_mask_family_case_only_calls_helper(self):
        src = TS_DISPATCH.read_text(encoding="utf-8")
        m = re.search(
            r"case RouteKind\.MASK_FAMILY:\s*return\s+(\w+)",
            src,
        )
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "executeMaskFamilySearchResult")

    def test_ts_mask_family_helper_sets_total(self):
        """C1.1: page contract always assigns total from ordered length."""
        src = TS_DISPATCH.read_text(encoding="utf-8")
        m = re.search(
            r"async function executeMaskFamilySearchResult[\s\S]*?return \{ items, total, hint \}",
            src,
        )
        self.assertIsNotNone(m, msg="executeMaskFamilySearchResult must return total")
        body = m.group(0)
        self.assertIn("const total = ordered.length", body)
        self.assertIn("normalizeToMatchSpec", body)


if __name__ == "__main__":
    unittest.main()
