"""Structured workbench candidate reasons; presentation copy stays in the client."""

from __future__ import annotations

from app.schemas.workbench_schema import CandidateReason, ReplacementPlanV1
from app.utils.jyutping_codec import normalize_02493_code


def candidate_reasons(
    plan: ReplacementPlanV1,
    code: str,
    group: str,
    *,
    relation_source: str | None = None,
) -> list[CandidateReason]:
    reasons: list[CandidateReason] = []
    for slot in plan.slots:
        if slot.kind == "code_digit":
            expected = normalize_02493_code(slot.digit or "")
            exact = slot.pos < len(code) and code[slot.pos] == expected
            reasons.append(CandidateReason(
                kind="tone_exact" if exact else "tone_loose",
                positions=[slot.pos],
            ))
        elif slot.kind == "literal_char":
            reasons.append(CandidateReason(kind="literal_match", positions=[slot.pos]))
        elif slot.kind == "final_anchor":
            reasons.append(CandidateReason(kind="same_final", positions=[slot.pos]))
        elif slot.kind == "initial_anchor":
            reasons.append(CandidateReason(kind="same_initial", positions=[slot.pos]))
        elif slot.kind == "tone_class":
            reasons.append(CandidateReason(kind="tone_exact", positions=[slot.pos]))
    if group == "direct_syn":
        reasons.append(CandidateReason(kind="direct_syn", source=relation_source))
    elif group == "semantic_related":
        reasons.append(CandidateReason(kind="semantic_related", source=relation_source))
    reasons.append(CandidateReason(kind="frequency_rank"))
    return reasons


__all__ = ["candidate_reasons"]
