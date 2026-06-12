import unittest
from unittest.mock import MagicMock

from app.services.position_match import (
    PositionMatchEngine,
    MatchSpec,
    SlotConstraint,
    matches_code_positions,
    matches_phoneme_at_position,
    filter_words_by_code_and_mask,
    build_final_options_at_positions,
    word_matches_last_final,
    matches_final_options,
    matches_hybrid_ref_chars,
    mask_priority_key,
    get_length_candidates,
    get_candidates_for_length,
)
from app.services.query_engine import (
    RhymeAnchorQuery,
    CodeTailQuery,
    LiteralRefQuery,
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

    def test_mask_priority_key(self):
        w = MagicMock(char="香港", jyutping="hoeng1 gong2")
        key = mask_priority_key(w, [(0, "香"), (1, "港")])
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
    """Phase 2.3: verify the normalized to_match_spec() on position query dataclasses."""

    def test_rhyme_anchor_to_spec(self):
        q = RhymeAnchorQuery(constraint="final", anchor_pos=2, anchor="就", slots="23", width=3)
        spec = q.to_match_spec()
        self.assertEqual(spec.width, 3)
        self.assertEqual(spec.mask, "23?")
        self.assertEqual(len(spec.slots), 1)
        self.assertEqual(spec.slots[0].kind, "final_anchor")
        self.assertEqual(spec.slots[0].pos, 2)
        self.assertEqual(spec.slots[0].value, "就")

    def test_code_tail_literal_to_spec(self):
        q = CodeTailQuery(code_digits="23", width=3, constraint="literal", anchor="就", anchor_pos=2)
        spec = q.to_match_spec()
        self.assertEqual(spec.width, 3)
        self.assertEqual(spec.code_prefix, "23")
        self.assertEqual(spec.mask, "??就")  # derived same as old handler: build_mask("") then override at anchor_pos
        self.assertEqual(len(spec.slots), 1)
        self.assertEqual(spec.slots[0].kind, "literal_char")
        self.assertEqual(spec.slots[0].pos, 2)

    def test_literal_ref_to_spec(self):
        q = LiteralRefQuery(code_digits="2", literal_char="我", width=2)
        spec = q.to_match_spec()
        self.assertEqual(spec.width, 2)
        self.assertEqual(spec.code_prefix, "2")
        self.assertEqual(spec.mask, "?我")
        self.assertEqual(len(spec.slots), 1)
        self.assertEqual(spec.slots[0].kind, "literal_char")
        self.assertEqual(spec.slots[0].pos, 1)


if __name__ == "__main__":
    unittest.main()
