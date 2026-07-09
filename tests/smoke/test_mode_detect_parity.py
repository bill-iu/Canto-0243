"""Phase B PR3: frontend query-mode-detect vs Python is_relation_syntax_query / ping_ze."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

CASES_RELATION = [
    ("~~香", True),
    ("!!你", True),
    ("~開心", True),
    ("!快樂", True),
    ("~與~", True),
    ("開心", False),
    ("333", False),
    ("", False),
]

CASES_PING_ZE = [
    ("PPZ", True),
    ("P3Z", True),
    ("333", False),
    ("開心", False),
    ("", False),
]


class ModeDetectParity(unittest.TestCase):
    def test_relation_detect_mjs_matches_python(self):
        from app.services.query_parse import is_relation_syntax_query

        for q, expect in CASES_RELATION:
            with self.subTest(q=q):
                self.assertEqual(is_relation_syntax_query(q), expect)
                js = self._eval_mjs("isRelationSyntaxQuery", q)
                self.assertEqual(js, expect)

    def test_ping_ze_detect_mjs_matches_python(self):
        from app.services.ping_zak import is_ping_ze_serial_query

        for q, expect in CASES_PING_ZE:
            with self.subTest(q=q):
                self.assertEqual(bool(is_ping_ze_serial_query(q)), expect)
                js = self._eval_mjs("isPingZeSerialQuery", q)
                self.assertEqual(js, expect)

    def _eval_mjs(self, fn: str, q: str) -> bool:
        script = (
            f"import {{ {fn} }} from './frontend/query-mode-detect.mjs'; "
            f"console.log({fn}({q!r}) ? '1' : '0');"
        )
        proc = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        return proc.stdout.strip() == "1"


if __name__ == "__main__":
    unittest.main()
