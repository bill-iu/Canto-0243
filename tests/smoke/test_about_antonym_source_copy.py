"""About 資料來源：反義詞庫條目唔顯示檔名（簡潔格式）。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ABOUT_I18N = ROOT / "frontend" / "about-i18n.mjs"
INDEX_HTML = ROOT / "frontend" / "index.html"
FORBIDDEN = (
    "dict_synonym.txt",
    "dict_antonym.txt",
    "project_antonyms.tsv",
)


class AboutAntonymSourceCopyTests(unittest.TestCase):
    def test_about_i18n_omits_lexicon_filenames(self) -> None:
        text = ABOUT_I18N.read_text(encoding="utf-8")
        for name in FORBIDDEN:
            self.assertNotIn(name, text, f"about-i18n must not cite {name}")
        self.assertIn("自建反義詞庫", text)
        self.assertIn("Project antonym lexicon", text)

    def test_portable_about_omits_lexicon_filenames(self) -> None:
        text = INDEX_HTML.read_text(encoding="utf-8")
        for name in FORBIDDEN:
            self.assertNotIn(name, text, f"index.html About must not cite {name}")
        self.assertIn("自建反義詞庫", text)


if __name__ == "__main__":
    unittest.main()
