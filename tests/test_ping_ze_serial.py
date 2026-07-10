"""Explicit pingze mode parser and mixed-slot matching."""
from __future__ import annotations

import unittest

from app.services.ping_zak import code_matches_ping_ze_pattern, ping_zak_class
from app.services.query_match_spec_registry import build_match_spec_for_parsed
from app.services.query_parse import normalize_and_parse
from app.services.query_types import JyutpingFragmentQuery, PingZeSerialQuery, QueryKind, UnmatchedQuery


class PingZakClassTests(unittest.TestCase):
    def test_ping_is_fixed_to_stored_394052_digits(self):
        self.assertEqual(ping_zak_class("0"), "ping")
        self.assertEqual(ping_zak_class("3"), "ping")
        self.assertEqual(ping_zak_class("9"), "ze")


class PingZeParseTests(unittest.TestCase):
    def test_only_explicit_mode_claims_pingze_tokens(self):
        parsed = normalize_and_parse("PZ3", mode="pz", pzmode="m2")
        self.assertIsInstance(parsed, PingZeSerialQuery)
        self.assertEqual(parsed.pzmode, "m2")
        self.assertEqual(parsed.raw_q, "PZ3")

        normal = normalize_and_parse("pz3", mode="m1")
        self.assertIsInstance(normal, JyutpingFragmentQuery)

    def test_question_mark_is_one_unconstrained_slot(self):
        parsed = normalize_and_parse("PZ?", mode="pz")
        self.assertIsInstance(parsed, PingZeSerialQuery)
        spec = build_match_spec_for_parsed(parsed)
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.width, 3)
        self.assertEqual(spec.mask, "???")
        self.assertEqual([(s.pos, s.kind, s.value) for s in spec.slots], [
            (0, "tone_class", "ping"),
            (1, "tone_class", "ze"),
        ])
        self.assertEqual(parsed.kind, QueryKind.PING_ZE_SERIAL)

    def test_rhyme_anchor_composes_after_pingze_slots(self):
        parsed = normalize_and_parse("PZ好=", mode="pz")
        self.assertIsInstance(parsed, PingZeSerialQuery)
        spec = build_match_spec_for_parsed(parsed)
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.width, 3)
        self.assertIn((2, "final_anchor", "好"), [(s.pos, s.kind, s.value) for s in spec.slots])

    def test_jyutping_anchor_is_rejected_only_in_pingze_mode(self):
        parsed = normalize_and_parse("?hon", mode="pz")
        self.assertIsInstance(parsed, UnmatchedQuery)
        self.assertIn("不支援粵拼錨", parsed.hint or "")

    def test_existing_non_jyutping_anchor_families_accept_pingze_slots(self):
        cases = {
            "PZ好=": "final_anchor",
            "=好PZ": "initial_anchor",
            "PZ+好": "literal_char",
            "PZ+好=": "final_anchor",
            "PZ@手": "literal_char",
            "?PZ好=": "final_anchor",
            "?PZ人": "final_anchor",
            "PZ困=49倒=": "final_anchor",
            "PZ人=?": "final_anchor",
        }
        for query, anchor_kind in cases.items():
            with self.subTest(query=query):
                parsed = normalize_and_parse(query, mode="pz")
                self.assertIsInstance(parsed, PingZeSerialQuery)
                spec = build_match_spec_for_parsed(parsed)
                self.assertIsNotNone(spec)
                assert spec is not None
                kinds = {(slot.pos, slot.kind, slot.value) for slot in spec.slots}
                self.assertTrue(any(slot.kind == "tone_class" and slot.value == "ping" for slot in spec.slots))
                self.assertTrue(any(slot.kind == "tone_class" and slot.value == "ze" for slot in spec.slots))
                self.assertTrue(any(slot.kind == anchor_kind for slot in spec.slots))


class PingZeMatchTests(unittest.TestCase):
    def test_pz_is_fixed_while_numeric_slot_uses_pzmode(self):
        self.assertTrue(code_matches_ping_ze_pattern("399", "PZ3", "m1"))
        self.assertFalse(code_matches_ping_ze_pattern("399", "PZ3", "m2"))
        self.assertFalse(code_matches_ping_ze_pattern("999", "PZ3", "m1"))

    def test_wildcard_is_exactly_one_slot(self):
        self.assertTrue(code_matches_ping_ze_pattern("029", "PZ?", "m3"))
        self.assertFalse(code_matches_ping_ze_pattern("02", "PZ?", "m3"))


if __name__ == "__main__":
    unittest.main()
