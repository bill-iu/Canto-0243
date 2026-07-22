from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
import unittest

from app.models.word import Word
from app.schemas.workbench_schema import ReplacementPlanV1
from app.services.position_match.spec import MaskFamilySearchResult
from app.services.position_match.spec import get_equals_span
from app.services.workbench.replacement_planner import (
    build_match_spec,
    plan_replacements,
)
from tests.smoke.helpers import memory_sessionmaker


def make_plan(**changes) -> ReplacementPlanV1:
    data = {
        "version": 1,
        "selectionVersion": 7,
        "width": 2,
        "mode": "m3",
        "slots": [
            {"pos": 0, "kind": "literal_char", "literal": "香"},
            {"pos": 1, "kind": "code_digit", "digit": "9"},
        ],
        "semanticIntent": "ranked",
        "semanticSeed": "香港",
        "limit": 20,
    }
    data.update(changes)
    return ReplacementPlanV1.model_validate(data)


class WorkbenchPlannerTests(unittest.TestCase):
    def test_contiguous_rhyme_slots_share_prefix_wildcard_equals_semantics(self) -> None:
        spec = build_match_spec(make_plan(
            width=4,
            slots=[
                {"pos": 1, "kind": "final_anchor", "ref": "困", "refJyutping": "kwan3"},
                {"pos": 2, "kind": "final_anchor", "ref": "潦", "refJyutping": "liu5"},
                {"pos": 3, "kind": "final_anchor", "ref": "倒", "refJyutping": "dou2"},
            ],
            semanticIntent="off",
            semanticSeed="窮困潦倒",
        ))
        span = get_equals_span(spec)
        self.assertIsNotNone(span)
        self.assertEqual((span.ref_literal, span.start_pos), ("困潦倒", 1))
        self.assertEqual(span.ref_jyutping, "kwan3 liu5 dou2")
        self.assertEqual(span.dimension, "final")
        self.assertTrue(span.phoneme_anchor_only)
        self.assertFalse(span.whole_word)
        self.assertTrue(spec.extra.get("prefix_wildcard_equals"))
        self.assertFalse(any(slot.kind == "final_anchor" for slot in spec.slots))

    def test_plan_maps_directly_to_match_spec(self) -> None:
        spec = build_match_spec(make_plan())
        self.assertEqual(spec.width, 2)
        self.assertEqual(spec.mask, "香?")
        self.assertEqual([(slot.pos, slot.kind, slot.value) for slot in spec.slots], [
            (0, "literal_char", "香"),
            (1, "code_digit", "9"),
        ])

    def test_candidates_are_grouped_ranked_and_explained(self) -> None:
        rows = [
            {"char": "香江", "jyutping": "hoeng1 gong1", "code": "33"},
            {"char": "香港", "jyutping": "hoeng1 gong2", "code": "39"},
            {"char": "香島", "jyutping": "hoeng1 dou2", "code": "39"},
        ]
        pool = SimpleNamespace(
            syns=[{"char": "香港", "source": "manual"}],
            semantic=[{"char": "香島", "source": "embedding_cosine"}],
        )

        response = plan_replacements(
            make_plan(),
            object(),
            execute=lambda *_args, **_kwargs: MaskFamilySearchResult(items=rows),
            relation_projector=lambda *_args, **_kwargs: pool,
        )

        self.assertEqual([item.literal for item in response.exact.direct_syn], ["香港"])
        self.assertEqual([item.literal for item in response.exact.semantic_related], ["香島"])
        self.assertEqual([item.literal for item in response.exact.sound_only], ["香江"])
        self.assertTrue(all(reason["kind"] for group in response.exact.model_dump().values() for item in group for reason in item["reasons"]))

    def test_semantic_priority_pool_keeps_order_across_pages(self) -> None:
        rows = [
            {"char": "甲甲", "jyutping": "gaa1 gaa1", "code": "11"},
            {"char": "乙乙", "jyutping": "jat1 jat1", "code": "22"},
            {"char": "丙丙", "jyutping": "bing2 bing2", "code": "33"},
            {"char": "丁丁", "jyutping": "ding1 ding1", "code": "44"},
        ]
        pool = SimpleNamespace(
            syns=[{"char": "乙乙", "source": "manual"}],
            semantic=[{"char": "丙丙", "source": "embedding_cosine"}],
        )

        def execute(_spec, **kwargs):
            offset = kwargs["offset"]
            limit = kwargs["limit"]
            return MaskFamilySearchResult(
                items=rows[offset : offset + limit],
                total=len(rows),
            )

        Session = memory_sessionmaker()
        with Session() as db:
            db.add_all([
                Word(char=row["char"], jyutping=row["jyutping"], code=row["code"], length=2)
                for row in rows
            ])
            db.commit()
            first = plan_replacements(
                make_plan(slots=[], limit=2),
                db,
                execute=execute,
                relation_projector=lambda *_args, **_kwargs: pool,
            )
            second = plan_replacements(
                make_plan(slots=[], limit=2, offset=2),
                db,
                execute=execute,
                relation_projector=lambda *_args, **_kwargs: pool,
            )

        self.assertEqual([item.literal for item in first.exact.direct_syn], ["乙乙"])
        self.assertEqual([item.literal for item in first.exact.semantic_related], ["丙丙"])
        self.assertEqual([item.literal for item in second.exact.sound_only], ["甲甲", "丁丁"])
        self.assertEqual((first.engine_total, second.engine_total), (4, 4))

    def test_direct_only_never_falls_back_to_sound_candidates(self) -> None:
        plan = make_plan(semanticIntent="direct_only")
        response = plan_replacements(
            plan,
            object(),
            execute=lambda *_args, **_kwargs: MaskFamilySearchResult(
                items=[{"char": "香江", "jyutping": "hoeng1 gong1", "code": "33"}]
            ),
            relation_projector=lambda *_args, **_kwargs: SimpleNamespace(syns=[], semantic=[]),
        )
        self.assertEqual(response.exact.direct_syn, [])
        self.assertEqual(response.exact.sound_only, [])

    def test_unrestricted_code_keeps_direct_synonym_from_constrained_results(self) -> None:
        pool = SimpleNamespace(
            syns=[{"char": "遇救", "source": "manual"}],
            semantic=[],
        )

        def execute(spec, **_kwargs):
            items = [{"char": "遇救", "jyutping": "jyu6 gau3", "code": "24"}]
            if not spec.slots:
                items = [{"char": "一個", "jyutping": "jat1 go3", "code": "34"}]
            return MaskFamilySearchResult(items=items)

        changes = {
            "width": 2,
            "semanticIntent": "ranked",
            "semanticSeed": "獲救",
        }
        Session = memory_sessionmaker()
        with Session() as db:
            db.add(Word(char="遇救", jyutping="jyu6 gau3", code="24", length=2))
            db.commit()
            constrained = plan_replacements(
                make_plan(**changes, slots=[
                    {"pos": 0, "kind": "code_digit", "digit": "2"},
                    {"pos": 1, "kind": "code_digit", "digit": "4"},
                ]),
                db,
                execute=execute,
                relation_projector=lambda *_args, **_kwargs: pool,
            )
            unrestricted = plan_replacements(
                make_plan(**changes, slots=[]),
                db,
                execute=execute,
                relation_projector=lambda *_args, **_kwargs: pool,
            )

        self.assertIn("遇救", [item.literal for item in constrained.exact.direct_syn])
        self.assertIn("遇救", [item.literal for item in unrestricted.exact.direct_syn])

    def test_zero_results_returns_one_non_mutating_relaxation(self) -> None:
        plan = make_plan(
            width=1,
            slots=[{"pos": 0, "kind": "code_digit", "digit": "3"}],
            semanticIntent="off",
            semanticSeed=None,
        )
        before = deepcopy(plan.model_dump())

        def execute(spec, **kwargs):
            if kwargs["mode"] == "m2":
                return MaskFamilySearchResult(items=[{"char": "香", "jyutping": "hoeng1", "code": "3"}])
            return MaskFamilySearchResult(items=[])

        response = plan_replacements(plan, object(), execute=execute)
        self.assertEqual(response.relaxation.kind, "loosen_mode")
        self.assertEqual(response.relaxation.candidate_count, 1)
        self.assertEqual(plan.model_dump(), before)
        self.assertEqual(response.exact.sound_only, [])


if __name__ == "__main__":
    unittest.main()
