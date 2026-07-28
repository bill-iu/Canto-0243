"""Keep production dispatch on the canonical compiler seam."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class CanonicalArchitectureTests(unittest.TestCase):
    def test_python_compiler_has_no_registry_fallback(self) -> None:
        source = (ROOT / "app/services/position_match/compiler.py").read_text(encoding="utf-8")
        self.assertNotIn("query_match_spec_registry", source)

    def test_python_dispatch_uses_canonical_execution_entry(self) -> None:
        source = (ROOT / "app/services/query_dispatch.py").read_text(encoding="utf-8")
        self.assertIn("compile_parsed_query", source)
        self.assertIn("execute_canonical_match_spec", source)
        self.assertNotIn("build_match_spec_for_parsed", source)

    def test_python_canonical_execution_does_not_convert_back_to_legacy(self) -> None:
        source = (ROOT / "app/services/position_match/engine.py").read_text(encoding="utf-8")
        self.assertNotIn("canonical_match_spec_to_legacy", source)


if __name__ == "__main__":
    unittest.main()
