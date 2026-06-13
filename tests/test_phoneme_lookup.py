import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.lexicon.static_index import LexiconEntry
from app.services.phoneme_lookup import final_options_for_char, initial_options_for_char
from app.utils.word_cache import reset_word_cache_for_tests, update_word_in_cache


class PhonemeLookupAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def tearDown(self):
        reset_word_cache_for_tests()

    def test_initial_options_from_admission_not_stale_cache(self):
        """收錄決策優先於快取（快取不作讀音權威）。"""
        update_word_in_cache("你", "9", "laa5", ["l"], ["aa"], 1)
        port_entries = [LexiconEntry(char="你", jyutping="nei5", code="4")]

        class Port:
            def ensure_loaded(self):
                pass

            def get_rime_char_entries(self, char: str):
                return port_entries if char == "你" else []

            def get_word_lexicon_entries(self, text: str):
                return []

        with patch("app.domain.lexicon.admission.default_lexicon_port", return_value=Port()):
            with self.Session() as db:
                options = initial_options_for_char("你", db)
        self.assertEqual(options, {"n"})

    def test_final_options_from_admission_without_db(self):
        port_entries = [LexiconEntry(char="香", jyutping="hoeng1", code="5")]

        class Port:
            def ensure_loaded(self):
                pass

            def get_rime_char_entries(self, char: str):
                return port_entries if char == "香" else []

            def get_word_lexicon_entries(self, text: str):
                return []

        with patch("app.domain.lexicon.admission.default_lexicon_port", return_value=Port()):
            with self.Session() as db:
                options = final_options_for_char("香", db)
        self.assertEqual(options, {"oeng"})


if __name__ == "__main__":
    unittest.main()
