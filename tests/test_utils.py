import unittest
import tempfile
from pathlib import Path

from app.thesaurus.static_index import (
    get_antonyms,
    get_cilin_synonyms,
    get_synonyms,
    load_antonym_dict,
    load_cilin_index,
    load_thesaurus_dicts,
)
from app.utils.jyutping_codec import get_0243_code, get_code_variants, split_jyutping


class UtilsTests(unittest.TestCase):
    def test_get_0243_code(self):
        self.assertEqual(get_0243_code("si1"), "3")
        self.assertEqual(get_0243_code("gaa3"), "4")

    def test_split_jyutping(self):
        initials, finals, tones = split_jyutping("si1 jyun2")
        self.assertEqual(initials, '["s", "j"]')
        self.assertEqual(finals, '["i", "yun"]')
        self.assertEqual(tones, '[1, 2]')

    def test_split_jyutping_jy_nucleus(self):
        initials, finals, _ = split_jyutping("jyut6 jyu5")
        self.assertEqual(initials, '["j", "j"]')
        self.assertEqual(finals, '["yut", "yu"]')
        initials2, finals2, _ = split_jyutping("but6 fu6")
        self.assertEqual(finals2, '["ut", "u"]')
        self.assertNotEqual(finals, finals2)

        initials3, finals3, _ = split_jyutping("jyun4")
        self.assertEqual(initials3, '["j"]')
        self.assertEqual(finals3, '["yun"]')
        _, finals4, _ = split_jyutping("wun6")
        self.assertEqual(finals4, '["un"]')
        self.assertNotEqual(finals3, finals4)

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

    def test_bundled_cilin_file_traditional_and_loadable(self):
        path = Path(__file__).resolve().parents[1] / "data" / "cilin" / "new_cilin.txt"
        if not path.exists() or path.stat().st_size < 50_000:
            self.skipTest("data/cilin/new_cilin.txt not populated; run scripts/fetch/fetch_cilin_data.py")
        content = path.read_text(encoding="utf-8")
        self.assertIn("舊曆", content)
        self.assertIn("快樂", content)
        self.assertNotIn("旧历", content)

        load_cilin_index(str(path))
        syns = get_cilin_synonyms("快樂")
        self.assertGreater(len(syns), 5)
        self.assertIn("開心", syns)


if __name__ == "__main__":
    unittest.main()
