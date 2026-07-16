"""About 資料來源：反義詞庫條目唔顯示檔名（簡潔格式）。"""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ABOUT_I18N = ROOT / "frontend" / "about-i18n.mjs"
ABOUT_VIEW = ROOT / "client" / "src" / "about-view.tsx"
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

    def test_client_about_uses_i18n_ssot(self) -> None:
        """Product About is client + about-i18n; frontend/index.html is only /app redirect."""
        view = ABOUT_VIEW.read_text(encoding="utf-8")
        self.assertIn("getAboutCopy", view)
        self.assertIn("about-i18n.mjs", view)
        for name in FORBIDDEN:
            self.assertNotIn(name, view, f"about-view must not cite {name}")


if __name__ == "__main__":
    unittest.main()
