import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


class BootstrapDataTests(unittest.TestCase):
    def test_dry_run_lists_all_fetch_steps(self):
        result = subprocess.run(
            [sys.executable, "scripts/bootstrap_data.py", "--dry-run"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)
        out = result.stdout
        self.assertIn("fetch_rime_data.py", out)
        self.assertIn("fetch_antisem_data.py", out)
        self.assertIn("fetch_guotong_thesaurus.py", out)
        self.assertIn("fetch_words_hk_wordslist.py", out)
        self.assertIn("fetch_cilin_data.py", out)

    def test_license_file_exists(self):
        text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("CANTO-0243 LICENCE", text)
        self.assertIn("IU Ching Ue Bill", text)


if __name__ == "__main__":
    unittest.main()
