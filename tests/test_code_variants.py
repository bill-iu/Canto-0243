"""0243／02493／394052 模式 code 變體 — ADR-0028 + ADR-0031。"""
from __future__ import annotations

import unittest

from app.utils.jyutping_codec import get_code_variants, normalize_02493_code


class CodeVariantsPerDigitLooseTests(unittest.TestCase):
    def test_m1_39_includes_cross_digit_93(self):
        variants = get_code_variants("39", "m1")
        self.assertIn("93", variants)

    def test_m1_23_includes_cross_digit_69(self):
        variants = get_code_variants("23", "m1")
        self.assertIn("69", variants)

    def test_m1_021_includes_all_per_digit_combos(self):
        self.assertEqual(normalize_02493_code("021"), "023")
        variants = set(get_code_variants("021", "m1"))
        self.assertEqual(variants, {"023", "029", "063", "069"})

    def test_m2_partial_loose_45_only(self):
        self.assertEqual(get_code_variants("39", "m2"), ["39"])
        self.assertEqual(get_code_variants("021", "m2"), ["023"])
        self.assertEqual(set(get_code_variants("4", "m2")), {"4", "5"})

    def test_m3_strict_single_variant(self):
        self.assertEqual(get_code_variants("39", "m3"), ["39"])
        self.assertEqual(get_code_variants("45", "m3"), ["45"])
        self.assertEqual(get_code_variants("021", "m3"), ["023"])

    def test_m1_single_digit_flip(self):
        self.assertEqual(get_code_variants("3", "m1"), ["3", "9"])


if __name__ == "__main__":
    unittest.main()