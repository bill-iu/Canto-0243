"""詞條 lookup 缺庫時記憶體拼接（唔寫庫）。

CI 只 bootstrap `data/rime/fixtures/char_sample.csv`；查詢字面必須可由該 fixture 音節拼接。
"""

from __future__ import annotations

import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.lexicon.port import default_lexicon_port
from app.domain.relations.compound_connect import compose_transient_words
from app.models.word import Word
from app.services.word_lookup_executor import WordLookupExecutor

# 各字 ∈ char_sample.csv；整串唔喺靜態詞庫 → SYLLABLE_COMPOSE
_CI_COMPOSE_Q = "香雪就死"


class LookupTransientComposeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        default_lexicon_port().ensure_loaded()

    def setUp(self) -> None:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)
        self.db = self.Session()
        # 空庫：證明結果來自 admission 合成，唔係 DB 命中

    def tearDown(self) -> None:
        self.db.close()

    def test_compose_transient_no_db_write(self) -> None:
        q = _CI_COMPOSE_Q
        self.assertIsNone(self.db.query(Word).filter(Word.char == q).first())
        rows = compose_transient_words(q)
        self.assertTrue(rows, "expected syllable-compose transient rows")
        self.assertIsNone(self.db.query(Word).filter(Word.char == q).first())

    def test_pure_canto_lookup_layout_without_persist(self) -> None:
        q = _CI_COMPOSE_Q
        ex = WordLookupExecutor(self.db)
        items = ex.pure_canto(q, None, "m1", limit=50, offset=0)
        self.assertTrue(items, "lookup must not be empty for composable literal")
        self.assertTrue(any(i.get("char") == q or i.get("query_text") == q for i in items))
        self.assertIsNone(
            self.db.query(Word).filter(Word.char == q).first(),
            "lookup must not INSERT composed rows",
        )


if __name__ == "__main__":
    unittest.main()
