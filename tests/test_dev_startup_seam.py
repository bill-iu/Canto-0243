"""接縫測試：本機啟動 — local_launch 統一編排。"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_PATH = REPO_ROOT / "scripts" / "local_launch.py"
START_SH = REPO_ROOT / "start.sh"
START_BAT = REPO_ROOT / "portable" / "START.bat"
START_SH_PORTABLE = REPO_ROOT / "portable" / "START.sh"
MACOS_LAUNCHER = REPO_ROOT / "portable" / "macos" / "launcher"
MAIN_PATH = REPO_ROOT / "main.py"


class TestLocalLaunchSeam(unittest.TestCase):
    def test_local_launch_waits_html_before_browser(self):
        source = LAUNCH_PATH.read_text(encoding="utf-8")
        open_idx = source.find("webbrowser.open")
        self.assertGreater(open_idx, 0)
        before_open = source[:open_idx]
        self.assertIn("frontend/index.html", before_open)
        self.assertIn("wait_for_url.py", before_open)
        gate_idx = source.find("--gate")
        self.assertGreater(gate_idx, open_idx)

    def test_local_launch_prints_starting_first(self):
        source = LAUNCH_PATH.read_text(encoding="utf-8")
        starting_idx = source.find('msgs["starting"]')
        free_idx = source.find("free_port.py")
        self.assertGreater(starting_idx, 0)
        self.assertGreater(free_idx, starting_idx)

    def test_start_sh_delegates_to_local_launch(self):
        source = START_SH.read_text(encoding="utf-8")
        self.assertIn("local_launch.py", source)
        self.assertNotIn("wait_for_url.py", source)

    def test_portable_entries_delegate_to_local_launch(self):
        for path in (START_BAT, START_SH_PORTABLE, MACOS_LAUNCHER):
            with self.subTest(path=path.name):
                self.assertIn("local_launch.py", path.read_text(encoding="utf-8"))

    def test_main_does_not_run_main_block_startup(self):
        source = MAIN_PATH.read_text(encoding="utf-8")
        self.assertNotIn("run_main_block_startup", source)


if __name__ == "__main__":
    unittest.main()
