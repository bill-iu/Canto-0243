"""Dense full-width code uses unlimited LengthCode source (貪婪→金錢)."""
from __future__ import annotations

import unittest

from app.services.position_match.sources import (
    LengthCodeCandidateSource,
    LengthMaskCandidateSource,
    _resolve_mask_family_source,
)
from app.services.position_match.spec import MatchSpec, SlotConstraint


class WorkbenchDenseCodeSourceTests(unittest.TestCase):
    def test_dense_code_on_q_mask_uses_unlimited_length_code(self) -> None:
        spec = MatchSpec(
            width=2,
            mask="??",
            slots=[
                SlotConstraint(pos=0, kind="code_digit", value="3"),
                SlotConstraint(pos=1, kind="code_digit", value="0"),
            ],
        )
        source, _ = _resolve_mask_family_source(spec, db=None, mode="m1", query_code=None)
        self.assertIsInstance(source, LengthCodeCandidateSource)
        assert isinstance(source, LengthCodeCandidateSource)
        self.assertEqual(source.code, "30")
        self.assertIsNone(source.fallback_limit)

    def test_literal_mask_without_dense_code_stays_mask_source(self) -> None:
        spec = MatchSpec(width=2, mask="香?", slots=[])
        source, _ = _resolve_mask_family_source(spec, db=None, mode="m1", query_code=None)
        self.assertIsInstance(source, LengthMaskCandidateSource)


if __name__ == "__main__":
    unittest.main()
