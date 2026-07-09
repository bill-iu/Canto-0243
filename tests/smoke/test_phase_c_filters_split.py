"""Phase C PR2: position_match filters split by F1–F5 (grill C2)."""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FILTERS_PKG = REPO / "app" / "services" / "position_match" / "filters"
# Soft ADR-0022: implementation modules (not __init__) under 350 lines
MAX_LINES = 350

EXPECTED = {
    "f1_slot_code.py": ("matches_code_positions", "filter_words_by_code_and_mask"),
    "f2_phoneme_anchor.py": ("matches_phoneme_at_position", "contextual_final_options_at_position"),
    "f3_letters.py": ("slot_constraint_matches",),
    "f4_equals.py": ("query_words_by_equals_spec", "matches_equals_phoneme_span"),
    "apply.py": ("apply_match_spec", "filter_candidates_by_match_spec"),
}


class PhaseCFiltersSplit(unittest.TestCase):
    def test_package_layout(self):
        self.assertTrue(FILTERS_PKG.is_dir(), msg="filters/ package required")
        self.assertTrue((FILTERS_PKG / "__init__.py").is_file())
        for name in EXPECTED:
            with self.subTest(name=name):
                path = FILTERS_PKG / name
                self.assertTrue(path.is_file(), msg=f"missing {name}")

    def test_no_monolithic_filters_py(self):
        mono = REPO / "app" / "services" / "position_match" / "filters.py"
        self.assertFalse(mono.is_file(), msg="filters.py must become package filters/")

    def test_module_line_caps(self):
        for name in EXPECTED:
            path = FILTERS_PKG / name
            lines = path.read_text(encoding="utf-8").count("\n") + 1
            with self.subTest(name=name, lines=lines):
                self.assertLessEqual(lines, MAX_LINES, msg=f"{name} too large ({lines})")

    def test_symbols_live_in_family_modules(self):
        for name, symbols in EXPECTED.items():
            src = (FILTERS_PKG / name).read_text(encoding="utf-8")
            for sym in symbols:
                with self.subTest(name=name, sym=sym):
                    self.assertIn(f"def {sym}", src)

    def test_public_import_path(self):
        from app.services.position_match.filters import apply_match_spec
        from app.services.position_match.filters import matches_code_positions
        from app.services.position_match.filters import contextual_final_options_at_position
        from app.services.position_match.engine import execute_match_spec

        self.assertTrue(callable(apply_match_spec))
        self.assertTrue(callable(matches_code_positions))
        self.assertTrue(callable(contextual_final_options_at_position))
        self.assertTrue(callable(execute_match_spec))


if __name__ == "__main__":
    unittest.main()
