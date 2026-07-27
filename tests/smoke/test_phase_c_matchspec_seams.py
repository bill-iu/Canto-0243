"""Phase C PR1: mask_family only via MatchSpec → execute_match_spec family (grill C1)."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY_DISPATCH = REPO / "app" / "services" / "query_dispatch.py"
TS_DISPATCH = REPO / "client" / "src" / "db" / "query" / "dispatch.ts"
TS_MASK_EXEC = REPO / "client" / "src" / "db" / "query" / "mask-family-executor.ts"


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
        self.assertIn("compile_parsed_query", src)
        self.assertIn("execute_canonical_match_spec", src)
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
        i_norm = body.find("compile_parsed_query")
        i_exec = body.find("execute_canonical_match_spec")
        self.assertGreaterEqual(i_norm, 0)
        self.assertGreater(i_exec, i_norm)

    def test_ts_dispatch_mask_family_single_entry(self):
        """P3#5: thin dispatch delegates; MatchSpec work lives in mask-family-executor."""
        src = TS_DISPATCH.read_text(encoding="utf-8")
        exec_src = TS_MASK_EXEC.read_text(encoding="utf-8")
        self.assertIn("case RouteKind.MASK_FAMILY", src)
        self.assertIn("executeMaskFamilySearchResult", src)
        self.assertIn("mask-family-executor", src)
        self.assertIn("compileParsedQuery", exec_src)
        self.assertTrue(
            "executeMatchSpec" in exec_src or "filterMatchSpecRows" in exec_src,
            msg="TS mask executor must call executeMatchSpec or filterMatchSpecRows",
        )
        self.assertEqual(exec_src.count("export async function executeMaskFamilySearchResult"), 1)
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
                self.assertNotIn(sym, exec_src)

    def test_ts_mask_family_case_only_calls_helper(self):
        src = TS_DISPATCH.read_text(encoding="utf-8")
        m = re.search(
            r"case RouteKind\.MASK_FAMILY:\s*return\s+(\w+)",
            src,
        )
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "executeMaskFamilySearchResult")

    def test_ts_mask_family_helper_sets_total(self):
        """C1.1: page contract always assigns total (executor owns body after P3#5)."""
        src = TS_MASK_EXEC.read_text(encoding="utf-8")
        m = re.search(
            r"export async function executeMaskFamilySearchResult[\s\S]*?return \{ items, total, hint \}",
            src,
        )
        self.assertIsNotNone(m, msg="executeMaskFamilySearchResult must return total")
        body = m.group(0)
        # total from unique char set of ordered rows (not raw ordered.length)
        self.assertIn("const total =", body)
        self.assertIn("compileParsedQuery", body)


if __name__ == "__main__":
    unittest.main()
