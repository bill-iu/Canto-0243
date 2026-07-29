"""ADR-0078 韻母比對檔 expand tables."""
from __future__ import annotations

import unittest

from app.domain.lexicon.rhyme_match_profile import (
    expand_one_final,
    finals_compatible,
    normalize_rhyme_profile,
)


class RhymeMatchProfileTests(unittest.TestCase):
    def test_exact_is_identity(self) -> None:
        self.assertEqual(expand_one_final("ong", "exact"), {"ong"})
        self.assertTrue(finals_compatible("ong", "ong", "exact"))
        self.assertFalse(finals_compatible("ong", "on", "exact"))

    def test_tong_chicken_group(self) -> None:
        # 雞啼：i / ei / yu / eoi / ai
        self.assertTrue(finals_compatible("i", "ei", "tong"))
        self.assertTrue(finals_compatible("i", "ai", "tong"))
        self.assertFalse(finals_compatible("i", "ong", "tong"))

    def test_nucleus_aa_bucket(self) -> None:
        self.assertTrue(finals_compatible("aa", "aap", "nucleus"))
        self.assertTrue(finals_compatible("aam", "aang", "nucleus"))
        self.assertFalse(finals_compatible("aa", "ai", "nucleus"))

    def test_coda_p_group(self) -> None:
        self.assertTrue(finals_compatible("ip", "ap", "coda"))
        self.assertTrue(finals_compatible("aap", "op", "coda"))
        self.assertFalse(finals_compatible("ip", "it", "coda"))

    def test_unknown_falls_back(self) -> None:
        self.assertEqual(expand_one_final("xyz", "tong"), {"xyz"})

    def test_normalize(self) -> None:
        self.assertEqual(normalize_rhyme_profile(None), "exact")
        self.assertEqual(normalize_rhyme_profile("tong"), "tong")
        self.assertEqual(normalize_rhyme_profile("nope"), "exact")


if __name__ == "__main__":
    unittest.main()
