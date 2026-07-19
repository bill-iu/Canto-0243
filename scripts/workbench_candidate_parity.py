#!/usr/bin/env python3
"""Cross-runtime parity for workbench replacement candidates and reasons."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.schemas.workbench_schema import ReplacementPlanV1
from app.services.workbench.replacement_planner import plan_replacements
from tests.smoke.helpers import FIXTURE_DB, fixture_sessionmaker


PLANS = [
    {
        "version": 1, "selectionVersion": 1, "width": 1, "mode": "m3",
        "slots": [
            {"pos": 0, "kind": "literal_char", "literal": "好"},
            {"pos": 0, "kind": "code_digit", "digit": "9"},
        ],
        "semanticIntent": "off", "limit": 8,
    },
    {
        "version": 1, "selectionVersion": 2, "width": 1, "mode": "m3",
        "slots": [{"pos": 0, "kind": "literal_char", "literal": "你"}],
        "semanticIntent": "off", "limit": 8,
    },
    {
        "version": 1, "selectionVersion": 3, "width": 2, "mode": "m3",
        "slots": [
            {"pos": 0, "kind": "code_digit", "digit": "0"},
            {"pos": 1, "kind": "code_digit", "digit": "9"},
        ],
        "semanticIntent": "off", "limit": 8,
    },
    {
        "version": 1, "selectionVersion": 4, "width": 4, "mode": "m1",
        "slots": [
            {"pos": 1, "kind": "final_anchor", "ref": "困", "refJyutping": "kwan3"},
            {"pos": 2, "kind": "final_anchor", "ref": "潦", "refJyutping": "liu5"},
            {"pos": 3, "kind": "final_anchor", "ref": "倒", "refJyutping": "dou2"},
        ],
        "semanticIntent": "off", "limit": 8,
    },
]


def _without_none(value):
    if isinstance(value, dict):
        return {key: _without_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [_without_none(item) for item in value]
    return value


def _portable() -> dict[int, dict]:
    Session = fixture_sessionmaker()
    with Session() as db:
        return {
            index: _without_none(plan_replacements(
                ReplacementPlanV1.model_validate(plan), db
            ).model_dump(by_alias=True))
            for index, plan in enumerate(PLANS)
        }


def _pwa() -> dict[int, dict]:
    esbuild = REPO_ROOT / "client" / "node_modules" / "esbuild" / "bin" / "esbuild"
    bundle_dir = REPO_ROOT / "client" / ".tmp"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle = bundle_dir / "workbench-candidate-parity.mjs"
    build = subprocess.run(
        [os.environ.get("NODE", "node"), str(esbuild), "scripts/workbench-candidate-run.ts",
         "--bundle", "--platform=node", "--format=esm", "--packages=external", f"--outfile={bundle}"],
        cwd=REPO_ROOT / "client", capture_output=True, text=True, encoding="utf-8", check=False,
    )
    if build.returncode != 0:
        raise RuntimeError(build.stderr)
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as handle:
        json.dump([{"id": index, "plan": plan} for index, plan in enumerate(PLANS)], handle, ensure_ascii=False)
        cases_path = handle.name
    try:
        proc = subprocess.run(
            [os.environ.get("NODE", "node"), str(bundle), str(FIXTURE_DB), cases_path],
            cwd=REPO_ROOT / "client", capture_output=True, text=True, encoding="utf-8", check=False,
        )
    finally:
        os.unlink(cases_path)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)
    return {item["id"]: _without_none(item["response"]) for item in json.loads(proc.stdout)}


def main() -> int:
    portable, pwa = _portable(), _pwa()
    if portable != pwa:
        print(json.dumps({"portable": portable, "pwa": pwa}, ensure_ascii=False, indent=2))
        return 1
    print("workbench candidate parity ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
