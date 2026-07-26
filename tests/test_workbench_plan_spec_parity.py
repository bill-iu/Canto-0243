"""L1 MatchSpec + L3 relaxation + L2 group fixtures (no DB)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.schemas.workbench_schema import ReplacementPlanV1
from app.services.workbench.build_match_spec import (
    build_match_spec,
    compile_replacement_plan,
    match_spec_to_canonical,
)
from app.services.workbench.group_candidates import group_candidates, group_literals
from app.services.workbench.relaxation import relaxation_ids

CASES = Path("contracts/workbench-plan-spec-cases.json")


class WorkbenchPlanSpecParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = json.loads(CASES.read_text(encoding="utf-8"))

    def test_l1_match_spec_and_l3_relaxation_ids(self) -> None:
        for item in self.doc["cases"]:
            with self.subTest(item["id"]):
                plan = ReplacementPlanV1.model_validate(item["plan"])
                got = match_spec_to_canonical(build_match_spec(plan))
                self.assertEqual(got, item["matchSpec"], msg=item["id"])
                canonical = compile_replacement_plan(plan)
                self.assertEqual(canonical.candidate_scope, "complete", msg=item["id"])
                self.assertEqual(canonical.width, item["matchSpec"]["width"], msg=item["id"])
                self.assertEqual(canonical.mask, item["matchSpec"]["mask"], msg=item["id"])
                self.assertEqual(
                    canonical.equals_span is not None,
                    bool(item["matchSpec"]["extra"].get("equals_span")),
                    msg=item["id"],
                )
                self.assertEqual(relaxation_ids(plan), item["relaxationIds"], msg=item["id"])

    def test_l2_group_literals(self) -> None:
        for item in self.doc["groupCases"]:
            with self.subTest(item["id"]):
                plan = ReplacementPlanV1.model_validate(item["plan"])
                pool = SimpleNamespace(
                    syns=item["pool"]["syns"],
                    semantic=item["pool"]["semantic"],
                )
                groups = group_candidates(plan, item["rows"], pool)
                self.assertEqual(group_literals(groups), item["literals"], msg=item["id"])


if __name__ == "__main__":
    unittest.main()
