"""reading_resolve — 音節槽修復解析。"""

import unittest
from unittest.mock import patch

from app.lexicon.rime_char_index import load_rime_char_csv, reset_rime_char_for_tests
from app.utils.reading_resolve import cjk_literal, phoneme_slot_count, resolve_repair_reading

_FIXTURE = __import__("pathlib").Path(__file__).resolve().parent.parent / "data" / "rime" / "fixtures" / "char_sample.csv"


class ReadingResolveTests(unittest.TestCase):
    def setUp(self):
        reset_rime_char_for_tests()
        load_rime_char_csv(_FIXTURE)

    def tearDown(self):
        reset_rime_char_for_tests()

    def test_cjk_literal_strips_punctuation(self):
        self.assertEqual(cjk_literal("一人計短，二人計長"), "一人計短二人計長")

    def test_phoneme_slot_count(self):
        self.assertEqual(phoneme_slot_count("seoi4 tau4 song3 hei3"), 4)

    def test_pycantonese_repairs_missing_rime_char(self):
        with patch("app.domain.lexicon.admission.resolve_admission") as mock_adm:
            from app.domain.lexicon.admission import AdmissionResult, AdmissionSource

            mock_adm.return_value = AdmissionResult("垂頭喪氣", AdmissionSource.NONE, [])
            ent = resolve_repair_reading("垂頭喪氣")
        self.assertIsNotNone(ent)
        assert ent is not None
        self.assertEqual(phoneme_slot_count(ent.jyutping), 4)
        self.assertEqual(cjk_literal(ent.char), "垂頭喪氣")


if __name__ == "__main__":
    unittest.main()
