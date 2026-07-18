"""碼尾／中格 hybrid 聲母粵拼錨（34p／34+p／3+p4；gw／kw）。"""
from __future__ import annotations

import unittest

from app.services.jyutping_anchor import parse_jyutping_anchor_query
from app.services.query_match_spec_registry import build_match_spec_for_parsed
from app.services.query_parse import normalize_and_parse
from app.services.query_types import QueryKind


class HybridInitialJyutpingAnchorTests(unittest.TestCase):
    def test_34p_end_initial(self):
        p = parse_jyutping_anchor_query("34p")
        self.assertIsNotNone(p)
        assert p is not None
        self.assertEqual(p["width"], 2)
        self.assertEqual(p["anchor_pos"], 1)
        self.assertEqual(p["anchor_kind"], "initial_letters")
        self.assertEqual(p["anchor_value"], "p")
        self.assertEqual(p["code_slots"], [(0, "3"), (1, "4")])

    def test_34on_still_syllable_end(self):
        p = parse_jyutping_anchor_query("34on")
        self.assertIsNotNone(p)
        assert p is not None
        self.assertEqual(p["anchor_kind"], "syllable_letters")
        self.assertEqual(p["anchor_pos"], 1)
        self.assertEqual(p["anchor_value"], "on")

    def test_34_plus_p_tail(self):
        p = parse_jyutping_anchor_query("34+p")
        self.assertIsNotNone(p)
        assert p is not None
        self.assertEqual(p["width"], 3)
        self.assertEqual(p["anchor_pos"], 2)
        self.assertEqual(p["anchor_value"], "p")
        self.assertEqual(p["code_slots"], [(0, "3"), (1, "4")])

    def test_3_plus_p4_middle(self):
        for q in ("3+p4", "3?p4"):
            p = parse_jyutping_anchor_query(q)
            self.assertIsNotNone(p, q)
            assert p is not None
            self.assertEqual(p["width"], 3, q)
            self.assertEqual(p["anchor_pos"], 1, q)
            self.assertEqual(p["anchor_value"], "p", q)
            self.assertEqual(p["code_slots"], [(0, "3"), (2, "4")], q)

    def test_gw_cluster_forms(self):
        end = parse_jyutping_anchor_query("34gw")
        self.assertIsNotNone(end)
        assert end is not None
        self.assertEqual(end["anchor_value"], "gw")
        self.assertEqual(end["anchor_pos"], 1)

        mid = parse_jyutping_anchor_query("3+gw4")
        self.assertIsNotNone(mid)
        assert mid is not None
        self.assertEqual(mid["anchor_value"], "gw")
        self.assertEqual(mid["anchor_pos"], 1)
        self.assertEqual(mid["code_slots"], [(0, "3"), (2, "4")])

        tail = parse_jyutping_anchor_query("34+gw")
        self.assertIsNotNone(tail)
        assert tail is not None
        self.assertEqual(tail["width"], 3)
        self.assertEqual(tail["anchor_pos"], 2)

    def test_ng_not_pure_initial_hybrid(self):
        # 34ng stays hybrid rhyme (ambiguous), not initial hybrid
        p = parse_jyutping_anchor_query("34ng")
        self.assertIsNotNone(p)
        assert p is not None
        self.assertEqual(p["anchor_kind"], "rhyme_letters")

    def test_match_spec_per_digit_slots(self):
        for q in ("34p", "34+p", "3+p4", "3?p4", "34gw"):
            parsed = normalize_and_parse(q)
            self.assertEqual(parsed.kind, QueryKind.JYUTPING_ANCHOR, q)
            spec = build_match_spec_for_parsed(parsed)
            self.assertIsNotNone(spec, q)
            assert spec is not None
            digits = sorted(
                (s.pos, s.value) for s in spec.slots if s.kind == "code_digit"
            )
            inits = [s for s in spec.slots if s.kind == "initial_letters"]
            self.assertTrue(digits, q)
            self.assertEqual(len(inits), 1, q)
            # no reliance on bare prefix-only matching: every digit is a slot
            for pos, val in digits:
                self.assertRegex(val, r"^\d$", q)
                self.assertIsInstance(pos, int)

    def test_dollar_hanzi_syllable_includes_literal_row(self):
        """$獅 → si syllable anchor；唔排除字面「獅」；唔因 2000 cap 漏 舞獅。"""
        from app.database import SessionLocal
        from app.services.query_dispatch import search_words

        db = SessionLocal()
        try:
            at_chars = {
                (r.get("char") if isinstance(r, dict) else r.char)
                for r in search_words(q="43@獅", mode="m1", limit=50, offset=0, db=db)
            }
            dollar_chars = {
                (r.get("char") if isinstance(r, dict) else r.char)
                for r in search_words(q="43$獅", mode="m1", limit=200, offset=0, db=db)
            }
            self.assertIn("舞獅", at_chars)
            self.assertIn("舞獅", dollar_chars)
            parsed = normalize_and_parse("43$獅")
            self.assertEqual(parsed.kind, QueryKind.JYUTPING_ANCHOR)
            self.assertEqual(getattr(parsed, "anchor_kind", None), "syllable_letters")
            self.assertEqual(getattr(parsed, "anchor_value", None), "si")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
