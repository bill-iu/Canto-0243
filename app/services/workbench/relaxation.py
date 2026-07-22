"""Deterministic one-change relaxation enumeration."""

from __future__ import annotations

from app.schemas.workbench_schema import ReplacementPlanV1


def relaxation_variants(plan: ReplacementPlanV1):
    if plan.semantic_intent == "direct_only":
        yield (
            "semantic:direct_only:ranked",
            "semantic_ranked",
            [],
            "direct_only",
            "ranked",
            plan.model_copy(update={"semantic_intent": "ranked"}),
        )
    for kind, relaxation_kind in (
        ("final_anchor", "remove_final"),
        ("initial_anchor", "remove_initial"),
        ("code_digit", "remove_code"),
    ):
        for slot in plan.slots:
            if slot.kind != kind:
                continue
            slots = [item for item in plan.slots if item is not slot]
            yield (
                f"{kind}:{slot.pos}:remove",
                relaxation_kind,
                [slot.pos],
                kind,
                None,
                plan.model_copy(update={"slots": slots}),
            )
    next_mode = {"m3": "m2", "m2": "m1"}.get(plan.mode)
    if next_mode:
        yield (
            f"mode:{plan.mode}:{next_mode}",
            "loosen_mode",
            [],
            plan.mode,
            next_mode,
            plan.model_copy(update={"mode": next_mode}),
        )


def relaxation_ids(plan: ReplacementPlanV1) -> list[str]:
    """Ordered relaxation ids for L3 parity with TS."""
    return [item_id for item_id, *_rest in relaxation_variants(plan)]


__all__ = ["relaxation_ids", "relaxation_variants"]
