"""缺字型查詢執行 — 候選比對與 slot 過濾。"""

from __future__ import annotations

from typing import Any, Optional

from app.domain.lexicon.reference_reading import anchor_phoneme_options
from app.lexicon.rime_char_index import pron_rank_sort_value_for_word
from app.services.position_match.spec import MatchSpec, get_equals_span
from app.services.position_match.mask_adapter import matches_mask_literal_chars
from app.services.word_serializer import (
    get_rhyme_finals,
    get_word_jyutping,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
)
from app.utils.jyutping_codec import get_code_variants
from app.utils.word_cache import narrow_candidates_by_phoneme_anchor


def matches_equals_phoneme_span(
    word,
    ref_parts: list,
    start_pos: int,
    *,
    phoneme_anchor_only: bool,
    ref_literal: str,
    dimension: str,
) -> bool:
    """碼夾等號 span：參考詞 JSON 逐格精確比對（非 options OR）。"""
    char_text = get_word_text(word)
    if not phoneme_anchor_only and ref_literal and ref_literal not in char_text:
        return False
    field = "finals" if dimension == "final" else "initials"
    word_parts = get_rhyme_finals(word) if dimension == "final" else get_word_parts(word, field)
    if not word_parts:
        return False
    for i in range(len(ref_parts)):
        pos = start_pos + i
        if pos < len(word_parts) and i < len(ref_parts):
            if ref_parts[i] and ref_parts[i] != word_parts[pos]:
                return False
    return True


def matches_code_positions(code_str: str, required_codes: list[Optional[str]], mode: str) -> bool:
    if len(code_str) != len(required_codes):
        return False
    for idx, req_digit in enumerate(required_codes):
        if req_digit is None:
            continue
        if code_str[idx] not in set(get_code_variants(req_digit, mode)):
            return False
    return True


def matches_phoneme_at_position(
    word,
    pos: int,
    anchor: str,
    *,
    constraint: str,
    db,
) -> bool:
    if constraint == "final":
        options = anchor_phoneme_options(anchor, "final", db, allow_inject=True)
        parts = get_rhyme_finals(word)
    else:
        options = anchor_phoneme_options(anchor, "initial", db, allow_inject=True)
        from app.utils.jyutping_codec import is_standalone_nasal_syllable_token, syllable_token_at

        if is_standalone_nasal_syllable_token(syllable_token_at(get_word_jyutping(word), pos)):
            return False
        parts = get_word_parts(word, "initials")
    if not options or pos >= len(parts):
        return False
    return parts[pos] in options


def slot_constraint_matches(word, slot, db) -> bool:
    from app.services.jyutping_anchor import matches_jyutping_anchor_at_position

    if slot.kind in ("rhyme_letters", "syllable_letters", "initial_letters"):
        return matches_jyutping_anchor_at_position(
            word, slot.pos, slot.kind, str(slot.value or ""), db
        )
    return False


def _group_candidates_by_char(candidates: list) -> dict[str, list]:
    grouped: dict[str, list] = {}
    for word in candidates:
        char = get_word_text(word)
        grouped.setdefault(char, []).append(word)
    return grouped


def preferred_pronunciation_rows(rows: list) -> list:
    if not rows:
        return []
    ranked = [
        (pron_rank_sort_value_for_word(get_word_text(word), get_word_jyutping(word)), word)
        for word in rows
    ]
    best = min(rank for rank, _ in ranked)
    return [word for rank, word in ranked if rank == best]


def _word_passes_position_filters(
    word,
    *,
    width: int,
    required_codes: list[Optional[str]],
    mode: str,
    mask: str,
    db,
    anchor_pos: Optional[int],
    anchor: Optional[str],
    constraint: Optional[str],
    literal_char: Optional[str],
    slots: Optional[list] = None,
) -> bool:
    word_char = get_word_text(word)
    if len(word_char) != width:
        return False
    if mask and not matches_mask_literal_chars(word_char, mask):
        return False
    if literal_char is not None and word_char[-1] != literal_char:
        return False
    word_code_str = get_word_sort_code(word)
    word_finals = get_rhyme_finals(word)
    if not word_code_str or not word_finals:
        return False
    if any(req is not None for req in required_codes):
        if not matches_code_positions(word_code_str, required_codes, mode):
            return False
    anchor_slots = [s for s in (slots or []) if s.kind in ("final_anchor", "initial_anchor")]
    if anchor_slots:
        for slot in anchor_slots:
            constraint = "final" if slot.kind == "final_anchor" else "initial"
            if not matches_phoneme_at_position(
                word, slot.pos, slot.value, constraint=constraint, db=db,
            ):
                return False
    elif anchor_pos is not None and anchor and constraint:
        if not matches_phoneme_at_position(
            word, anchor_pos, anchor, constraint=constraint, db=db,
        ):
            return False
    for slot in slots or []:
        if slot.kind in ("rhyme_letters", "syllable_letters", "initial_letters"):
            if not slot_constraint_matches(word, slot, db):
                return False
    return True


def filter_words_by_code_and_mask(
    candidates: list,
    *,
    width: int,
    code_digits: str,
    mode: str,
    mask: str,
    db,
    anchor_pos: Optional[int] = None,
    anchor: Optional[str] = None,
    constraint: Optional[str] = None,
    literal_char: Optional[str] = None,
    slots: Optional[list] = None,
) -> list:
    required_codes: list[Optional[str]] = [None] * width
    if code_digits:
        for i, d in enumerate(code_digits):
            required_codes[i] = d
    if mask:
        for i, ch in enumerate(mask):
            if i < width and ch.isdigit():
                required_codes[i] = ch
    if slots:
        for slot in slots:
            if getattr(slot, "kind", None) == "code_digit" and slot.pos < width and slot.value is not None:
                required_codes[slot.pos] = str(slot.value)

    filtered = []
    has_code_digit_constraints = any(req is not None for req in required_codes)
    if has_code_digit_constraints:
        for _char, group in _group_candidates_by_char(candidates).items():
            for word in preferred_pronunciation_rows(group):
                if _word_passes_position_filters(
                    word,
                    width=width,
                    required_codes=required_codes,
                    mode=mode,
                    mask=mask,
                    db=db,
                    anchor_pos=anchor_pos,
                    anchor=anchor,
                    constraint=constraint,
                    literal_char=literal_char,
                    slots=slots,
                ):
                    filtered.append(word)
                    break
    else:
        for word in candidates:
            if _word_passes_position_filters(
                word,
                width=width,
                required_codes=required_codes,
                mode=mode,
                mask=mask,
                db=db,
                anchor_pos=anchor_pos,
                anchor=anchor,
                constraint=constraint,
                literal_char=literal_char,
                slots=slots,
            ):
                filtered.append(word)
    return filtered


def filter_candidates_by_match_spec(
    candidates: list,
    spec: MatchSpec,
    mode: str,
    db,
) -> list:
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
        code_digits=spec.code_prefix or "",
        mode=mode,
        mask=spec.mask or "",
        db=db,
        literal_char=literal_char,
        slots=spec.slots,
    )


def build_final_options_at_positions(
    ref_chars: str,
    start_pos: int,
    width: int,
    db,
) -> list[Optional[set[str]]]:
    target_final_options: list[Optional[set[str]]] = [None] * width
    for i, ch in enumerate(ref_chars):
        pos = start_pos + i
        if 0 <= pos < width:
            options = anchor_phoneme_options(ch, "final", db, allow_inject=True)
            if options:
                target_final_options[pos] = options
    return target_final_options


def word_matches_last_final(word, final_options: Optional[set[str]]) -> bool:
    if not final_options:
        return True
    word_finals = get_rhyme_finals(word)
    return len(word_finals) >= 2 and word_finals[-1] in final_options


def matches_final_options(word_finals: list, target_final_options: list[Optional[set[str]]]) -> bool:
    if len(word_finals) != len(target_final_options):
        return False
    for idx, options in enumerate(target_final_options):
        if not options:
            continue
        if idx >= len(word_finals) or word_finals[idx] not in options:
            return False
    return True


def matches_hybrid_ref_chars(
    word_char: str,
    word_finals: list,
    ref_chars: str,
    start_pos: int,
    target_final_options: list[Optional[set[str]]],
) -> bool:
    width = len(target_final_options)
    if len(word_char) != width or len(word_finals) != width:
        return False
    for i, ch in enumerate(ref_chars):
        pos = start_pos + i
        if pos < 0 or pos >= width:
            return False
        if word_char[pos] == ch:
            continue
        options = target_final_options[pos]
        if options and word_finals[pos] in options:
            continue
        return False
    return True


def _word_stored_phoneme_json(word: Any, field: str):
    if isinstance(word, dict):
        return word.get(field)
    return getattr(word, field, None)


def _phoneme_storage_key(word: Any, field: str) -> tuple:
    raw = _word_stored_phoneme_json(word, field)
    if isinstance(raw, list):
        return tuple(raw)
    if isinstance(raw, str) and raw:
        from app.utils.json_helpers import load_json_list

        return tuple(load_json_list(raw))
    return ()


def _phoneme_db_literal(word: Any, field: str) -> str:
    import json

    raw = _word_stored_phoneme_json(word, field)
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return json.dumps(raw, ensure_ascii=False, separators=(", ", ": "))
    return ""


def _equals_length_bucket_candidates(
    width: int,
    code_prefix: Optional[str],
    mode: str,
) -> Optional[list]:
    from app.utils.jyutping_codec import get_code_variants
    from app.utils.word_cache import get_words_for_length, is_word_cache_ready

    if not is_word_cache_ready():
        return None
    candidates = get_words_for_length(width)
    if not code_prefix:
        return candidates
    variants = set(get_code_variants(code_prefix, mode))
    return [w for w in candidates if get_word_sort_code(w) in variants]


def _equals_whole_word_matches(
    spec: MatchSpec,
    db: Any,
    mode: str,
    *,
    target: Any,
    target_parts: list,
    is_final: bool,
) -> list[Any]:
    from app.models.word import Word
    from app.services.word_db_filters import apply_code_filter, length_filter

    full_code = spec.code_prefix or ""
    target_key = tuple(target_parts)
    cached = _equals_length_bucket_candidates(spec.width, full_code or None, mode)
    storage_field = "finals" if is_final else "initials"
    target_storage_key = _phoneme_storage_key(target, storage_field)

    if cached is not None:
        pool = cached
        if target_storage_key:
            pool = [
                w
                for w in pool
                if _phoneme_storage_key(w, storage_field) == target_storage_key
            ]
        if is_final:
            return [w for w in pool if tuple(get_rhyme_finals(w)) == target_key]
        return [w for w in pool if tuple(get_word_parts(w, "initials")) == target_key]

    query = db.query(Word).filter(length_filter(spec.width))
    if full_code:
        query = apply_code_filter(query, full_code, mode)
    if is_final:
        db_literal = _phoneme_db_literal(target, "finals")
        if db_literal:
            query = query.filter(Word.finals == db_literal)
        return [
            w
            for w in query.all()
            if tuple(get_rhyme_finals(w)) == target_key
        ]
    db_literal = _phoneme_db_literal(target, "initials")
    if db_literal:
        query = query.filter(Word.initials == db_literal)
    return query.all()


def query_words_by_equals_spec(spec: MatchSpec, db: Any, mode: str = "m1") -> list[Any]:
    """等號／碼夾等號查詢：候選解析 + span 比對（ADR-0004 收斂至 filters）。"""
    from app.domain.lexicon.reference_reading import (
        equals_authoritative_row,
        suffix_aligned_ref_phoneme_parts,
    )
    from app.models.word import Word
    from app.services.word_db_filters import apply_code_filter, length_filter
    from app.utils.json_helpers import load_json_list

    if not get_equals_span(spec):
        return []

    span = get_equals_span(spec)
    assert span is not None
    is_final = span.dimension == "final"
    dimension = "final" if is_final else "initial"
    prefix_wildcard = bool(spec.extra.get("prefix_wildcard_equals"))

    if prefix_wildcard:
        target_parts = suffix_aligned_ref_phoneme_parts(
            span.ref_literal, dimension, db, allow_inject=True,
        )
        if not target_parts:
            return []
        target = None
    else:
        target = equals_authoritative_row(span.ref_literal, db, allow_inject=True)
        if not target:
            return []
        target_parts = (
            get_rhyme_finals(target)
            if is_final
            else load_json_list(target.initials)
        )

    full_code = spec.code_prefix or ""

    query = db.query(Word)
    query = apply_code_filter(query, full_code, mode)
    query = query.filter(length_filter(spec.width))

    if span.whole_word:
        return _equals_whole_word_matches(
            spec,
            db,
            mode,
            target=target,
            target_parts=target_parts,
            is_final=is_final,
        )

    if prefix_wildcard:
        cached = _equals_length_bucket_candidates(spec.width, full_code or None, mode)
        candidates = cached if cached is not None else query.all()
    else:
        candidates = query.limit(2000).all()
    return [
        word
        for word in candidates
        if matches_equals_phoneme_span(
            word,
            target_parts,
            span.start_pos,
            phoneme_anchor_only=span.phoneme_anchor_only,
            ref_literal=span.ref_literal,
            dimension=span.dimension,
        )
    ]


def filter_hybrid_ref_candidates(
    candidates: list,
    spec: MatchSpec,
    mode: str,
    db,
) -> list:
    """碼夾 hybrid 查詢：參考字韻母選項比對。"""
    if spec.hybrid_ref_chars is None or spec.hybrid_ref_pos is None:
        return candidates
    target_final_options = build_final_options_at_positions(
        spec.hybrid_ref_chars, spec.hybrid_ref_pos, spec.width, db
    )
    filtered = []
    allowed_full_codes = (
        set(get_code_variants(spec.code_prefix or "", mode)) if spec.code_prefix else set()
    )
    for word in candidates:
        word_code_str = get_word_sort_code(word)
        if spec.code_prefix and word_code_str not in allowed_full_codes:
            continue
        word_finals = get_rhyme_finals(word)
        word_char = get_word_text(word)
        if matches_hybrid_ref_chars(
            word_char, word_finals, spec.hybrid_ref_chars, spec.hybrid_ref_pos, target_final_options
        ):
            filtered.append(word)
    return filtered


def apply_match_spec(
    spec: MatchSpec,
    candidates: list,
    db: Any,
    mode: str = "m1",
) -> list[Any]:
    """MatchSpec 單一過濾管線（equals／hybrid／slot；ADR-0004 #6）。"""
    if get_equals_span(spec):
        return query_words_by_equals_spec(spec, db, mode)
    if spec.hybrid_ref_chars is not None and spec.hybrid_ref_pos is not None:
        return filter_hybrid_ref_candidates(candidates, spec, mode, db)
    return filter_candidates_by_match_spec(candidates, spec, mode, db)