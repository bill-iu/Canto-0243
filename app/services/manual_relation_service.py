"""創作者手動關係 — see CONTEXT § 創作者手動關係、關係補錄命令."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Set, Tuple

from sqlalchemy.orm import Session

from app.domain.relations.canonical import canonical_word_ids
from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.pool_projection import relation_chars_for_seed
from app.domain.relations.store import insert_relation_candidates
from app.domain.relations.syn_neighbors import one_hop_syn_neighbors
from app.models.word import Word, WordRelation

MANUAL_SOURCE = "manual"
MANUAL_SYN_CLUSTER_SOURCE = "manual_syn_cluster"
MANUAL_ANT_MIRROR_SOURCE = "manual_ant_mirror"
MANUAL_DIRECT_SCORE = 0.95
MANUAL_EXPAND_SCORE = 0.82

RelationType = Literal["syn", "ant"]


class ManualRelationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class ValidatedManualRelation:
    seed_char: str
    opposite_char: str
    relation_type: RelationType
    seed_id: int
    opposite_id: int
    char_to_id: Dict[str, int]


def _normalize_char(value: str) -> str:
    return (value or "").strip()


def _char_in_lexicon(db: Session, char: str) -> bool:
    return (
        db.query(Word.id).filter(Word.char == char).limit(1).first() is not None
    )


def _direct_relation_exists(
    db: Session, seed_id: int, opposite_id: int, relation_type: str
) -> bool:
    w, r = canonical_word_ids(seed_id, opposite_id)
    return (
        db.query(WordRelation.id)
        .filter(
            WordRelation.word_id == w,
            WordRelation.related_id == r,
            WordRelation.relation_type == relation_type,
        )
        .limit(1)
        .first()
        is not None
    )


def validate_manual_relation_request(
    db: Session,
    *,
    seed_char: str,
    opposite_char: str,
    relation_type: RelationType,
) -> ValidatedManualRelation:
    """關係補錄命令共用字面驗證。"""
    seed = _normalize_char(seed_char)
    opposite = _normalize_char(opposite_char)
    if relation_type not in ("syn", "ant"):
        raise ManualRelationError("invalid_relation_type", "關係類型須為近義或反義")
    if not seed or not opposite:
        raise ManualRelationError("missing_literal", "請填寫種子字面與對端字面")
    if seed == opposite:
        raise ManualRelationError("self_relation", "種子字面與對端字面不可相同")

    for label, char in (("種子字面", seed), ("對端字面", opposite)):
        if not _char_in_lexicon(db, char):
            raise ManualRelationError(
                "not_in_lexicon",
                f"{label}「{char}」未收錄於詞條庫",
            )

    char_to_id = get_char_to_primary_id(db)
    seed_id = char_to_id.get(seed)
    opposite_id = char_to_id.get(opposite)
    if not seed_id or not opposite_id:
        raise ManualRelationError("not_in_lexicon", "字面未收錄於詞條庫")

    return ValidatedManualRelation(
        seed_char=seed,
        opposite_char=opposite,
        relation_type=relation_type,
        seed_id=seed_id,
        opposite_id=opposite_id,
        char_to_id=char_to_id,
    )


def build_expand_plan(
    db: Session,
    validated: ValidatedManualRelation,
) -> frozenset[str]:
    """一跳擴展計畫：補錄與撤回共用（重算對稱）。"""
    neighbors = one_hop_syn_neighbors(
        db,
        opposite_char=validated.opposite_char,
        seed_char=validated.seed_char,
    )
    if validated.relation_type == "syn":
        blocked = relation_chars_for_seed(db, validated.seed_char, "ant")
    else:
        blocked = relation_chars_for_seed(db, validated.seed_char, "syn")
    return frozenset(ch for ch in neighbors if ch not in blocked)


def _expand_source_for(relation_type: RelationType) -> str:
    return (
        MANUAL_SYN_CLUSTER_SOURCE if relation_type == "syn" else MANUAL_ANT_MIRROR_SOURCE
    )


def _relation_candidate(
    char_to_id: Dict[str, int],
    head_char: str,
    tail_char: str,
    relation_type: str,
    *,
    source: str,
    score: float,
) -> Tuple[Tuple[int, int, str], dict] | None:
    if not head_char or not tail_char or head_char == tail_char:
        return None
    head_id = char_to_id.get(head_char)
    tail_id = char_to_id.get(tail_char)
    if not head_id or not tail_id:
        return None
    w, r = canonical_word_ids(head_id, tail_id)
    if w == r:
        return None
    key = (w, r, relation_type)
    return key, {
        "word_id": w,
        "related_id": r,
        "relation_type": relation_type,
        "score": score,
        "source": source[:32],
    }


def _build_create_candidates(
    validated: ValidatedManualRelation,
    plan: frozenset[str],
) -> Tuple[Tuple[int, int, str], dict, Dict[Tuple[int, int, str], dict]]:
    direct_key, direct_row = _relation_candidate(
        validated.char_to_id,
        validated.seed_char,
        validated.opposite_char,
        validated.relation_type,
        source=MANUAL_SOURCE,
        score=MANUAL_DIRECT_SCORE,
    )
    if direct_key is None or direct_row is None:
        raise ManualRelationError("not_in_lexicon", "字面未收錄於詞條庫")

    expand_source = _expand_source_for(validated.relation_type)
    expand_candidates: Dict[Tuple[int, int, str], dict] = {}
    for neighbor in sorted(plan):
        item = _relation_candidate(
            validated.char_to_id,
            validated.seed_char,
            neighbor,
            validated.relation_type,
            source=expand_source,
            score=MANUAL_EXPAND_SCORE,
        )
        if item is not None:
            expand_candidates[item[0]] = item[1]

    return direct_key, direct_row, expand_candidates


def _apply_create(
    db: Session,
    validated: ValidatedManualRelation,
    plan: frozenset[str],
) -> dict:
    if _direct_relation_exists(
        db,
        validated.seed_id,
        validated.opposite_id,
        validated.relation_type,
    ):
        raise ManualRelationError("already_exists", "此關係已存在")

    direct_key, direct_row, expand_candidates = _build_create_candidates(validated, plan)

    try:
        direct_inserted, _direct_skipped = insert_relation_candidates(
            db,
            {direct_key: direct_row},
            dedupe_existing=True,
            batch_size=500,
            commit=False,
        )
        if direct_inserted != 1:
            raise ManualRelationError("already_exists", "此關係已存在")

        expand_inserted, expand_skipped = insert_relation_candidates(
            db,
            expand_candidates,
            dedupe_existing=True,
            batch_size=500,
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "direct": direct_inserted,
        "expand": expand_inserted,
        "skipped": expand_skipped,
    }


def _delete_relation_row(
    db: Session,
    word_id: int,
    related_id: int,
    relation_type: str,
    *,
    source: str,
) -> int:
    w, r = canonical_word_ids(word_id, related_id)
    rows = (
        db.query(WordRelation)
        .filter(
            WordRelation.word_id == w,
            WordRelation.related_id == r,
            WordRelation.relation_type == relation_type,
            WordRelation.source == source,
        )
        .all()
    )
    for row in rows:
        db.delete(row)
    return len(rows)


def _manual_direct_exists(db: Session, validated: ValidatedManualRelation) -> bool:
    w, r = canonical_word_ids(validated.seed_id, validated.opposite_id)
    return (
        db.query(WordRelation.id)
        .filter(
            WordRelation.word_id == w,
            WordRelation.related_id == r,
            WordRelation.relation_type == validated.relation_type,
            WordRelation.source == MANUAL_SOURCE,
        )
        .limit(1)
        .first()
        is not None
    )


def _apply_revoke(db: Session, validated: ValidatedManualRelation, plan: frozenset[str]) -> dict:
    if not _manual_direct_exists(db, validated):
        raise ManualRelationError("not_found", "找不到可撤回的創作者手動關係")

    expand_source = _expand_source_for(validated.relation_type)
    expand_removed = 0
    try:
        for neighbor in sorted(plan):
            neighbor_id = validated.char_to_id.get(neighbor)
            if not neighbor_id:
                continue
            expand_removed += _delete_relation_row(
                db,
                validated.seed_id,
                neighbor_id,
                validated.relation_type,
                source=expand_source,
            )

        direct_removed = _delete_relation_row(
            db,
            validated.seed_id,
            validated.opposite_id,
            validated.relation_type,
            source=MANUAL_SOURCE,
        )
        if direct_removed != 1:
            raise ManualRelationError("not_found", "找不到可撤回的創作者手動關係")

        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"direct": direct_removed, "expand": expand_removed}


def create_creator_manual_relation(
    db: Session,
    *,
    seed_char: str,
    opposite_char: str,
    relation_type: RelationType,
) -> dict:
    validated = validate_manual_relation_request(
        db,
        seed_char=seed_char,
        opposite_char=opposite_char,
        relation_type=relation_type,
    )
    plan = build_expand_plan(db, validated)
    return _apply_create(db, validated, plan)


def revoke_creator_manual_relation(
    db: Session,
    *,
    seed_char: str,
    opposite_char: str,
    relation_type: RelationType,
) -> dict:
    validated = validate_manual_relation_request(
        db,
        seed_char=seed_char,
        opposite_char=opposite_char,
        relation_type=relation_type,
    )
    plan = build_expand_plan(db, validated)
    return _apply_revoke(db, validated, plan)


MANUAL_EXPAND_SOURCES = frozenset({MANUAL_SYN_CLUSTER_SOURCE, MANUAL_ANT_MIRROR_SOURCE})


def prune_conflicting_manual_expansions(
    db: Session,
    *,
    seed_char: str | None = None,
) -> dict:
    """Remove manual expand rows that contradict seed's opposite relation type."""
    from sqlalchemy.orm import aliased

    w_head = aliased(Word)
    w_tail = aliased(Word)
    q = (
        db.query(WordRelation, w_head.char, w_tail.char)
        .join(w_head, WordRelation.word_id == w_head.id)
        .join(w_tail, WordRelation.related_id == w_tail.id)
        .filter(WordRelation.source.in_(MANUAL_EXPAND_SOURCES))
    )
    seed = seed_char.strip() if seed_char else None
    if seed:
        q = q.filter((w_head.char == seed) | (w_tail.char == seed))

    removed = 0
    for rel, head, tail in q.all():
        if rel.relation_type == "syn":
            opposite_kind = "ant"
        elif rel.relation_type == "ant":
            opposite_kind = "syn"
        else:
            continue

        pairs = [(head, tail), (tail, head)]
        if seed:
            pairs = [
                (candidate_seed, other)
                for candidate_seed, other in pairs
                if candidate_seed == seed
            ]
            if not pairs:
                continue

        if not any(
            other in relation_chars_for_seed(db, candidate_seed, opposite_kind)
            for candidate_seed, other in pairs
        ):
            continue
        db.delete(rel)
        removed += 1
    if removed:
        db.commit()
    return {"removed": removed}


__all__ = [
    "ManualRelationError",
    "ValidatedManualRelation",
    "validate_manual_relation_request",
    "build_expand_plan",
    "create_creator_manual_relation",
    "prune_conflicting_manual_expansions",
    "revoke_creator_manual_relation",
]
