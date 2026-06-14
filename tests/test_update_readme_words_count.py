import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.update_readme_words_count import (
    EN_BEGIN,
    EN_END,
    EN_HEADING,
    ZH_BEGIN,
    ZH_END,
    ZH_HEADING,
    count_words,
    update_readme_files,
)


class UpdateReadmeWordsCountTests(unittest.TestCase):
    def test_count_words_from_sqlite(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                "CREATE TABLE words (id INTEGER PRIMARY KEY, char TEXT, code TEXT, jyutping TEXT)"
            )
            conn.executemany(
                "INSERT INTO words (char, code, jyutping) VALUES (?, ?, ?)",
                [("你", "5", "nei5"), ("好", "2", "hou2")],
            )
            conn.commit()
            conn.close()
            self.assertEqual(count_words(db_path), 2)

    def test_update_readme_files_replaces_marker_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readme_zh = root / "README.md"
            readme_en = root / "README.en.md"
            readme_zh.write_text(
                f"{ZH_HEADING}\n\n{ZH_BEGIN}\n舊數字\n{ZH_END}\n",
                encoding="utf-8",
            )
            readme_en.write_text(
                f"{EN_HEADING}\n\n{EN_BEGIN}\nold count\n{EN_END}\n",
                encoding="utf-8",
            )

            updated = update_readme_files(
                193_277,
                readme_zh=readme_zh,
                readme_en=readme_en,
            )

            self.assertEqual(updated, [readme_zh, readme_en])
            self.assertIn("193,277", readme_zh.read_text(encoding="utf-8"))
            self.assertIn("193,277", readme_en.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
