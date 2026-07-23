from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ESBUILD = ROOT / "client" / "node_modules" / "esbuild" / "bin" / "esbuild"


class WorkbenchParitySmokeTests(unittest.TestCase):
    def run_ts_self_check(self, script: str, bundle_name: str) -> None:
        if not ESBUILD.is_file():
            self.skipTest("client esbuild missing (npm ci runs later in CI; run locally after npm ci)")
        bundle = ROOT / "client" / ".tmp" / bundle_name
        bundle.parent.mkdir(parents=True, exist_ok=True)
        build = subprocess.run(
            [
                os.environ.get("NODE", "node"),
                str(ESBUILD),
                f"scripts/{script}",
                "--bundle",
                "--platform=node",
                "--format=esm",
                "--packages=external",
                f"--outfile={bundle}",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            cwd=str(ROOT / "client"),
        )
        self.assertEqual(build.returncode, 0, (build.stdout or "") + (build.stderr or ""))
        result = subprocess.run(
            [os.environ.get("NODE", "node"), str(bundle)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            cwd=str(ROOT / "client"),
        )
        self.assertEqual(result.returncode, 0, (result.stdout or "") + (result.stderr or ""))

    def test_portable_and_pwa_candidate_contracts_match(self) -> None:
        if not ESBUILD.is_file():
            self.skipTest("client esbuild missing (npm ci runs later in CI; run locally after npm ci)")
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(
            [sys.executable, "scripts/workbench_candidate_parity.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
            cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, (result.stdout or "") + (result.stderr or ""))

    def test_302_and_constraint_results_keep_canonical_ranking(self) -> None:
        self.run_ts_self_check(
            "digit-code-ranking-self-check.ts",
            "digit-code-ranking-self-check.mjs",
        )

    def test_pos_filter_preserves_canonical_relative_order(self) -> None:
        self.run_ts_self_check(
            "workbench-candidate-session-self-check.ts",
            "workbench-candidate-session-self-check.mjs",
        )


if __name__ == "__main__":
    unittest.main()
