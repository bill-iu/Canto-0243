"""PR-A: code constraints from slots/mask only — not code_prefix blob."""
from __future__ import annotations

import unittest

from app.services.position_match.filters.f1_slot_code import matches_code_positions
from app.services.position_match.mask_adapter import (
    dense_code_from_spec,
    required_codes_from_digit_string,
    required_codes_from_spec,
)
from app.services.position_match.spec import MatchSpec, SlotConstraint


class CodeDigitRequiredCodesTests(unittest.TestCase):
    def test_required_codes_ignores_code_prefix_blob(self):
        spec = MatchSpec(
            width=2,
            code_prefix="99",
            slots=[
                SlotConstraint(pos=0, kind="code_digit", value="3"),
                SlotConstraint(pos=1, kind="code_digit", value="9"),
            ],
        )
        self.assertEqual(required_codes_from_spec(spec), ["3", "9"])
        self.assertEqual(dense_code_from_spec(spec), "39")

    def test_sparse_slots_no_dense(self):
        spec = MatchSpec(
            width=3,
            code_prefix="349",
            mask="?a?",
            slots=[
                SlotConstraint(pos=0, kind="code_digit", value="3"),
                SlotConstraint(pos=2, kind="code_digit", value="4"),
            ],
        )
        self.assertEqual(required_codes_from_spec(spec), ["3", None, "4"])
        self.assertIsNone(dense_code_from_spec(spec))

    def test_prefix_shorter_than_word_code(self):
        required = required_codes_from_digit_string("23")
        self.assertTrue(matches_code_positions("23", required, "m1"))
        self.assertTrue(matches_code_positions("2399", required, "m1"))
        self.assertTrue(matches_code_positions("69", required, "m1"))  # 2↔6, 3↔9
        self.assertFalse(matches_code_positions("00", required, "m1"))


if __name__ == "__main__":
    unittest.main()
