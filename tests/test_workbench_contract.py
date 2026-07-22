"""句格工作台跨端 JSON contract。"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from app.schemas.workbench_schema import (
    ReplacementPlanV1,
    WorkbenchCandidate,
    WorkbenchCandidateResponse,
)


class ReplacementPlanContractTests(unittest.TestCase):
    def test_unknown_contract_version_is_rejected(self):
        payload = {
            "version": 2,
            "selectionVersion": 1,
            "width": 1,
            "mode": "m1",
            "slots": [],
            "semanticIntent": "off",
            "limit": 20,
        }

        with self.assertRaises(ValidationError):
            ReplacementPlanV1.model_validate(payload)

    def test_selection_width_must_be_between_one_and_line_max(self):
        base = {
            "version": 1,
            "selectionVersion": 1,
            "mode": "m1",
            "slots": [],
            "semanticIntent": "off",
            "limit": 20,
        }

        for width in (0, 65):
            with self.subTest(width=width), self.assertRaises(ValidationError):
                ReplacementPlanV1.model_validate({**base, "width": width})
        # ADR-0069: width 5–64 accepted (was hard-capped at 4)
        ReplacementPlanV1.model_validate({**base, "width": 5})
        ReplacementPlanV1.model_validate({**base, "width": 64})

    def test_slot_position_must_fit_selection_width(self):
        payload = {
            "version": 1,
            "selectionVersion": 1,
            "width": 1,
            "mode": "m1",
            "slots": [{"pos": 1, "kind": "code_digit", "digit": "3"}],
            "semanticIntent": "off",
            "limit": 20,
        }

        with self.assertRaises(ValidationError):
            ReplacementPlanV1.model_validate(payload)

    def test_each_slot_kind_requires_its_payload(self):
        base = {
            "version": 1,
            "selectionVersion": 1,
            "width": 1,
            "mode": "m1",
            "semanticIntent": "off",
            "limit": 20,
        }

        for kind in ("code_digit", "literal_char", "final_anchor", "initial_anchor", "tone_class"):
            with self.subTest(kind=kind), self.assertRaises(ValidationError):
                ReplacementPlanV1.model_validate(
                    {**base, "slots": [{"pos": 0, "kind": kind}]}
                )


class CandidateContractTests(unittest.TestCase):
    def test_candidate_reasons_must_be_structured(self):
        payload = {
            "literal": "快樂",
            "jyutping": "faai3 lok6",
            "code": "42",
            "group": "direct_syn",
            "reasons": ["直接近義"],
            "sourceRank": 1,
        }

        with self.assertRaises(ValidationError):
            WorkbenchCandidate.model_validate(payload)

    def test_response_has_exactly_three_candidate_groups(self):
        payload = {
            "version": 1,
            "selectionVersion": 1,
            "exact": {
                "direct_syn": [],
                "semantic_related": [],
                "sound_only": [],
                "other": [],
            },
            "relaxation": None,
        }

        with self.assertRaises(ValidationError):
            WorkbenchCandidateResponse.model_validate(payload)


class PublishedSchemaTests(unittest.TestCase):
    def test_schema_publishes_version_width_and_candidate_groups(self):
        path = Path("contracts/workbench-candidate.schema.json")
        schema = json.loads(path.read_text(encoding="utf-8"))

        plan = schema["$defs"]["ReplacementPlanV1"]
        self.assertEqual(plan["properties"]["version"]["const"], 1)
        self.assertEqual(plan["properties"]["width"]["maximum"], 64)
        self.assertEqual(plan["properties"]["limit"]["maximum"], 400)
        self.assertIn("offset", plan["properties"])
        response = schema["$defs"]["WorkbenchCandidateResponse"]
        self.assertIn("total", response["required"])
        candidate = schema["$defs"]["WorkbenchCandidate"]
        self.assertEqual(
            candidate["properties"]["group"]["enum"],
            ["direct_syn", "semantic_related", "sound_only"],
        )

    def test_all_golden_plans_validate_against_published_schema(self):
        schema = json.loads(
            Path("contracts/workbench-candidate.schema.json").read_text(encoding="utf-8")
        )
        cases = json.loads(
            Path("contracts/workbench-candidate-cases.json").read_text(encoding="utf-8")
        )["cases"]
        validator = Draft202012Validator(schema)

        self.assertEqual(len(cases), 8)
        self.assertEqual(len({case["id"] for case in cases}), len(cases))
        for case in cases:
            with self.subTest(case=case["id"]):
                validator.validate(case["plan"])


if __name__ == "__main__":
    unittest.main()
