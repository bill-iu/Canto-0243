"""Phase B PR1: dispatch_parsed public seam + parse classify-only (ADR-0002 / grill B)."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DISPATCH = REPO / "app" / "services" / "query_dispatch.py"
MODE = REPO / "app" / "services" / "query_mode_dispatch.py"
PARSE = REPO / "app" / "services" / "query_parse.py"


class PhaseBDispatchParsedSeam(unittest.TestCase):
    def test_query_engine_exposes_dispatch_parsed(self):
        from app.services.query_dispatch import QueryEngine

        self.assertTrue(callable(getattr(QueryEngine, "dispatch_parsed", None)))

    def test_mode_dispatch_does_not_call_private_dispatch(self):
        src = MODE.read_text(encoding="utf-8")
        self.assertNotIn("._dispatch", src)
        self.assertIn("dispatch_parsed", src)

    def test_query_parse_does_not_export_normalize_to_match_spec(self):
        src = PARSE.read_text(encoding="utf-8")
        self.assertNotIn("def normalize_to_match_spec", src)
        self.assertNotIn('"normalize_to_match_spec"', src)
        tree = ast.parse(src)
        names = {
            n.name
            for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertNotIn("normalize_to_match_spec", names)
        self.assertNotIn("build_match_spec", names)

    def test_query_dispatch_normalizes_via_compiler_not_parse(self):
        src = DISPATCH.read_text(encoding="utf-8")
        self.assertNotRegex(
            src,
            r"from app\.services\.query_parse import \([^)]*normalize_to_match_spec",
        )
        self.assertIn("compile_parsed_query", src)
        self.assertIn("dispatch_parsed", src)


if __name__ == "__main__":
    unittest.main()
