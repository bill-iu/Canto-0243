"""ADR-0037 / J2: phoneme compact encode/decode (S1+K1)."""
from __future__ import annotations

import unittest

from app.domain.lexicon.phoneme_codec import (
    FINALS_VOCAB,
    INITIALS_VOCAB,
    decode_phoneme_field,
    encode_phoneme_list,
    phoneme_vocab_fingerprint,
)
from app.utils.jyutping_codec import rhyme_finals_from_jyutping, split_jyutping


class PhonemeCodecTests(unittest.TestCase):
    def test_roundtrip_finals(self):
        parts = ["ung", "an", "ou", "ou"]
        enc = encode_phoneme_list(parts, "final")
        self.assertEqual(enc, "56.14.51.51")
        self.assertEqual(decode_phoneme_field(enc, "final"), parts)

    def test_roundtrip_initials(self):
        parts = ["h", "k", "l", "d"]
        enc = encode_phoneme_list(parts, "initial")
        self.assertEqual(decode_phoneme_field(enc, "initial"), parts)

    def test_empty_list(self):
        self.assertEqual(encode_phoneme_list([], "final"), "")
        self.assertEqual(decode_phoneme_field("", "final"), [])
        self.assertEqual(decode_phoneme_field(None, "final"), [])

    def test_empty_token_id_zero(self):
        enc = encode_phoneme_list([""], "final")
        self.assertEqual(enc, "0")
        self.assertEqual(decode_phoneme_field(enc, "final"), [""])

    def test_reject_legacy_json(self):
        self.assertEqual(decode_phoneme_field('["an","iu"]', "final"), [])

    def test_unknown_token_raises(self):
        with self.assertRaises(ValueError):
            encode_phoneme_list(["not_a_final"], "final")

    def test_vocab_zero_is_empty(self):
        self.assertEqual(FINALS_VOCAB[0], "")
        self.assertEqual(INITIALS_VOCAB[0], "")

    def test_fingerprint_stable(self):
        a = phoneme_vocab_fingerprint()
        b = phoneme_vocab_fingerprint()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)

    def test_split_jyutping_compact(self):
        ini, fin, _tones = split_jyutping("zyu6")
        self.assertEqual(decode_phoneme_field(fin, "final"), ["yu"])
        self.assertEqual(decode_phoneme_field(ini, "initial"), ["z"])
        self.assertEqual(rhyme_finals_from_jyutping("zyu6"), ["yu"])


if __name__ == "__main__":
    unittest.main()
