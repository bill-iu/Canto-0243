#!/usr/bin/env python3
"""Golden parity: portable (Python QueryEngine) vs PWA (client query-engine.ts).

Runs parity cases against both engines and reports mismatches.

Suites:
  - journey (18): GOLDEN_QUERY_JOURNEYS — D-G1 gate (default exit code)
  - match_spec (15): MATCH_SPEC_REPRESENTATIVE_CASES — M2 baseline (informational)

Usage (repo root):
  python scripts/pwa_golden_parity.py
  python scripts/pwa_golden_parity.py --json
  python scripts/pwa_golden_parity.py --gate all   # fail if match_spec also fails
  python scripts/pwa_golden_parity.py --suite journey
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.word import Word
from app.services.query_dispatch import QueryEngine, SearchContext
from app.services.query_parse import normalize_and_parse
from tests.smoke.golden_queries import (
    ALL_PARITY_CASES,
    PARITY_JOURNEY_CASES,
    PARITY_MATCH_SPEC_CASES,
    ParityCase,
)
from tests.smoke.helpers import FIXTURE_DB, fixture_sessionmaker, seed_happy_sad

GateMode = Literal["journeys", "all"]
SuiteFilter = Literal["all", "journey", "match_spec"]


def _kind_label(kind: Any) -> str:
    name = getattr(kind, "name", None) or str(kind)
    return name.upper()


def _extract_chars(items: list) -> list[str]:
    chars: list[str] = []
    for item in items:
        if isinstance(item, dict):
            c = item.get("char")
        else:
            c = getattr(item, "char", None)
        if c:
            chars.append(c)
    return chars


def _seed_memory_db(seed: str, dest: Path) -> None:
    engine = create_engine(f"sqlite:///{dest.as_posix()}")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    with Session() as db:
        if seed == "left_code":
            db.add_all(
                [
                    Word(
                        char="好我",
                        code="34",
                        jyutping="hou2 ngo5",
                        finals='["ou", "o"]',
                        initials='["h", "ng"]',
                        length=2,
                    ),
                    Word(
                        char="小馬騮",
                        code="944",
                        jyutping="siu2 maa5 ngau4",
                        finals='["iu", "aa", "au"]',
                        initials='["s", "m", "ng"]',
                        length=3,
                    ),
                ]
            )
            db.commit()
        elif seed == "relation_syn":
            seed_happy_sad(db)
        else:
            raise ValueError(f"unknown seed: {seed}")


def _python_side(case_id: int, case: ParityCase, db_path: Path) -> dict:
    if case.db == "fixture":
        Session = fixture_sessionmaker()
    else:
        engine = create_engine(f"sqlite:///{db_path.as_posix()}")
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    engine = QueryEngine()
    with Session() as db:
        parsed = normalize_and_parse(case.query)
        ctx = SearchContext(
            q=case.query,
            code=None,
            char=None,
            mode=case.mode,
            limit=10,
            offset=0,
            db=db,
        )
        result = engine.execute(ctx)

    return {
        "id": case_id,
        "kind": _kind_label(parsed.kind),
        "chars": _extract_chars(result.items),
        "hint": result.hint,
    }


def _esbuild_cmd() -> list[str]:
    esbuild_js = REPO_ROOT / "client" / "node_modules" / "esbuild" / "bin" / "esbuild"
    if not esbuild_js.is_file():
        raise RuntimeError("missing esbuild — run: cd client && npm install")
    return [os.environ.get("NODE", "node"), str(esbuild_js)]


def _typescript_side(db_path: Path, batch: list[tuple[int, ParityCase]]) -> dict[int, dict]:
    bundle_dir = REPO_ROOT / "client" / ".tmp"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_path = bundle_dir / "golden-parity.mjs"

    build = subprocess.run(
        [
            *_esbuild_cmd(),
            "scripts/golden-parity-run.ts",
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
            [{"id": i, "query": c.query, "mode": c.mode} for i, c in batch],
            f,
            ensure_ascii=False,
        )
        cases_path = f.name

    try:
        proc = subprocess.run(
            [
                os.environ.get("NODE", "node"),
                str(bundle_path),
                str(db_path.resolve()),
                cases_path,
            ],
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
            "TS runner failed\n"
            f"stdout: {proc.stdout}\n"
            f"stderr: {proc.stderr}"
        )

    rows = json.loads(proc.stdout or "[]")
    return {row["id"]: row for row in rows}


def _compare(py: dict, ts: dict, *, ordered: bool) -> dict:
    issues: list[str] = []
    if py["kind"] != _kind_label(ts.get("kind", "")):
        issues.append("kind")
    py_chars = py["chars"]
    ts_chars = ts.get("chars", [])
    if ordered:
        if py_chars != ts_chars:
            issues.append("order")
    elif sorted(py_chars) != sorted(ts_chars):
        issues.append("chars")
    if (py["hint"] or None) != (ts.get("hint") or None):
        issues.append("hint")
    if ts.get("error"):
        issues.append(f"ts_error:{ts['error']}")
    return {
        "match": not issues,
        "issues": issues,
        "python": py,
        "typescript": ts,
    }


def _suite_summary(report: list[dict], suite: str) -> dict[str, int]:
    rows = [r for r in report if r["suite"] == suite]
    passed = sum(1 for r in rows if r["match"])
    return {"passed": passed, "total": len(rows)}


def _select_cases(suite: SuiteFilter) -> tuple[ParityCase, ...]:
    if suite == "journey":
        return PARITY_JOURNEY_CASES
    if suite == "match_spec":
        return PARITY_MATCH_SPEC_CASES
    return ALL_PARITY_CASES


def _run_cases(cases: tuple[ParityCase, ...]) -> list[dict]:
    groups: dict[tuple[str, str], list[tuple[int, ParityCase]]] = {}
    for i, case in enumerate(cases):
        key = (case.db, case.seed)
        groups.setdefault(key, []).append((i, case))

    report: list[dict] = []
    temp_dbs: list[Path] = []

    try:
        for (db_kind, seed), batch in groups.items():
            if db_kind == "fixture":
                db_path = FIXTURE_DB
            else:
                fd, tmp = tempfile.mkstemp(suffix=".db")
                os.close(fd)
                db_path = Path(tmp)
                temp_dbs.append(db_path)
                _seed_memory_db(seed, db_path)

            ts_by_id = _typescript_side(db_path, batch)

            for case_id, case in batch:
                py = _python_side(case_id, case, db_path)
                ts = ts_by_id.get(case_id, {"error": "missing ts row"})
                compared = _compare(py, ts, ordered=case.ordered)
                report.append(
                    {
                        "id": case_id,
                        "suite": case.suite,
                        "query": case.query,
                        "mode": case.mode,
                        "db": case.db,
                        "ordered": case.ordered,
                        **compared,
                    }
                )
    finally:
        for p in temp_dbs:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass  # ponytail: Windows may keep sqlite handle briefly

    report.sort(key=lambda r: (r["suite"], r["id"]))
    return report


def _print_human(report: list[dict], *, gate: GateMode) -> None:
    journey = _suite_summary(report, "journey")
    match_spec = _suite_summary(report, "match_spec")

    if journey["total"]:
        print(f"=== Journeys (gate: {gate}) ===")
        print(f"PWA golden parity journeys: {journey['passed']}/{journey['total']} matched\n")
        for r in report:
            if r["suite"] != "journey":
                continue
            _print_row(r)

    if match_spec["total"]:
        print(f"=== Match spec (M2 baseline) ===")
        print(f"PWA golden parity match_spec: {match_spec['passed']}/{match_spec['total']} matched\n")
        for r in report:
            if r["suite"] != "match_spec":
                continue
            _print_row(r)


def _print_row(r: dict) -> None:
    mark = "OK" if r["match"] else "FAIL"
    ordered = " ordered" if r.get("ordered") else ""
    print(f"[{mark}] {r['query']!r} mode={r['mode']} db={r['db']}{ordered}")
    if not r["match"]:
        print(f"       issues: {', '.join(r['issues'])}")
        print(f"       py kind={r['python']['kind']} chars={r['python']['chars'][:8]}")
        ts = r["typescript"]
        print(f"       ts kind={_kind_label(ts.get('kind', ''))} chars={ts.get('chars', [])[:8]}")
        if ts.get("error"):
            print(f"       ts error: {ts['error']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="PWA vs portable golden query parity")
    parser.add_argument("--json", action="store_true", help="emit JSON report only")
    parser.add_argument(
        "--gate",
        choices=("journeys", "all"),
        default="journeys",
        help="exit 0 only when selected suite(s) pass (default: journeys=D-G1)",
    )
    parser.add_argument(
        "--suite",
        choices=("all", "journey", "match_spec"),
        default="all",
        help="which cases to run (default: all)",
    )
    args = parser.parse_args()

    if not FIXTURE_DB.is_file():
        print(f"missing fixture db: {FIXTURE_DB}", file=sys.stderr)
        return 2

    cases = _select_cases(args.suite)
    report = _run_cases(cases)

    journey = _suite_summary(report, "journey")
    match_spec = _suite_summary(report, "match_spec")
    gate_ok = journey["passed"] == journey["total"] if journey["total"] else True
    if args.gate == "all":
        gate_ok = gate_ok and (
            match_spec["passed"] == match_spec["total"] if match_spec["total"] else True
        )

    if args.json:
        payload = {
            "gate": args.gate,
            "gate_pass": gate_ok,
            "journeys": journey,
            "match_spec": match_spec,
            "cases": report,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_human(report, gate=args.gate)
        if args.gate == "all":
            print(
                f"Gate ({args.gate}): "
                f"{'PASS' if gate_ok else 'FAIL'} "
                f"(journeys {journey['passed']}/{journey['total']}, "
                f"match_spec {match_spec['passed']}/{match_spec['total']})"
            )

    return 0 if gate_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
