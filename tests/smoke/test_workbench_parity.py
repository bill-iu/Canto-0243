from __future__ import annotations

import subprocess
import sys
import os
import unittest


class WorkbenchParitySmokeTests(unittest.TestCase):
    def test_portable_and_pwa_candidate_contracts_match(self) -> None:
        env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(
            [sys.executable, "scripts/workbench_candidate_parity.py"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, (result.stdout or "") + (result.stderr or ""))


if __name__ == "__main__":
    unittest.main()
