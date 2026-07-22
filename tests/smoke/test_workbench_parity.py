from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ESBUILD = ROOT / "client" / "node_modules" / "esbuild" / "bin" / "esbuild"


class WorkbenchParitySmokeTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
