#!/usr/bin/env python3
"""Golden parity: Python explain_query vs client query-explain.ts."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.services.query_explain import explain_query
from tests.smoke.golden_explains import GOLDEN_EXPLAIN_CASES, ExplainCase


def _esbuild_cmd() -> list[str]:
    esbuild_js = REPO_ROOT / "client" / "node_modules" / "esbuild" / "bin" / "esbuild"
    if not esbuild_js.is_file():
        raise RuntimeError("missing esbuild — run: cd client && npm install")
    return [os.environ.get("NODE", "node"), str(esbuild_js)]


def _typescript_side(batch: list[tuple[int, ExplainCase]]) -> dict[int, dict]:
    bundle_dir = REPO_ROOT / "client" / ".tmp"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = bundle_dir / "explain-parity.mjs"

    build = subprocess.run(
        [
            *_esbuild_cmd(),
            "scripts/explain-parity-run.ts",
            "--bundle",
            "--platform=node",
            "--format=esm",
            "--packages=external",
            f"--outfile={bundle_path}",
        ],
        cwd=REPO_ROOT / "client",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if build.returncode != 0:
        raise RuntimeError(f"esbuild failed\n{build.stderr}")

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(
            [{"id": i, "query": c.query} for i, c in batch],
            f,
            ensure_ascii=False,
        )
        cases_path = f.name

    try:
        proc = subprocess.run(
            [os.environ.get("NODE", "node"), str(bundle_path), cases_path],
            cwd=REPO_ROOT / "client",
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    finally:
        os.unlink(cases_path)

    if proc.returncode != 0:
        raise RuntimeError(
            "TS explain runner failed\n"
            f"stdout: {proc.stdout}\n"
            f"stderr: {proc.stderr}"
        )

    rows = json.loads(proc.stdout or "[]")
    return {row["id"]: row for row in rows}


def _python_side(case_id: int, case: ExplainCase) -> dict:
    result = explain_query(case.query)
    return {
        "id": case_id,
        "summary": result.summary,
        "warning": result.warning,
        "kind": result.kind,
    }


def _compare(py: dict, ts: dict) -> dict:
    issues: list[str] = []
    for field in ("summary", "warning", "kind"):
        if (py.get(field) or None) != (ts.get(field) or None):
            issues.append(field)
    if ts.get("error"):
        issues.append(f"ts_error:{ts['error']}")
    return {
        "match": not issues,
        "issues": issues,
        "python": py,
        "typescript": ts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="PWA explain golden parity")
    parser.add_argument("--json", action="store_true", help="JSON report")
    args = parser.parse_args()

    batch = list(enumerate(GOLDEN_EXPLAIN_CASES))
    ts_by_id = _typescript_side(batch)
    report: list[dict] = []

    for case_id, case in batch:
        py = _python_side(case_id, case)
        ts = ts_by_id.get(case_id, {"error": "missing ts row"})
        compared = _compare(py, ts)
        report.append(
            {
                "id": case_id,
                "query": case.query,
                **compared,
            }
        )

    passed = sum(1 for r in report if r["match"])
    total = len(report)

    if args.json:
        print(json.dumps({"passed": passed, "total": total, "report": report}, ensure_ascii=False, indent=2))
    else:
        print(f"PWA explain parity: {passed}/{total} matched\n")
        for row in report:
            mark = "OK" if row["match"] else "FAIL"
            print(f"[{mark}] {row['query']!r}")
            if not row["match"]:
                print(f"  issues: {row['issues']}")
                print(f"  python: {row['python']}")
                print(f"  ts:     {row['typescript']}")

    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
