"""Reported workbench rhyme + creator POS regression against the local lexicon."""

from __future__ import annotations

import unittest

from app.schemas.workbench_schema import ReplacementPlanV1
from app.utils.jyutping_codec import rhyme_finals_from_jyutping
from app.services.workbench.replacement_planner import plan_replacements
from ingest.project_pos import DEFAULT_TSV, parse_project_pos_tsv
from tests.smoke.helpers import LYRICS_DB, lyrics_sessionmaker


@unittest.skipUnless(LYRICS_DB.is_file() and DEFAULT_TSV.is_file(), "lyrics.db and POS SSOT required")
class WorkbenchPosRegressionTests(unittest.TestCase):
    def test_疑難_00_direct_synonyms_are_visible_on_first_page(self) -> None:
        plan = ReplacementPlanV1.model_validate({
            "version": 1,
            "selectionVersion": 1,
            "width": 2,
            "mode": "m1",
            "slots": [
                {"pos": 0, "kind": "code_digit", "digit": "0"},
                {"pos": 1, "kind": "code_digit", "digit": "0"},
            ],
            "semanticIntent": "ranked",
            "semanticSeed": "疑難",
            "limit": 120,
        })

        Session = lyrics_sessionmaker()
        with Session() as db:
            response = plan_replacements(plan, db)

        direct = response.exact.direct_syn
        self.assertTrue(direct)
        self.assertTrue(all(item.code == "00" for item in direct))
        self.assertIn("疑團", [item.literal for item in direct])
        self.assertIn("疑雲", [item.literal for item in direct])

    def test_窮困潦倒_selected_suffix_readings_narrow_workbench_candidates(self) -> None:
        plan = ReplacementPlanV1.model_validate({
            "version": 1,
            "selectionVersion": 1,
            "width": 4,
            "mode": "m1",
            "slots": [
                {"pos": 1, "kind": "final_anchor", "ref": "困", "refJyutping": "kwan3"},
                {"pos": 2, "kind": "final_anchor", "ref": "潦", "refJyutping": "liu2"},
                {"pos": 3, "kind": "final_anchor", "ref": "倒", "refJyutping": "dou2"},
            ],
            "semanticIntent": "off",
            "limit": 120,
        })

        Session = lyrics_sessionmaker()
        with Session() as db:
            workbench = plan_replacements(plan, db)

        workbench_literals = [item.literal for item in workbench.exact.sound_only]
        self.assertTrue(workbench_literals)
        self.assertEqual(len(workbench_literals), len(set(workbench_literals)))
        expected_finals = ["an", "iu", "ou"]
        for item in workbench.exact.sound_only:
            self.assertEqual(rhyme_finals_from_jyutping(item.jyutping)[1:], expected_finals)

    def test_changing_selected_readings_changes_contiguous_rhyme_results(self) -> None:
        def plan(readings: tuple[str, str, str]) -> ReplacementPlanV1:
            return ReplacementPlanV1.model_validate({
                "version": 1,
                "selectionVersion": 1,
                "width": 4,
                "mode": "m1",
                "slots": [
                    {"pos": pos, "kind": "final_anchor", "ref": ref, "refJyutping": reading}
                    for pos, ref, reading in zip((1, 2, 3), "困潦倒", readings)
                ],
                "semanticIntent": "off",
                "limit": 120,
            })

        Session = lyrics_sessionmaker()
        with Session() as db:
            selected = plan_replacements(plan(("kwan3", "liu2", "dou2")), db)
            changed = plan_replacements(plan(("wan3", "lou5", "dou3")), db)

        selected_literals = [item.literal for item in selected.exact.sound_only]
        changed_literals = [item.literal for item in changed.exact.sound_only]
        self.assertNotEqual(selected_literals, changed_literals)

    def test_稻草_whole_rhyme_candidates_survive_distinct_pos_filters(self) -> None:
        plan = ReplacementPlanV1.model_validate({
            "version": 1,
            "selectionVersion": 1,
            "width": 2,
            "mode": "m1",
            "slots": [
                {"pos": 0, "kind": "final_anchor", "ref": "稻", "refJyutping": "dou6"},
                {"pos": 1, "kind": "final_anchor", "ref": "草", "refJyutping": "cou2"},
            ],
            "semanticIntent": "off",
            "limit": 120,
        })

        Session = lyrics_sessionmaker()
        with Session() as db:
            response = plan_replacements(plan, db)

        candidates = {
            item.literal
            for group in (
                response.exact.direct_syn,
                response.exact.semantic_related,
                response.exact.sound_only,
            )
            for item in group
        }
        pos_table = parse_project_pos_tsv()
        buckets = {
            code: {literal for literal in candidates if code in pos_table.get(literal, _EMPTY_POS).display_pos()}
            for code in ("n", "v", "a", "r")
        }

        self.assertTrue(all(buckets.values()), buckets)
        self.assertGreater(len({frozenset(values) for values in buckets.values()}), 1, buckets)


class _EmptyPos:
    @staticmethod
    def display_pos() -> frozenset[str]:
        return frozenset()


_EMPTY_POS = _EmptyPos()


if __name__ == "__main__":
    unittest.main()
