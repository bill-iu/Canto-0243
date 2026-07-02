"""recompute_phoneme_json 維護腳本 — y- 韻核後 stored finals 重算。"""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.recompute_phoneme_json import needs_phoneme_recompute, recompute_db, recompute_phoneme_json


class RecomputePhonemeJsonTests(unittest.TestCase):
    def test_detects_stale_zyu_final(self):
        self.assertTrue(needs_phoneme_recompute("zyu6", '["zy"]', '["u"]', "[6]"))
        initials, finals, tones = recompute_phoneme_json("zyu6")
        self.assertEqual(initials, '["z"]')
        self.assertEqual(finals, '["yu"]')
        self.assertFalse(needs_phoneme_recompute("zyu6", initials, finals, tones))

    def test_recompute_in_memory_db(self):
        import gc
        import shutil
        import sqlite3
        import tempfile
        from pathlib import Path

        tmp = tempfile.mkdtemp()
        try:
            db_path = Path(tmp) / "test.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, jyutping TEXT, "
                "initials TEXT, finals TEXT, tones TEXT)"
            )
            conn.execute(
                "INSERT INTO words (char, jyutping, initials, finals, tones) VALUES (?, ?, ?, ?, ?)",
                ("住", "zyu6", '["zy"]', '["u"]', "[6]"),
            )
            conn.commit()
            conn.close()

            report = recompute_db(db_path, dry_run=False)
            self.assertEqual(report["stale"], 1)
            self.assertEqual(report["updated"], 1)

            with sqlite3.connect(db_path) as verify:
                row = verify.execute(
                    "SELECT initials, finals FROM words WHERE char='住'"
                ).fetchone()
            self.assertEqual(row, ('["z"]', '["yu"]'))
        finally:
            gc.collect()
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
