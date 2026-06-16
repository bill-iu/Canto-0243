"""詞條 lookup 版面 — section order and cache sync boundary."""

import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.domain.lexicon.lookup_layout import build_lookup_layout
from app.models.word import Word
from app.services.query_dispatch import search_words


class LookupLayoutTests(unittest.TestCase):
    def _session(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        return sessionmaker(bind=engine, autoflush=False, autocommit=False)()

    def test_code_headers_precede_query_word(self):
        with self._session() as session:
            session.add(Word(char="字", code="23", jyutping="zi6", length=1))
            session.commit()
            layout = build_lookup_layout("字", session.query(Word).all(), session)

        self.assertEqual(layout[0]["result_type"], "code")
        self.assertEqual(layout[0]["display_text"], "23")
        self.assertEqual(layout[1]["result_type"], "jyutping")
        word_chars = [r["char"] for r in layout if r["result_type"] == "word"]
        self.assertEqual(word_chars[0], "字")

    def test_same_rhyme_shared_char_before_different_rhyme(self):
        with self._session() as session:
            session.add_all([
                Word(
                    char="做到",
                    code="24",
                    jyutping="zou6 dou3",
                    finals='["ou", "ou"]',
                    initials='["z", "d"]',
                    length=2,
                ),
                Word(
                    char="做數",
                    code="24",
                    jyutping="zou6 sou3",
                    finals='["ou", "ou"]',
                    initials='["z", "s"]',
                    length=2,
                ),
                Word(
                    char="路數",
                    code="24",
                    jyutping="lou6 sou3",
                    finals='["ou", "ou"]',
                    initials='["l", "s"]',
                    length=2,
                ),
                Word(
                    char="丈母",
                    code="24",
                    jyutping="zoeng6 mou5",
                    finals='["oeng", "ou"]',
                    initials='["z", "m"]',
                    length=2,
                ),
            ])
            session.commit()
            layout = build_lookup_layout(
                "做到",
                session.query(Word).filter(Word.char == "做到").all(),
                session,
            )

        words = [r["char"] for r in layout if r["result_type"] == "word"]
        self.assertEqual(words[0], "做到")
        self.assertEqual(words[1], "做數")
        if "路數" in words and "丈母" in words:
            self.assertLess(words.index("路數"), words.index("丈母"))

    def test_layout_module_does_not_sync_cache(self):
        with self._session() as session:
            session.add(
                Word(
                    char="到",
                    code="3",
                    jyutping="dou3",
                    finals='["ou"]',
                    initials='["d"]',
                    length=1,
                )
            )
            session.add(
                Word(
                    char="做到",
                    code="24",
                    jyutping="zou6 dou3",
                    finals='["ou", "ou"]',
                    initials='["z", "d"]',
                    length=2,
                )
            )
            session.commit()
            exact = session.query(Word).filter(Word.char == "做到").all()
            with patch("app.services.word_ensure_service.sync_word_to_cache") as sync:
                build_lookup_layout("做到", exact, session)
                sync.assert_not_called()

    def test_search_words_integration_matches_layout_contract(self):
        with self._session() as session:
            session.add(
                Word(
                    char="做到",
                    code="24",
                    jyutping="zou6 dou3",
                    finals='["ou", "ou"]',
                    initials='["z", "d"]',
                    length=2,
                )
            )
            session.commit()
            results = search_words(q="做到", db=session, limit=20, offset=0)
            word_rows = [r for r in results if r.get("result_type") == "word"]
            self.assertEqual(word_rows[0]["char"], "做到")


if __name__ == "__main__":
    unittest.main()