import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.lexicon.static_index import LexiconEntry, reset_lexicon_for_tests
from app.models.word import Word
from app.services.word_ensure_service import ensure_word_in_db
from app.utils.jyutping_codec import get_0243_code
from app.utils.word_cache import reset_word_cache_for_tests

FIXTURE_CSV = Path(__file__).resolve().parent.parent / "data" / "rime" / "fixtures" / "char_sample.csv"


class RimeCharLexiconTests(unittest.TestCase):
    def tearDown(self):
        from app.lexicon.rime_char_index import reset_rime_char_for_tests

        reset_rime_char_for_tests()
        reset_lexicon_for_tests()
        reset_word_cache_for_tests()

    def test_rime_char_csv_default_pron_rank_yields_jyutping_and_code(self):
        """Single-char lexicon: only pron_rank=預設 rows become injectable entries."""
        from app.lexicon.rime_char_index import get_rime_char_entries, load_rime_char_csv

        count = load_rime_char_csv(FIXTURE_CSV)
        self.assertEqual(count, 8)

        nei = get_rime_char_entries("你")
        self.assertEqual(len(nei), 1)
        self.assertEqual(nei[0].jyutping, "nei5")
        self.assertEqual(nei[0].code, get_0243_code("nei5"))

        hou = get_rime_char_entries("好")
        self.assertEqual(len(hou), 1)
        self.assertEqual(hou[0].jyutping, "hou2")
        self.assertNotIn("hou3", [e.jyutping for e in hou])


class FakeLexiconPort:
    def __init__(self, entries_by_char):
        self._entries = entries_by_char

    def ensure_loaded(self) -> None:
        pass

    def get_entries(self, char: str):
        return list(self._entries.get(char, []))


class SingleCharEnsureRimeTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def tearDown(self):
        reset_lexicon_for_tests()
        reset_word_cache_for_tests()

    def test_single_char_ensure_uses_lexicon_not_pycantonese(self):
        port = FakeLexiconPort({"你": [LexiconEntry(char="你", jyutping="nei5", code="4")]})
        with patch("pycantonese.characters_to_jyutping") as mock_pc:
            with self.Session() as db:
                rows = ensure_word_in_db(db, "你", lexicon=port)
                mock_pc.assert_not_called()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].jyutping, "nei5")


class CompositeLexiconTests(unittest.TestCase):
    def tearDown(self):
        from app.lexicon.rime_char_index import reset_rime_char_for_tests

        reset_rime_char_for_tests()
        reset_lexicon_for_tests()
        reset_word_cache_for_tests()

    def test_composite_lexicon_routes_single_char_to_rime_and_multi_to_static(self):
        import json
        import tempfile
        from pathlib import Path

        from app.lexicon.rime_char_index import load_rime_char_csv
        from app.lexicon.static_index import load_lexicon_from_folder
        from app.services.lexicon_port import CompositeLexicon

        with tempfile.TemporaryDirectory() as tmp:
            clean = Path(tmp) / "clean"
            clean.mkdir()
            (clean / "words.json").write_text(
                json.dumps([{"char": "開心", "jyutping": "hoi1 sam1", "code": "23"}], ensure_ascii=False),
                encoding="utf-8",
            )
            load_rime_char_csv(FIXTURE_CSV)
            load_lexicon_from_folder(clean)

            lex = CompositeLexicon(auto_load=False, clean_dir=clean, rime_char_csv=FIXTURE_CSV)
            nei = lex.get_entries("你")
            self.assertEqual(len(nei), 1)
            self.assertEqual(nei[0].jyutping, "nei5")

            word = lex.get_entries("開心")
            self.assertEqual(len(word), 1)
            self.assertEqual(word[0].code, "23")


if __name__ == "__main__":
    unittest.main()
