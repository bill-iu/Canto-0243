import unittest

from utils import get_0243_code, get_code_variants, split_jyutping


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


if __name__ == "__main__":
    unittest.main()
