"""startup lou_dou patch 接縫。"""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.startup.offline_preload import run_lou_dou_reading_patch


class LouDouStartupPatchTests(unittest.TestCase):
    def test_run_patch_updates_sqlite(self):
        import gc
        import shutil
        import sqlite3
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        tmp = tempfile.mkdtemp()
        try:
            db_path = Path(tmp) / "test.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, code TEXT, "
                "jyutping TEXT, initials TEXT, finals TEXT, tones TEXT, length INTEGER)"
            )
            conn.execute(
                "INSERT INTO words (char, code, jyutping, initials, finals, tones, length) "
                "VALUES ('窮困潦倒', '0499', 'kung4 kwan3 liu2 dou2', '[]', '[]', '[]', 4)"
            )
            conn.commit()
            conn.close()

            with patch("app.startup.offline_preload._local_sqlite_startup_enabled", return_value=True):
                with patch("app.db.connection.DATABASE_URL", f"sqlite:///{db_path}"):
                    with patch("app.db.connection.IS_POSTGRES", False):
                        run_lou_dou_reading_patch("local")

            with sqlite3.connect(db_path) as verify:
                row = verify.execute(
                    "SELECT code, jyutping FROM words WHERE char='窮困潦倒'"
                ).fetchone()
            self.assertEqual(row[0], "0449")
            self.assertEqual(row[1], "kung4 kwan3 lou5 dou2")
        finally:
            gc.collect()
            shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
