"""潦倒成語讀音修正（潦 → lou5）。"""

import unittest

from scripts.patch_lou_dou_readings import corrected_lou_dou_jyutping, patch_lyrics_db


class LouDouReadingPatchTests(unittest.TestCase):
    def test_corrects_liu_tail(self):
        self.assertEqual(
            corrected_lou_dou_jyutping("kung4 kwan3 liu2 dou2"),
            "kung4 kwan3 lou5 dou2",
        )
        self.assertEqual(
            corrected_lou_dou_jyutping("kung4 sau4 liu5 dou2"),
            "kung4 sau4 lou5 dou2",
        )

    def test_skips_already_lou5(self):
        self.assertIsNone(corrected_lou_dou_jyutping("pan4 kung4 lou5 dou2"))
        self.assertIsNone(corrected_lou_dou_jyutping("lou5 dou2"))

    def test_patch_in_memory_db(self):
        import sqlite3
        import tempfile
        from pathlib import Path

        from app.utils.jyutping_codec import split_jyutping

        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, code TEXT, "
                "jyutping TEXT, initials TEXT, finals TEXT, tones TEXT, length INTEGER)"
            )
            jp = "kung4 kwan3 liu2 dou2"
            initials, finals, tones = split_jyutping(jp)
            conn.execute(
                "INSERT INTO words (char, code, jyutping, initials, finals, tones, length) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("窮困潦倒", "0499", jp, initials, finals, tones, 4),
            )
            conn.commit()
            conn.close()

            self.assertEqual(patch_lyrics_db(db_path), 1)
            row = sqlite3.connect(db_path).execute(
                "SELECT jyutping, code FROM words WHERE char='窮困潦倒'"
            ).fetchone()
            self.assertEqual(row[0], "kung4 kwan3 lou5 dou2")
            self.assertEqual(row[1], "0449")


if __name__ == "__main__":
    unittest.main()
