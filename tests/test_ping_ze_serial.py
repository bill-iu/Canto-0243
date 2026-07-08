"""平仄串列查詢 — parse, classify, match."""
from __future__ import annotations

import unittest

from app.services.ping_zak import (
    MATRIX_394052_MODE,
    code_matches_ping_ze_pattern,
    is_ping_ze_serial_query,
    ping_ze_effective_mode,
    ping_ze_mode_redirect_hint,
    ping_zak_class,
    try_parse_ping_ze_serial,
)
from app.services.query_parse import normalize_and_parse
from app.services.query_types import DigitCodeQuery, PingZeSerialQuery, QueryKind, UnmatchedQuery


class PingZakClassTests(unittest.TestCase):
    def test_ping_digits(self):
        self.assertEqual(ping_zak_class("0"), "ping")
        self.assertEqual(ping_zak_class("3"), "ping")

    def test_ze_digits(self):
        for d in ("2", "4", "5", "9"):
            self.assertEqual(ping_zak_class(d), "ze")


class PingZeParseTests(unittest.TestCase):
    def test_pure_ping_ze(self):
        parsed = normalize_and_parse("PZP")
        self.assertIsInstance(parsed, PingZeSerialQuery)
        self.assertEqual(parsed.raw_q, "PZP")

    def test_mixed_digit(self):
        parsed = normalize_and_parse("pz3")
        self.assertIsInstance(parsed, PingZeSerialQuery)
        self.assertEqual(parsed.raw_q, "PZ3")

    def test_pure_digits_stays_digit_code(self):
        parsed = normalize_and_parse("333")
        self.assertIsInstance(parsed, DigitCodeQuery)

    def test_invalid_mixed_hint(self):
        parsed = normalize_and_parse("PZ3開")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertIn("平仄串列", parsed.hint or "")

    def test_is_ping_ze_serial_query(self):
        self.assertTrue(is_ping_ze_serial_query("ZP"))
        self.assertFalse(is_ping_ze_serial_query("23"))


class PingZeModeRedirectTests(unittest.TestCase):
    def test_ping_ze_effective_mode_is_m3(self):
        self.assertEqual(MATRIX_394052_MODE, "m3")
        self.assertEqual(ping_ze_effective_mode(), "m3")

    def test_ping_ze_m3_redirect_silent(self):
        self.assertIsNone(ping_ze_mode_redirect_hint("m3"))


class PingZeMatchTests(unittest.TestCase):
    def test_zp_matches_23(self):
        self.assertTrue(code_matches_ping_ze_pattern("23", "ZP"))

    def test_pzp_rejects_23(self):
        self.assertFalse(code_matches_ping_ze_pattern("23", "PZP"))

    def test_pz3_third_digit(self):
        self.assertTrue(code_matches_ping_ze_pattern("023", "PZ3"))
        self.assertFalse(code_matches_ping_ze_pattern("022", "PZ3"))

    def test_digit_normalizes_02493(self):
        self.assertTrue(code_matches_ping_ze_pattern("023", "PZ7"))


if __name__ == "__main__":
    unittest.main()