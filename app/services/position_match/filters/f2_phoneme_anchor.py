"""MF-5 F2 — final_anchor / initial_anchor + partial mask options."""
from __future__ import annotations

from typing import Optional

from app.domain.lexicon.reference_reading import anchor_phoneme_options
from app.services.position_match.spec import MatchSpec
from app.services.word_serializer import (
    get_rhyme_finals,
    get_word_jyutping,
    get_word_parts,
    get_word_text,
)

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


def _contextual_phoneme_options_at_position(
    db,
    width: int,
    pos: int,
    anchor_char: str,
    dimension: str,
) -> set[str]:
    from app.models.word import Word
    from app.services.word_db_filters import length_filter
    from app.utils.word_cache import get_words_for_length, is_word_cache_ready

    options: set[str] = set()
    rows = get_words_for_length(width) if is_word_cache_ready() else None
    if rows is None:
        rows = db.query(Word).filter(length_filter(width)).all()
    for row in rows:
        text = get_word_text(row)
        if len(text) != width or text[pos] != anchor_char:
            continue
        if dimension == "final":
            parts = get_rhyme_finals(row)
        else:
            parts = get_word_parts(row, "initials")
        if parts and pos < len(parts):
            options.add(parts[pos])
    options |= anchor_phoneme_options(anchor_char, dimension, db, allow_inject=True)
    return options


def contextual_final_options_at_position(
    db,
    width: int,
    pos: int,
    anchor_char: str,
) -> set[str]:
    return _contextual_phoneme_options_at_position(
        db, width, pos, anchor_char, "final",
    )


def contextual_initial_options_at_position(
    db,
    width: int,
    pos: int,
    anchor_char: str,
) -> set[str]:
    return _contextual_phoneme_options_at_position(
        db, width, pos, anchor_char, "initial",
    )


def _partial_mask_slot_options(
    spec: MatchSpec,
    db,
    *,
    dimension: str,
) -> dict[tuple[int, str], set[str]]:
    """每個錨格選項只算一次（唔好喺逐候選詞迴圈內全庫掃描）。"""
    kind = "final_anchor" if dimension == "final" else "initial_anchor"
    ctx = (
        contextual_final_options_at_position
        if dimension == "final"
        else contextual_initial_options_at_position
    )
    out: dict[tuple[int, str], set[str]] = {}
    for slot in spec.slots:
        if slot.kind != kind:
            continue
        key = (slot.pos, slot.value)
        if key not in out:
            out[key] = ctx(db, spec.width, slot.pos, slot.value)
    return out


def word_passes_partial_rhyme_mask(
    spec: MatchSpec,
    word,
    db,
    *,
    slot_options: Optional[dict[tuple[int, str], set[str]]] = None,
) -> bool:
    text = get_word_text(word)
    if len(text) != spec.width:
        return False
    finals = get_rhyme_finals(word)
    if not finals:
        return False
    opts = slot_options or _partial_mask_slot_options(spec, db, dimension="final")
    for slot in spec.slots:
        if slot.kind != "final_anchor":
            continue
        options = opts.get((slot.pos, slot.value))
        if not options or slot.pos >= len(finals) or finals[slot.pos] not in options:
            return False
    return True


def word_passes_partial_initial_mask(
    spec: MatchSpec,
    word,
    db,
    *,
    slot_options: Optional[dict[tuple[int, str], set[str]]] = None,
) -> bool:
    text = get_word_text(word)
    if len(text) != spec.width:
        return False
    initials = get_word_parts(word, "initials")
    if not initials:
        return False
    opts = slot_options or _partial_mask_slot_options(spec, db, dimension="initial")
    for slot in spec.slots:
        if slot.kind != "initial_anchor":
            continue
        options = opts.get((slot.pos, slot.value))
        if not options or slot.pos >= len(initials) or initials[slot.pos] not in options:
            return False
    return True

