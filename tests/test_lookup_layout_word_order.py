"""詞條 lookup 詞列順序與 PWA buildLookupLayout 對齊（Scenario C）。"""
from __future__ import annotations

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.lexicon.lookup_layout import build_lookup_layout
from app.lexicon.essay_index import ensure_essay_loaded
from app.models.word import Word

DEV_DB = "client/public/lyrics.db"

PWA_TOP10_事業 = [
    "事業",
    "肄業",
    "事實",
    "事後",
    "大事",
    "事物",
    "話事",
    "學業",
    "事務",
    "藥業",
]


class LookupLayoutWordOrderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        ensure_essay_loaded()
        engine = create_engine(f"sqlite:///{DEV_DB}")
        cls._session = sessionmaker(bind=engine)()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._session.close()

    def test_word_order_matches_pwa_事業(self) -> None:
        exact = self._session.query(Word).filter(Word.char == "事業").all()
        layout = build_lookup_layout("事業", exact, self._session)
        words = [r["char"] for r in layout if r.get("result_type") == "word"]
        self.assertEqual(words[: len(PWA_TOP10_事業)], PWA_TOP10_事業)

    def test_code_headers_before_words(self) -> None:
        exact = self._session.query(Word).filter(Word.char == "事業").all()
        layout = build_lookup_layout("事業", exact, self._session)
        types = [r.get("result_type") for r in layout]
        self.assertLess(types.index("code"), types.index("word"))
        self.assertLess(types.index("jyutping"), types.index("word"))


if __name__ == "__main__":
    unittest.main()
