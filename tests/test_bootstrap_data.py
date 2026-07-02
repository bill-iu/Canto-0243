import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _bootstrap_main():
    path = REPO_ROOT / "scripts" / "bootstrap_data.py"
    spec = importlib.util.spec_from_file_location("bootstrap_data", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["bootstrap_data"] = mod
    spec.loader.exec_module(mod)
    return mod.main


class BootstrapDataTests(unittest.TestCase):
    def test_dry_run_lists_all_fetch_steps(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = _bootstrap_main()(["--dry-run"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("fetch_rime_data.py", out)
        self.assertIn("fetch_guotong_thesaurus.py", out)
        self.assertIn("fetch_words_hk_wordslist.py", out)
        self.assertIn("fetch_cilin_data.py", out)

    def test_license_file_exists(self):
        text = (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("CANTO-0243 LICENCE", text)
        self.assertIn("IU Ching Ue Bill", text)


if __name__ == "__main__":
    unittest.main()
