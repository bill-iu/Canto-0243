"""Thin orchestrator (L4): MatchSpec execute → group → optional relaxation probe."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from app.domain.relation_pool import project_relation_pool
from app.models.word import Word
from app.schemas.workbench_schema import (
    RelaxationSuggestion,
    ReplacementPlanV1,
    WorkbenchCandidateResponse,
)
from app.services.position_match.engine import execute_canonical_match_spec
from app.services.workbench.build_match_spec import build_match_spec, compile_replacement_plan
from app.services.workbench.group_candidates import candidate_count_for_pool, group_candidates
from app.services.workbench.limits import WORKBENCH_LEXICON_MAX_WORD_LEN
from app.services.workbench.relaxation import relaxation_variants
from app.services.word_serializer import serialize_word

CandidateHandle: TypeAlias = str


@dataclass(frozen=True, slots=True)
class ReplacementSnapshot:
    candidates: tuple[CandidateHandle, ...]
    pool: object | None
    relaxation: RelaxationSuggestion | None


def _execute(plan: ReplacementPlanV1, db, execute) -> tuple[list[dict], int]:
    from app.domain.lexicon.rhyme_profile_context import rhyme_profile_scope

    profile = getattr(plan, "rhyme_profile", None) or "exact"
    with rhyme_profile_scope(profile):
        canonical = compile_replacement_plan(plan)
        result = execute(
            canonical,
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
    seen: set[str] = set()
    for row in [*priority_rows, *rows]:
        key = str(row.get("char") or row.get("literal") or "")
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _matching_relation_rows(rows: list[dict], pool) -> list[dict]:
    """Project relation priority from rows that already passed MatchSpec."""
    by_literal: dict[str, dict] = {}
    for row in rows:
        literal = str(row.get("char") or row.get("literal") or "")
        if literal and literal not in by_literal:
            by_literal[literal] = row
    ordered = [*pool.syns, *pool.semantic]
    return [
        by_literal[literal]
        for item in ordered
        if (literal := str(item.get("char") or "")) in by_literal
    ]


def _compact_rows(rows: list[dict]) -> tuple[CandidateHandle, ...]:
    return tuple(
        "\0".join((
            str(row.get("char") or row.get("literal") or ""),
            str(row.get("jyutping") or ""),
            str(row.get("code") or ""),
        ))
        for row in rows
        if row.get("char") or row.get("literal")
    )


def _materialize_rows(handles: tuple[CandidateHandle, ...]) -> list[dict]:
    rows = []
    for item in handles:
        literal, jyutping, code = item.split("\0", 2)
        rows.append({"char": literal, "jyutping": jyutping, "code": code})
    return rows


def _canonical_page(
    plan: ReplacementPlanV1,
    db,
    execute,
    pool,
) -> tuple[list[dict], int]:
    """Merge relation priority with the same-width pool before paging."""
    if not pool:
        return _execute(plan, db, execute)
    if plan.slots:
        rows, total = _execute(plan, db, execute)
        priority_rows = _matching_relation_rows(rows, pool)
        return _prepend_distinct(rows, priority_rows), total
    priority_rows = _load_relation_rows(db, plan.width, pool)
    if not priority_rows:
        return _execute(plan, db, execute)
    expanded_limit = plan.offset + plan.limit + len(priority_rows)
    expanded = plan.model_copy(update={"limit": expanded_limit, "offset": 0})
    rows, total = _execute(expanded, db, execute)
    canonical = _prepend_distinct(rows, priority_rows)
    return canonical[plan.offset : plan.offset + plan.limit], total


def build_replacement_snapshot(
    plan: ReplacementPlanV1,
    db,
    *,
    execute=execute_canonical_match_spec,
    relation_projector=project_relation_pool,
) -> ReplacementSnapshot:
    """Build one immutable canonical pool before paging or POS projection."""
    # ADR-0069: span wider than observed lexicon max word → structural empty, skip engine.
    if plan.width > WORKBENCH_LEXICON_MAX_WORD_LEN:
        return ReplacementSnapshot(candidates=(), pool=None, relaxation=None)

    pool = None
    if plan.semantic_intent != "off" and plan.semantic_seed:
        pool = relation_projector(db, plan.semantic_seed)

    full_plan = plan.model_copy(update={"limit": 1_000_000, "offset": 0})
    rows, _total = _canonical_page(full_plan, db, execute, pool)
    handles = _compact_rows(rows)
    has_exact = bool(handles)
    if plan.semantic_intent == "direct_only":
        has_exact = candidate_count_for_pool(plan, rows, pool) > 0
    suggestion = None
    if not has_exact:
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

    return ReplacementSnapshot(
        candidates=handles,
        pool=pool,
        relaxation=suggestion,
    )


def page_replacement_snapshot(
    plan: ReplacementPlanV1,
    snapshot: ReplacementSnapshot,
) -> WorkbenchCandidateResponse:
    """Materialize one transport page from a completed snapshot."""
    page = snapshot.candidates[plan.offset : plan.offset + plan.limit]
    rows = _materialize_rows(page)
    exact = group_candidates(plan, rows, snapshot.pool)
    total = len(snapshot.candidates)
    relaxation = snapshot.relaxation
    if relaxation is not None:
        relaxation = relaxation.model_copy(update={
            "plan": relaxation.plan.model_copy(
                update={"selection_version": plan.selection_version}
            )
        })

    return WorkbenchCandidateResponse(
        selection_version=plan.selection_version,
        exact=exact,
        total=total,
        engine_total=total,
        relaxation=relaxation if plan.offset == 0 else None,
    )


def plan_replacements(
    plan: ReplacementPlanV1,
    db,
    *,
    execute=execute_canonical_match_spec,
    relation_projector=project_relation_pool,
) -> WorkbenchCandidateResponse:
    """Stateless compatibility entry; adapters retain build_replacement_snapshot."""
    snapshot = build_replacement_snapshot(
        plan,
        db,
        execute=execute,
        relation_projector=relation_projector,
    )
    return page_replacement_snapshot(plan, snapshot)


__all__ = [
    "CandidateHandle",
    "ReplacementSnapshot",
    "build_match_spec",
    "build_replacement_snapshot",
    "page_replacement_snapshot",
    "plan_replacements",
]
