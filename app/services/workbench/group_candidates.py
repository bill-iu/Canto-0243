"""rows → CandidateGroups (L2) — mirror of client group-candidates.ts."""

from __future__ import annotations

from app.schemas.workbench_schema import CandidateGroups, ReplacementPlanV1, WorkbenchCandidate
from app.services.workbench.candidate_rank import candidate_sort_key, relation_index
from app.services.workbench.candidate_reason import candidate_reasons


def group_candidates(plan: ReplacementPlanV1, rows: list[dict], pool) -> CandidateGroups:
    direct = relation_index(pool.syns) if pool else {}
    semantic = relation_index(pool.semantic) if pool else {}
    groups: dict[str, list[WorkbenchCandidate]] = {
        "direct_syn": [],
        "semantic_related": [],
        "sound_only": [],
    }
    for row_rank, row in enumerate(rows):
        literal = str(row.get("char") or row.get("literal") or "")
        if not literal:
            continue
        if literal in direct:
            group = "direct_syn"
            source_rank, source = direct[literal]
        elif literal in semantic:
            group = "semantic_related"
            source_rank, source = semantic[literal]
        else:
            group = "sound_only"
            source_rank, source = row_rank, None

        if plan.semantic_intent == "direct_only" and group != "direct_syn":
            continue
        if plan.semantic_intent == "off":
            group, source_rank, source = "sound_only", row_rank, None

        code = str(row.get("code") or "")
        groups[group].append(WorkbenchCandidate(
            literal=literal,
            jyutping=str(row.get("jyutping") or ""),
            code=code,
            group=group,
            reasons=candidate_reasons(plan, code, group, relation_source=source),
            source_rank=source_rank,
        ))
    for values in groups.values():
        values.sort(key=candidate_sort_key)
    return CandidateGroups(**groups)


def group_literals(groups: CandidateGroups) -> dict[str, list[str]]:
    return {
        "direct_syn": [c.literal for c in groups.direct_syn],
        "semantic_related": [c.literal for c in groups.semantic_related],
        "sound_only": [c.literal for c in groups.sound_only],
    }


def candidate_count_for_pool(plan: ReplacementPlanV1, rows: list[dict], pool) -> int:
    if plan.semantic_intent != "direct_only":
        return len(rows)
    direct = relation_index(pool.syns) if pool else {}
    return sum(1 for row in rows if str(row.get("char") or "") in direct)


__all__ = ["candidate_count_for_pool", "group_candidates", "group_literals"]
