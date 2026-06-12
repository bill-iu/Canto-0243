import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.lexicon.static_index import LexiconEntry, load_lexicon_from_folder, reset_lexicon_for_tests
from app.models.word import Word
from app.services.lexicon_port import Static0243Lexicon
from app.services.word_ensure_service import ensure_word_in_db
from app.utils.word_cache import reset_word_cache_for_tests


class FakeLexiconPort:
    def __init__(self, entries_by_char):
        self._entries = entries_by_char

    def ensure_loaded(self) -> None:
        pass

    def get_entries(self, char: str):
        return list(self._entries.get(char, []))


class LexiconEnsureTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def tearDown(self):
        reset_lexicon_for_tests()
        reset_word_cache_for_tests()

    def test_multi_char_lexicon_hit_injects_all_codes(self):
        port = FakeLexiconPort(
            {
                "香港": [
                    LexiconEntry(char="香港", jyutping="hoeng1 gong2", code="12"),
                    LexiconEntry(char="香港", jyutping="hoeng1 gong2", code="949"),
                ],
            }
        )
        with self.Session() as db:
            rows = ensure_word_in_db(db, "香港", lexicon=port)
            self.assertEqual(len(rows), 2)
            codes = sorted(r.code for r in rows)
            self.assertEqual(codes, ["12", "949"])

    def test_multi_char_lexicon_miss_does_not_inject(self):
        port = FakeLexiconPort({})
        with patch("app.services.word_ensure_service.pycantonese", create=True) as mock_pc:
            with self.Session() as db:
                rows = ensure_word_in_db(db, "走你好", lexicon=port)
                self.assertEqual(rows, [])
                mock_pc.characters_to_jyutping.assert_not_called()

    def test_single_char_still_uses_pycantonese_transition(self):
        port = FakeLexiconPort({})
        fake_jyut = [("你", "nei5")]
        with patch("pycantonese.characters_to_jyutping", return_value=fake_jyut):
            with self.Session() as db:
                rows = ensure_word_in_db(db, "你", lexicon=port)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].char, "你")
                self.assertEqual(rows[0].jyutping, "nei5")

    def test_existing_char_skips_injection(self):
        port = FakeLexiconPort({"香港": [LexiconEntry("香港", "hoeng1 gong2", "12")]})
        with self.Session() as db:
            db.add(Word(char="香港", code="12", jyutping="hoeng1 gong2", length=2))
            db.commit()
            rows = ensure_word_in_db(db, "香港", lexicon=port)
            self.assertEqual(len(rows), 1)
            self.assertEqual(db.query(Word).filter(Word.char == "香港").count(), 1)


class Static0243LexiconTests(unittest.TestCase):
    def tearDown(self):
        reset_lexicon_for_tests()
        reset_word_cache_for_tests()

    def test_load_from_temp_json_folder(self):
        import json
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.json"
            path.write_text(
                json.dumps(
                    [
                        {"char": "開心", "jyutping": "hoi1 sam1", "code": "23"},
                        {"char": "開心", "jyutping": "hoi1 sam1", "code": "949"},
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            count = load_lexicon_from_folder(tmp)
            self.assertEqual(count, 2)
            lex = Static0243Lexicon(auto_load=False, clean_dir=tmp)
            entries = lex.get_entries("開心")
            self.assertEqual(len(entries), 2)
            self.assertEqual({e.code for e in entries}, {"23", "949"})


if __name__ == "__main__":
    unittest.main()
