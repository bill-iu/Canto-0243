import unittest
import tempfile
from pathlib import Path

from utils import (
    get_0243_code,
    get_code_variants,
    split_jyutping,
    get_synonyms,
    get_antonyms,
    load_cilin_index,
    load_antonym_dict,
    load_thesaurus_dicts,
)


class UtilsTests(unittest.TestCase):
    def test_get_0243_code(self):
        self.assertEqual(get_0243_code("si1"), "3")
        self.assertEqual(get_0243_code("gaa3"), "4")

    def test_split_jyutping(self):
        initials, finals, tones = split_jyutping("si1 jyun2")
        self.assertEqual(initials, '["s", "jy"]')
        self.assertEqual(finals, '["i", "un"]')
        self.assertEqual(tones, '[1, 2]')

    def test_get_code_variants(self):
        self.assertEqual(get_code_variants("23", "m2"), ["23"])
        self.assertIn("44", get_code_variants("54", "m1"))

    def test_static_thesaurus_parsers_are_bidirectional(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cilin = root / "cilin.txt"
            antisem = root / "antisem.txt"
            syn = root / "syn.txt"
            ant = root / "ant.txt"

            cilin.write_text("Aa01A01 開心 快樂 高興\n", encoding="utf-8")
            antisem.write_text("開心:難過;悲傷\n", encoding="utf-8")
            syn.write_text("Bb01= 愉快 欣喜\n", encoding="utf-8")
            ant.write_text("前——後\n", encoding="utf-8")

            load_cilin_index(str(cilin))
            load_antonym_dict(str(antisem))
            load_thesaurus_dicts(str(syn), str(ant))

            self.assertIn("快樂", get_synonyms("開心"))
            self.assertIn("開心", get_synonyms("快樂"))
            self.assertIn("欣喜", get_synonyms("愉快"))
            self.assertIn("悲傷", get_antonyms("開心"))
            self.assertIn("開心", get_antonyms("悲傷"))
            self.assertIn("後", get_antonyms("前"))
            self.assertIn("前", get_antonyms("後"))


if __name__ == "__main__":
    unittest.main()
