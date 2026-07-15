"""Phase D: dual-port 查詢語意解釋 parity vs contracts/query-explain-parity.json."""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONTRACT = REPO / "contracts" / "query-explain-parity.json"
TS_SCRIPT = REPO / "client" / "scripts" / "query-explain-parity-self-check.ts"


def _load_cases() -> list[dict]:
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise AssertionError("query-explain-parity: empty cases")
    return cases


def _assert_case(case: dict, summary: str | None, warning: str | None, kind: str | None) -> None:
    q = case["q"]
    if "kind" in case and case["kind"] is not None:
        assert kind == case["kind"], f"{q!r}: kind {kind!r} != {case['kind']!r}"
    text_s = summary or ""
    text_w = warning or ""
    for needle in case.get("summary_contains") or []:
        assert needle in text_s, f"{q!r}: summary missing {needle!r} in {text_s!r}"
    for needle in case.get("summary_not_contains") or []:
        assert needle not in text_s, f"{q!r}: summary must not contain {needle!r}: {text_s!r}"
    for needle in case.get("warning_contains") or []:
        assert needle in text_w, f"{q!r}: warning missing {needle!r} in {text_w!r}"
    if "summary_eq" in case:
        assert text_s == case["summary_eq"], f"{q!r}: summary_eq"
    if "warning_eq" in case:
        assert text_w == (case["warning_eq"] or ""), f"{q!r}: warning_eq"


def _assert_ir(q: str, expected: dict, actual: dict | None) -> None:
    assert actual is not None, f"{q!r}: missing Explain IR"
    if "variant" in expected:
        assert actual.get("variant") == expected["variant"], (
            f"{q!r}: variant {actual.get('variant')!r} != {expected['variant']!r}"
        )
    if "width" in expected:
        assert actual.get("width") == expected["width"], (
            f"{q!r}: width {actual.get('width')!r} != {expected['width']!r}"
        )
    if "raw_q" in expected:
        assert actual.get("raw_q") == expected["raw_q"], (
            f"{q!r}: raw_q {actual.get('raw_q')!r} != {expected['raw_q']!r}"
        )
    if "equals" in expected:
        actual_eq = actual.get("equals") or {}
        for key, value in expected["equals"].items():
            assert actual_eq.get(key) == value, (
                f"{q!r}: equals.{key} {actual_eq.get(key)!r} != {value!r}"
            )
    if "constraints" in expected:
        actual_cs = actual.get("constraints") or []
        for exp_c in expected["constraints"]:
            found = any(
                all(item.get(k) == v for k, v in exp_c.items()) for item in actual_cs
            )
            assert found, f"{q!r}: constraint {exp_c!r} not in {actual_cs!r}"


class QueryExplainParity(unittest.TestCase):
    def test_contract_file_shape(self):
        self.assertTrue(CONTRACT.is_file(), msg=str(CONTRACT))
        cases = _load_cases()
        self.assertGreaterEqual(len(cases), 4)
        for case in cases:
            with self.subTest(q=case.get("q")):
                self.assertIn("q", case)
                self.assertTrue(
                    case.get("summary_contains")
                    or case.get("warning_contains")
                    or "summary_eq" in case
                    or "warning_eq" in case,
                    msg="case needs at least one assertion",
                )

    def test_python_explain_matches_contract(self):
        from app.services.query_explain import explain_ir_for_query, explain_query

        for case in _load_cases():
            with self.subTest(q=case["q"]):
                r = explain_query(case["q"])
                _assert_case(case, r.summary, r.warning, r.kind)
                if case.get("ir_assert"):
                    ir = explain_ir_for_query(case["q"])
                    _assert_ir(case["q"], case["ir_assert"], ir)

    def test_ts_self_check_when_available(self):
        if not TS_SCRIPT.is_file():
            self.skipTest("TS parity script missing")
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        tsx = REPO / "client" / "node_modules" / "tsx" / "dist" / "cli.mjs"
        npx = shutil.which("npx")
        if tsx.is_file():
            cmd = [node, str(tsx), str(TS_SCRIPT)]
        elif npx:
            cmd = [npx, "--yes", "tsx", str(TS_SCRIPT)]
        else:
            cmd = [node, "--import", "tsx", str(TS_SCRIPT)]
        proc = subprocess.run(
            cmd,
            cwd=REPO / "client",
            capture_output=True,
            text=True,
            check=False,
        )
        err = (proc.stderr or "") + (proc.stdout or "")
        if proc.returncode != 0 and (
            "Cannot find package" in err
            or "not found" in err.lower()
            or "ENOENT" in err
        ):
            self.skipTest(f"tsx unavailable: {err[:200]}")
        self.assertEqual(proc.returncode, 0, msg=err)
        self.assertIn("query-explain-parity ok", proc.stdout)


if __name__ == "__main__":
    unittest.main()
