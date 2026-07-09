"""P1 #3: 搜尋模式轉接 detect — Python full-parse vs frontend regex adapters.

Case SSOT: contracts/relation-syntax-detect-cases.json
"""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CASES_PATH = REPO / "contracts" / "relation-syntax-detect-cases.json"


def load_detect_cases() -> dict:
    data = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if not isinstance(data.get("relation"), list) or not data["relation"]:
        raise SystemExit("relation-syntax-detect-cases.json: relation must be non-empty list")
    if not isinstance(data.get("ping_ze"), list) or not data["ping_ze"]:
        raise SystemExit("relation-syntax-detect-cases.json: ping_ze must be non-empty list")
    return data


class ModeDetectParity(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cases = load_detect_cases()

    def test_relation_case_table_has_family_coverage(self):
        families = {row.get("family") for row in self.cases["relation"]}
        for needed in (
            "compound_syn",
            "compound_ant",
            "relation_lookup",
            "compound_connect_syn",
            "compound_connect_ant",
            "fullwidth_normalize",
            "negative",
        ):
            self.assertIn(needed, families, msg=f"missing family {needed}")
        self.assertGreaterEqual(len(self.cases["relation"]), 20)

    def test_relation_detect_mjs_matches_python(self):
        from app.services.query_parse import is_relation_syntax_query

        for row in self.cases["relation"]:
            q = row["q"]
            expect = bool(row["expect"])
            with self.subTest(q=q, family=row.get("family")):
                self.assertEqual(is_relation_syntax_query(q), expect)
                js = self._eval_mjs("isRelationSyntaxQuery", q)
                self.assertEqual(js, expect)

    def test_ping_ze_detect_mjs_matches_python(self):
        from app.services.ping_zak import is_ping_ze_serial_query

        for row in self.cases["ping_ze"]:
            q = row["q"]
            expect = bool(row["expect"])
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
