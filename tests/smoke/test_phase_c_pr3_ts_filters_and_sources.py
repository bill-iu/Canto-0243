"""Phase C PR3: TS filters F1–F5 layout + CandidateSource truncation contract."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PM = REPO / "client" / "src" / "db" / "position-match"
FILTERS_DIR = PM / "filters"
MAX_LINES = 350


class PhaseCPr3TsFilters(unittest.TestCase):
    def test_ts_filters_family_modules(self):
        expected = {
            "f1-slot-code.ts": ("matchesCodePositions", "filterWordsByCodeAndMask"),
            "f2-phoneme-anchor.ts": ("matchesPhonemeAtPosition", "anchorPhonemeOptions"),
            "f3-letters.ts": ("slotConstraintMatches", "narrowByJyutpingLetterSlots"),
            "apply.ts": ("applyMatchSpec", "filterCandidatesByMatchSpec"),
        }
        self.assertTrue(FILTERS_DIR.is_dir())
        for name, symbols in expected.items():
            path = FILTERS_DIR / name
            with self.subTest(name=name):
                self.assertTrue(path.is_file())
                src = path.read_text(encoding="utf-8")
                lines = src.count("\n") + 1
                self.assertLessEqual(lines, MAX_LINES, msg=f"{name}={lines}")
                for sym in symbols:
                    self.assertTrue(
                        re.search(rf"(export )?(async )?function {sym}\b", src)
                        or re.search(rf"export async function {sym}\b", src),
                        msg=f"{name} missing {sym}",
                    )
        # F4 already equals-filters.ts at package parent
        equals = PM / "equals-filters.ts"
        self.assertTrue(equals.is_file())
        self.assertIn("queryWordsByEqualsSpec", equals.read_text(encoding="utf-8"))

    def test_filters_barrel_reexports(self):
        barrel = PM / "filters.ts"
        self.assertTrue(barrel.is_file())
        src = barrel.read_text(encoding="utf-8")
        self.assertIn("from './filters/", src)
        self.assertIn("applyMatchSpec", src)
        self.assertIn("matchesCodePositions", src)
        self.assertIn("anchorPhonemeOptions", src)


class PhaseCPr3CandidateTruncation(unittest.TestCase):
    def test_shared_fallback_limit_constant(self):
        """P3 #7: limit SSOT is contracts/ + _generated; modules import it."""
        py = (REPO / "app" / "services" / "position_match" / "sources.py").read_text(
            encoding="utf-8"
        )
        ts = (PM / "candidate-policy.ts").read_text(encoding="utf-8")
        gen_py = (
            REPO / "app" / "services" / "_generated" / "candidate_source_policy.py"
        ).read_text(encoding="utf-8")
        gen_ts = (
            REPO / "client" / "src" / "db" / "_generated" / "candidate-source-policy.ts"
        ).read_text(encoding="utf-8")
        self.assertIn("CANDIDATE_FALLBACK_LIMIT = 2000", gen_py)
        self.assertIn("export const CANDIDATE_FALLBACK_LIMIT = 2000", gen_ts)
        self.assertIn("candidate_source_policy", py)
        self.assertIn("CANDIDATE_FALLBACK_LIMIT", py)
        self.assertIn("candidate-source-policy", ts)
        self.assertIn("CANDIDATE_FALLBACK_LIMIT", ts)

        from app.services.position_match.sources import CANDIDATE_FALLBACK_LIMIT

        self.assertEqual(CANDIDATE_FALLBACK_LIMIT, 2000)

    def test_ts_sources_use_policy_limit(self):
        src = (PM / "sources.ts").read_text(encoding="utf-8")
        self.assertIn("CANDIDATE_FALLBACK_LIMIT", src)
        self.assertIn("from './candidate-policy.ts'", src)

    def test_python_get_candidates_default_limit(self):
        from app.services.position_match import sources as src

        import inspect

        sig = inspect.signature(src.get_candidates_for_length)
        param = sig.parameters["fallback_limit"]
        self.assertEqual(param.default, src.CANDIDATE_FALLBACK_LIMIT)


if __name__ == "__main__":
    unittest.main()
