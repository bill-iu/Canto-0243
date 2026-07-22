"""Thin orchestrator (L4): MatchSpec execute → group → optional relaxation probe."""

from __future__ import annotations

from app.domain.relation_pool import project_relation_pool
from app.models.word import Word
from app.schemas.workbench_schema import (
    CandidateGroups,
    RelaxationSuggestion,
    ReplacementPlanV1,
    WorkbenchCandidateResponse,
)
from app.services.position_match.engine import execute_match_spec
from app.services.workbench.build_match_spec import build_match_spec
from app.services.workbench.group_candidates import candidate_count_for_pool, group_candidates
from app.services.workbench.limits import WORKBENCH_LEXICON_MAX_WORD_LEN
from app.services.workbench.relaxation import relaxation_variants
from app.services.word_serializer import serialize_word

# Re-export for existing imports
__all__ = ["build_match_spec", "plan_replacements"]


def _execute(plan: ReplacementPlanV1, db, execute) -> tuple[list[dict], int]:
    result = execute(
        build_match_spec(plan),
        code=None,
        mode=plan.mode,
        limit=plan.limit,
        offset=plan.offset,
        db=db,
    )
    return result.items, int(result.total or len(result.items))


def _load_relation_rows(db, width: int, pool) -> list[dict]:
    literals = {
        str(item.get("char") or "")
        for item in [*pool.syns, *pool.semantic]
        if item.get("char")
    }
    if not literals:
        return []
    words = (
        db.query(Word)
        .filter(Word.length == width, Word.char.in_(literals))
        .order_by(Word.char, Word.code, Word.jyutping)
        .all()
    )
    return [serialize_word(word) for word in words]


def _prepend_distinct(rows: list[dict], priority_rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for row in [*priority_rows, *rows]:
        key = tuple(str(row.get(field) or "") for field in ("char", "jyutping", "code"))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def plan_replacements(
    plan: ReplacementPlanV1,
    db,
    *,
    execute=execute_match_spec,
    relation_projector=project_relation_pool,
) -> WorkbenchCandidateResponse:
    """Return options and trade-offs; never mutate the draft or apply a candidate."""
    # ADR-0069: span wider than observed lexicon max word → structural empty, skip engine.
    if plan.width > WORKBENCH_LEXICON_MAX_WORD_LEN:
        empty = CandidateGroups(direct_syn=[], semantic_related=[], sound_only=[])
        return WorkbenchCandidateResponse(
            selection_version=plan.selection_version,
            exact=empty,
            total=0,
            engine_total=0,
            relaxation=None,
        )

    pool = None
    if plan.semantic_intent != "off" and plan.semantic_seed:
        pool = relation_projector(db, plan.semantic_seed)

    rows, total = _execute(plan, db, execute)
    if pool and not plan.slots and plan.offset == 0:
        rows = _prepend_distinct(rows, _load_relation_rows(db, plan.width, pool))
    exact = group_candidates(plan, rows, pool)
    has_exact = any((exact.direct_syn, exact.semantic_related, exact.sound_only))
    suggestion = None
    if plan.offset == 0 and not has_exact:
        for item_id, kind, positions, from_value, to_value, variant in relaxation_variants(plan):
            variant_rows, variant_total = _execute(variant, db, execute)
            count = (
                candidate_count_for_pool(variant, variant_rows, pool)
                if variant.semantic_intent == "direct_only"
                else variant_total
            )
            if count < 1:
                continue
            suggestion = RelaxationSuggestion(
                id=item_id,
                kind=kind,
                positions=positions,
                from_value=from_value,
                to_value=to_value,
                candidate_count=count,
                plan=variant,
            )
            break

    return WorkbenchCandidateResponse(
        selection_version=plan.selection_version,
        exact=exact,
        total=total,
        engine_total=total,
        relaxation=suggestion,
    )
