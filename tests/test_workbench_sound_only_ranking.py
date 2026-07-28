from __future__ import annotations

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from app.services.workbench.group_candidates import group_candidates
from app.services.position_match.engine import execute_dual_phoneme_anchor_specs
from app.services.position_match.spec import MaskFamilySearchResult


class WorkbenchSoundOnlyRankingTests(TestCase):
    def test_sound_only_uses_essay_frequency_not_input_row_order(self) -> None:
        plan = SimpleNamespace(semantic_intent="off", slots=[])
        rows = [
            {"char": "低頻", "jyutping": "dai1 fan4", "code": "11"},
            {"char": "高頻", "jyutping": "gou1 fan4", "code": "22"},
        ]

        with patch(
            "app.domain.lexicon.ranking.get_essay_frequency",
            side_effect={"低頻": 1, "高頻": 100}.get,
        ):
            groups = group_candidates(plan, rows, None)

        self.assertEqual([candidate.literal for candidate in groups.sound_only], ["高頻", "低頻"])

    def test_dual_phoneme_union_is_canonically_sorted_before_paging(self) -> None:
        initial = MaskFamilySearchResult(items=[
            {"char": "低頻", "jyutping": "dai1 fan4", "code": "11"},
        ])
        final = MaskFamilySearchResult(items=[
            {"char": "高頻", "jyutping": "gou1 fan4", "code": "22"},
        ])

        with (
            patch(
                "app.services.position_match.engine.execute_canonical_match_spec",
                side_effect=[initial, final],
            ),
            patch(
                "app.domain.lexicon.ranking.get_essay_frequency",
                side_effect={"低頻": 1, "高頻": 100}.get,
            ),
        ):
            result = execute_dual_phoneme_anchor_specs(
                object(),
                object(),
                code=None,
                mode="m1",
                limit=2,
                offset=0,
                db=object(),
            )

        self.assertEqual([item["char"] for item in result.items], ["高頻", "低頻"])


if __name__ == "__main__":
    import unittest

    unittest.main()
