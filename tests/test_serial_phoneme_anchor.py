"""ADR-0014：串列韻／聲錨 + 前綴通配等號。"""
from __future__ import annotations

import unittest

from app.services.query_parse import (
    EqualsQuery,
    PrefixWildcardEqualsQuery,
    SerialPhonemeAnchorQuery,
    SingleCharRhymeAnchorQuery,
    UnmatchedQuery,
    build_match_spec,
    normalize_and_parse,
    parse_query,
)
from app.services.word_query_parser import (
    PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT,
    PURE_HANZI_SERIAL_HINT,
    normalize_search_query,
)


def _parse(q: str):
    return parse_query(normalize_search_query(q))


class SerialRhymeParseTests(unittest.TestCase):
    def test_one_syllable_4_kwan(self):
        parsed = _parse("4困=")
        self.assertIsInstance(parsed, SerialPhonemeAnchorQuery)
        self.assertEqual(parsed.width, 1)
        self.assertEqual(parsed.constraint, "final")

    def test_two_syllable_04_kwan(self):
        parsed = _parse("04困=")
        self.assertIsInstance(parsed, SerialPhonemeAnchorQuery)
        self.assertEqual(parsed.width, 2)

    def test_four_syllable_example(self):
        parsed = _parse("04困=49倒=")
        self.assertIsInstance(parsed, SerialPhonemeAnchorQuery)
        self.assertEqual(parsed.width, 4)
        self.assertEqual(len(parsed.anchors), 2)

    def test_serial_with_leading_wildcard(self):
        parsed = _parse("?4困=4潦=9倒=")
        self.assertIsInstance(parsed, SerialPhonemeAnchorQuery)
        self.assertEqual(parsed.width, 4)


class SerialInitialParseTests(unittest.TestCase):
    def test_four_syllable_initial(self):
        parsed = _parse("04=困49=倒")
        self.assertIsInstance(parsed, SerialPhonemeAnchorQuery)
        self.assertEqual(parsed.constraint, "initial")
        self.assertEqual(parsed.width, 4)


class SerialVsCodeSandwichTests(unittest.TestCase):
    def test_code_sandwich_stays_equals(self):
        parsed = _parse("2=我3")
        self.assertIsInstance(parsed, EqualsQuery)


class PrefixWildcardEqualsTests(unittest.TestCase):
    def test_kwan_liu_dou(self):
        parsed = _parse("?困潦倒=")
        self.assertIsInstance(parsed, PrefixWildcardEqualsQuery)
        self.assertEqual(parsed.width, 4)

    def test_missing_equals_hint(self):
        parsed = _parse("?困潦倒")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertEqual(parsed.hint, PREFIX_WILDCARD_EQUALS_MISSING_EQ_HINT)


class PureHanziSerialHintTests(unittest.TestCase):
    def test_qiong_kun_liu_dao(self):
        parsed = _parse("窮困=潦倒=")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertEqual(parsed.hint, PURE_HANZI_SERIAL_HINT)


class SingleCharRhymeNormalizeTests(unittest.TestCase):
    def test_question_zou_normalizes(self):
        self.assertEqual(normalize_search_query("?就="), "就=")

    def test_zou_canonical(self):
        parsed = _parse("就=")
        self.assertIsInstance(parsed, SingleCharRhymeAnchorQuery)

    def test_question_zou_still_works(self):
        parsed = _parse("?就=")
        self.assertIsInstance(parsed, SingleCharRhymeAnchorQuery)


class SerialMatchSpecTests(unittest.TestCase):
    def test_four_rhyme_spec(self):
        spec = build_match_spec(_parse("04困=49倒="))
        self.assertEqual(spec.width, 4)
        code_pos = {s.pos: s.value for s in spec.slots if s.kind == "code_digit"}
        self.assertEqual(code_pos, {0: "0", 1: "4", 2: "4", 3: "9"})


if __name__ == "__main__":
    unittest.main()
