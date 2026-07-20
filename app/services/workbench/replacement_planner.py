"""Plan user-authored slot constraints through the existing PositionMatch engine."""

from __future__ import annotations

from app.domain.relations.pool_projection import project_relation_pool
from app.schemas.workbench_schema import (
    CandidateGroups,
    RelaxationSuggestion,
    ReplacementPlanV1,
    WorkbenchCandidate,
    WorkbenchCandidateResponse,
)
from app.services.position_match.engine import execute_match_spec
from app.services.position_match.spec import EqualsSpan, MatchSpec, SlotConstraint, attach_equals_span
from app.services.workbench.candidate_rank import candidate_sort_key, relation_index
from app.services.workbench.candidate_reason import candidate_reasons
from app.services.workbench.relaxation import relaxation_variants


def build_match_spec(plan: ReplacementPlanV1) -> MatchSpec:
    mask = ["?"] * plan.width
    slots: list[SlotConstraint] = []
    for item in plan.slots:
        value = {
            "code_digit": item.digit,
            "literal_char": item.literal,
            "final_anchor": item.ref,
            "initial_anchor": item.ref,
            "tone_class": item.tone_class,
        }[item.kind]
        slots.append(SlotConstraint(pos=item.pos, kind=item.kind, value=value))
        if item.kind == "literal_char" and item.literal:
            mask[item.pos] = item.literal
    spec = MatchSpec(width=plan.width, slots=slots, mask="".join(mask))
    for kind, dimension in (("final_anchor", "final"), ("initial_anchor", "initial")):
        anchor_items = sorted(
            (item for item in plan.slots if item.kind == kind),
            key=lambda item: item.pos,
        )
        anchors = sorted((slot for slot in slots if slot.kind == kind), key=lambda slot: slot.pos)
        positions = [slot.pos for slot in anchors]
        if (
            len(anchors) < 2
            or not all(item.ref_jyutping for item in anchor_items)
            or positions != list(range(positions[0], positions[-1] + 1))
        ):
            continue
        spec.slots = [slot for slot in slots if slot.kind != kind]
        attach_equals_span(spec, EqualsSpan(
            ref_literal="".join(str(slot.value or "") for slot in anchors),
            ref_jyutping=" ".join(item.ref_jyutping or "" for item in anchor_items),
            start_pos=positions[0],
            dimension=dimension,
            phoneme_anchor_only=True,
            whole_word=positions[0] == 0 and len(positions) == plan.width,
        ))
        if positions[0] > 0 and positions[-1] == plan.width - 1:
            spec.extra["prefix_wildcard_equals"] = True
        break
    return spec


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


def _group_candidates(plan: ReplacementPlanV1, rows: list[dict], pool) -> CandidateGroups:
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


def _candidate_count(plan: ReplacementPlanV1, rows: list[dict], pool) -> int:
    if plan.semantic_intent != "direct_only":
        return len(rows)
    direct = relation_index(pool.syns) if pool else {}
    return sum(1 for row in rows if str(row.get("char") or "") in direct)


def plan_replacements(
    plan: ReplacementPlanV1,
    db,
    *,
    execute=execute_match_spec,
    relation_projector=project_relation_pool,
) -> WorkbenchCandidateResponse:
    """Return options and trade-offs; never mutate the draft or apply a candidate."""
    pool = None
    if plan.semantic_intent != "off" and plan.semantic_seed:
        pool = relation_projector(db, plan.semantic_seed)

    rows, total = _execute(plan, db, execute)
    exact = _group_candidates(plan, rows, pool)
    has_exact = any((exact.direct_syn, exact.semantic_related, exact.sound_only))
    suggestion = None
    if plan.offset == 0 and not has_exact:
        for item_id, kind, positions, from_value, to_value, variant in relaxation_variants(plan):
            variant_rows, variant_total = _execute(variant, db, execute)
            count = (
                _candidate_count(variant, variant_rows, pool)
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
        relaxation=suggestion,
    )


__all__ = ["build_match_spec", "plan_replacements"]
