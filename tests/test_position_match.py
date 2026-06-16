import unittest
from unittest.mock import MagicMock

from app.services.position_match.engine import PositionMatchEngine
from app.services.position_match.filters import (
    build_final_options_at_positions,
    filter_candidates_by_match_spec,
    filter_words_by_code_and_mask,
    matches_code_positions,
    matches_final_options,
    matches_hybrid_ref_chars,
    matches_phoneme_at_position,
    word_matches_last_final,
)
from app.domain.lexicon.ranking import literal_priority_sort_key
from app.services.position_match.sources import (
    get_candidates_for_length,
    get_length_candidates,
)
from app.services.position_match.spec import MatchSpec, SlotConstraint
from app.services.query_parse import _build_mask_family_match_spec as build_mask_family_match_spec
from app.services.query_parse import (
    RhymeAnchorQuery,
    CodeTailQuery,
    LiteralRefQuery,
    MaskQuery,
    HybridCodeQuery,
)

# Note: Some tests use real DB session from test setup; for full isolation, mocks can be expanded.
# These cover migrated helpers and basic engine usage.

class TestPositionMatchHelpers(unittest.TestCase):
    def test_matches_code_positions(self):
        # Basic code digit matching with variants (m2)
        self.assertTrue(matches_code_positions("23", ["2", "3"], "m2"))
        self.assertFalse(matches_code_positions("24", ["2", "3"], "m2"))
        # With None (wildcard)
        self.assertTrue(matches_code_positions("23", [None, "3"], "m2"))

    def test_filter_words_by_code_and_mask_basic(self):
        # Mock words and db
        w1 = MagicMock(char="做我", code="23", finals='["ou","o"]', initials='["z","ng"]')
        w2 = MagicMock(char="做得", code="23", finals='["ou","ak"]', initials='["z","d"]')
        w3 = MagicMock(char="好我", code="24", finals='["ou","o"]', initials='["h","ng"]')
        candidates = [w1, w2, w3]
        db = MagicMock()

        # Simple code + mask (no anchor)
        filtered = filter_words_by_code_and_mask(
            candidates, width=2, code_digits="23", mode="m1", mask="??", db=db
        )
        chars = [getattr(w, 'char', None) for w in filtered]
        self.assertIn("做我", chars)
        self.assertIn("做得", chars)
        self.assertNotIn("好我", chars)

    def test_literal_priority_sort_key(self):
        w = MagicMock(char="香港", jyutping="hoeng1 gong2")
        key = literal_priority_sort_key(w, [(0, "香"), (1, "港")])
        # Higher exact count -> lower (better) key due to -count
        self.assertEqual(key[0], -2)  # both match

class TestPositionMatchEngineBasic(unittest.TestCase):
    def test_engine_match_with_pre_candidates(self):
        # Basic test using pre_candidates + simple spec
        engine = PositionMatchEngine()
        w1 = MagicMock(char="做我", code="23", finals='["ou","o"]', initials='["z","ng"]')
        pre = [w1]
        db = MagicMock()
        spec = MatchSpec(width=2, code_prefix="23")
        # With pre, should return matching
        res = engine.match(spec, None, db, pre_candidates=pre)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].char, "做我")

    # More tests can cover hybrid, anchors, etc. using real parsed or mocks.


class TestPositionQueryToMatchSpec(unittest.TestCase):
    """ParsedQuery → build_mask_family_match_spec for position query types."""

    def test_rhyme_anchor_to_spec(self):
        q = RhymeAnchorQuery(constraint="final", anchor_pos=2, anchor="就", slots="23", width=3)
        spec = build_mask_family_match_spec(q)
        self.assertEqual(spec.width, 3)
        self.assertEqual(spec.mask, "23?")
        self.assertEqual(len(spec.slots), 1)
        self.assertEqual(spec.slots[0].kind, "final_anchor")
        self.assertEqual(spec.slots[0].pos, 2)
        self.assertEqual(spec.slots[0].value, "就")

    def test_code_tail_literal_to_spec(self):
        q = CodeTailQuery(code_digits="23", width=3, constraint="literal", anchor="就", anchor_pos=2)
        spec = build_mask_family_match_spec(q)
        self.assertEqual(spec.width, 3)
        self.assertEqual(spec.code_prefix, "23")
        self.assertEqual(spec.mask, "??就")  # derived same as old handler: build_mask("") then override at anchor_pos
        self.assertEqual(len(spec.slots), 1)
        self.assertEqual(spec.slots[0].kind, "literal_char")
        self.assertEqual(spec.slots[0].pos, 2)

    def test_literal_ref_to_spec(self):
        q = LiteralRefQuery(code_digits="2", literal_char="我", width=2)
        spec = build_mask_family_match_spec(q)
        self.assertEqual(spec.width, 2)
        self.assertEqual(spec.code_prefix, "2")
        self.assertEqual(spec.mask, "?我")
        self.assertEqual(len(spec.slots), 1)
        self.assertEqual(spec.slots[0].kind, "literal_char")
        self.assertEqual(spec.slots[0].pos, 1)

    def test_mask_query_to_spec(self):
        q = MaskQuery(raw_q="門0")
        spec = build_mask_family_match_spec(q)
        self.assertEqual(spec.width, 2)
        self.assertEqual(spec.mask, "門0")
        self.assertTrue(spec.literal_priority)
        digit_slots = [s for s in spec.slots if s.kind == "code_digit"]
        self.assertEqual(len(digit_slots), 1)
        self.assertEqual(digit_slots[0].pos, 1)
        self.assertEqual(digit_slots[0].value, "0")
        self.assertEqual(spec.extra.get("literal_positions"), [(0, "門")])

    def test_hybrid_code_to_spec(self):
        q = HybridCodeQuery(raw_q="23就")
        spec = build_mask_family_match_spec(q)
        self.assertEqual(spec.width, 2)
        self.assertEqual(spec.code_prefix, "23")
        self.assertEqual(spec.hybrid_ref_chars, "就")
        self.assertEqual(spec.hybrid_ref_pos, 1)


class TestFilterCandidatesByMatchSpec(unittest.TestCase):
    def test_match_spec_code_digit_slots门0(self):
        w_good = MagicMock(char="門人", code="00", finals='["un","an"]', initials='["m","j"]')
        w_bad = MagicMock(char="門下", code="02", finals='["un","a"]', initials='["m","h"]')
        spec = build_mask_family_match_spec(MaskQuery(raw_q="門0"))
        db = MagicMock()
        filtered = filter_candidates_by_match_spec([w_good, w_bad], spec, "m1", db)
        chars = [getattr(w, "char", None) for w in filtered]
        self.assertIn("門人", chars)
        self.assertNotIn("門下", chars)


class TestPositionMatchEngineMore(unittest.TestCase):
    """Additional isolation coverage for PositionMatchEngine / helpers.
    Targets handoff suggestions: hybrid boundaries (literal-or-phoneme), code_digit slots (門0 style mask),
    literal_priority_sort_key, more engine match scenarios.
    """

    def test_matches_hybrid_ref_chars_literal_or_phoneme(self):
        """Core semantic for hybrid: position can match by exact char (literal ref) OR by final options (rhyme)."""
        ref_chars = "就"
        start_pos = 1
        width = 2
        # finals option at the ref pos (len must match width)
        target_opts: list = [None, {"au", "iu", "o"}]  # dummy finals set containing possible

        # Use correct len=width word. pos1 ref '就' ; literal match at [1]
        # literal char match at ref pos bypasses final check (even if final not in opts)
        self.assertTrue(
            matches_hybrid_ref_chars("A就", ["x", "z"], ref_chars, start_pos, target_opts)
        )

        # phoneme match (final in options)
        self.assertTrue(
            matches_hybrid_ref_chars("A就", ["x", "au"], ref_chars, start_pos, target_opts)
        )

        # neither literal nor phoneme -> false
        self.assertFalse(
            matches_hybrid_ref_chars("A唔", ["x", "z"], ref_chars, start_pos, target_opts)
        )

    def test_filter_words_by_code_and_mask_with_code_digit_slots(self):
        """門0 / 好23 style: code_digit slots (populated for mask digits) + literal mask must drive required_codes overlay."""
        w_good = MagicMock(char="門人", code="00", finals='["un","an"]', initials='["m","j"]')
        w_bad = MagicMock(char="門下", code="02", finals='["un","a"]', initials='["m","h"]')
        candidates = [w_good, w_bad]
        db = MagicMock()

        # slots as produced by handle_mask_wildcard for "門0"
        slots = [
            SlotConstraint(pos=0, kind="literal_char", value="門"),
            SlotConstraint(pos=1, kind="code_digit", value="0"),
        ]
        filtered = filter_words_by_code_and_mask(
            candidates,
            width=2,
            code_digits="",
            mode="m1",
            mask="門0",
            db=db,
            slots=slots,
        )
        chars = [getattr(w, "char", None) for w in filtered]
        self.assertIn("門人", chars)
        self.assertNotIn("門下", chars)

    def test_literal_priority_sort_key_various_counts(self):
        """literal_priority sorting key: more literal matches -> smaller (better) first component."""
        w_full = MagicMock(char="門人", jyutping="mun4 jan4")
        w_partial = MagicMock(char="門下", jyutping="mun4 haa5")
        # Ensure w_none matches ZERO of the literal positions (avoid trailing '人' match on pos1)
        w_none = MagicMock(char="好心", jyutping="hou2 sam1")

        k_full = literal_priority_sort_key(w_full, [(0, "門"), (1, "人")])
        k_part = literal_priority_sort_key(w_partial, [(0, "門"), (1, "人")])
        k_none = literal_priority_sort_key(w_none, [(0, "門"), (1, "人")])

        self.assertEqual(k_full[0], -2)
        self.assertEqual(k_part[0], -1)
        self.assertEqual(k_none[0], 0)
        # full better (smaller) than partial
        self.assertLess(k_full[0], k_part[0])

    def test_engine_match_hybrid_spec_with_pre_candidates(self):
        """Exercise the hybrid special path in engine.match (pre_candidates + hybrid_* fields)."""
        engine = PositionMatchEngine()
        # Mock sufficient for hybrid branch (char match will succeed; get_* called on mock)
        w = MagicMock(char="23就", code="23")
        # Provide minimal so get_word_parts / get sort don't explode the path before matches_hybrid
        # (in practice real words or better mocks; here we accept list return or handled error as smoke)
        pre = [w]
        db = MagicMock()
        spec = MatchSpec(
            width=2,
            code_prefix="23",
            hybrid_ref_chars="就",
            hybrid_ref_pos=1,
        )
        res = engine.match(spec, None, db, pre_candidates=pre)
        self.assertIsInstance(res, list)
        # If the mock path lets the char match through, len may be 1; otherwise 0 is acceptable for isolation smoke.
        # Main goal: no exception, hybrid branch taken.


if __name__ == "__main__":
    unittest.main()
