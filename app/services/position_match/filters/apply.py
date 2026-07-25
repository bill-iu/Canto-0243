"""MatchSpec apply pipeline — F1–F5 orchestration (public apply_match_spec)."""
from __future__ import annotations

from typing import Any

from typing import Optional

from app.services.position_match.filters.f1_slot_code import filter_words_by_code_and_mask
from app.services.position_match.filters.f2_phoneme_anchor import (
    word_passes_partial_initial_mask,
    word_passes_partial_rhyme_mask,
    _partial_mask_slot_options,
)
from app.services.position_match.filters.f3_letters import slot_constraint_matches
from app.services.position_match.filters.f4_equals import query_words_by_equals_spec
from app.services.position_match.mask_adapter import (
    has_code_digit_constraints,
    required_codes_from_spec,
)
from app.services.position_match.spec import MatchSpec, get_equals_span
from app.services.word_serializer import (
    get_rhyme_finals,
    get_word_jyutping,
    get_word_sort_code,
    get_word_text,
)
from app.utils.word_cache import narrow_candidates_by_phoneme_anchor

def filter_candidates_by_match_spec(
    candidates: list,
    spec: MatchSpec,
    mode: str,
    db,
) -> list:
    if (
        spec.extra.get("workbench_full_bucket_scan")
        and not spec.slots
        and spec.mask
        and set(spec.mask) <= {"?", "_", "%"}
    ):
        return [
            word
            for word in candidates
            if len(get_word_text(word)) == spec.width
            and bool(get_word_sort_code(word))
            and bool(get_word_jyutping(word) or get_rhyme_finals(word))
        ]
    if spec.extra.get("partial_rhyme_mask"):
        slot_options = _partial_mask_slot_options(spec, db, dimension="final")
        candidates = [
            w for w in candidates
            if word_passes_partial_rhyme_mask(spec, w, db, slot_options=slot_options)
        ]
        return candidates
    if spec.extra.get("partial_initial_mask"):
        slot_options = _partial_mask_slot_options(spec, db, dimension="initial")
        candidates = [
            w for w in candidates
            if word_passes_partial_initial_mask(spec, w, db, slot_options=slot_options)
        ]
        return candidates

    literal_char: Optional[str] = None
    for slot in spec.slots:
        if slot.kind == "literal_char" and slot.pos == spec.width - 1:
            literal_char = slot.value
    for slot in spec.slots:
        if slot.kind in ("final_anchor", "initial_anchor"):
            constraint = "final" if slot.kind == "final_anchor" else "initial"
            candidates = narrow_candidates_by_phoneme_anchor(
                candidates, spec.width, slot.pos, slot.value, constraint, db,
            )
    for slot in spec.slots:
        if slot.kind in ("rhyme_letters", "syllable_letters", "initial_letters"):
            candidates = [w for w in candidates if slot_constraint_matches(w, slot, db)]
    return filter_words_by_code_and_mask(
        candidates,
        width=spec.width,
        code_digits="",  # PR-A: constraints only via required_codes (slots/mask)
        mode=mode,
        mask=spec.mask or "",
        db=db,
        literal_char=literal_char,
        slots=spec.slots,
        required_codes=required_codes_from_spec(spec),
    )

def apply_match_spec(
    spec: MatchSpec,
    candidates: list,
    db: Any,
    mode: str = "m1",
) -> list[Any]:
    """MatchSpec 單一過濾管線（equals／slot；ADR-0004 #6）。"""
    if get_equals_span(spec):
        candidates = query_words_by_equals_spec(spec, db, mode)
        if has_code_digit_constraints(spec):
            candidates = filter_words_by_code_and_mask(
                candidates,
                width=spec.width,
                code_digits="",
                mode=mode,
                mask=spec.mask or "",
                db=db,
                literal_char=None,
                slots=spec.slots,
                required_codes=required_codes_from_spec(spec),
            )
        return candidates
    filtered = filter_candidates_by_match_spec(candidates, spec, mode, db)
    if spec.compound_kind == "doubled_syllable":
        from app.domain.relations.compound_doubled_syllable import (
            row_has_uniform_syllable_letters,
        )

        filtered = [
            w
            for w in filtered
            if row_has_uniform_syllable_letters(get_word_jyutping(w), spec.width)
        ]
    return filtered
