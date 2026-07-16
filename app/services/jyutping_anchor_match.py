"""粵拼錨：缺字家族內比對與 MatchSpec 建構（CONTEXT § 粵拼錨）。"""
from __future__ import annotations

from functools import lru_cache

from app.services.jyutping_anchor_parse import STANDALONE_NG, normalize_rhyme_letters
from app.services.jyutping_match import _parse_syllable_token, parse_word_jyutping
from app.services.word_serializer import get_rhyme_finals, get_word_jyutping, get_word_parts

from app.utils.jyutping_codec import (
    STANDALONE_NASAL_FINALS,
    is_standalone_nasal_syllable_token,
    rhyme_final_index_keys_per_position,
    syllable_token_at,
)


def syllable_matches_rhyme_fragment(syl_letters: str, fragment: str) -> bool:
    from app.utils.jyutping_codec import split_jyutping

    fragment = normalize_rhyme_letters(fragment)
    syl_letters = syl_letters.lower()
    if fragment == STANDALONE_NG:
        return syl_letters in ("m", "ng")
    if len(fragment) == 1:
        from app.utils.jyutping_codec import split_jyutping_parts

        _ini, arr, _t = split_jyutping_parts(syl_letters)
        return bool(arr) and str(arr[0]) == fragment
    return syl_letters == fragment or syl_letters.endswith(fragment)


@lru_cache(maxsize=256)
def rhyme_letter_final_options(letters: str) -> frozenset[str]:
    """從 rime 預設讀音推導韻母片段對應嘅 finals 集合；空集表示無效錨。"""
    from app.lexicon.rime_char_index import _entries_by_char, ensure_rime_char_loaded
    from app.utils.jyutping_codec import split_jyutping

    letters = normalize_rhyme_letters(letters)
    if letters == STANDALONE_NG:
        return frozenset(STANDALONE_NASAL_FINALS)
    ensure_rime_char_loaded()
    finals: set[str] = set()
    for entries in _entries_by_char.values():
        for entry in entries:
            token = entry.jyutping.split()[0]
            syl = _parse_syllable_token(token)
            if not syl or not syllable_matches_rhyme_fragment(syl.letters, letters):
                continue
            if is_standalone_nasal_syllable_token(token):
                finals |= set(STANDALONE_NASAL_FINALS)
                continue
            from app.utils.jyutping_codec import split_jyutping_parts

            _ini, arr, _t = split_jyutping_parts(token)
            if not arr:
                continue
            if arr:
                finals.add(str(arr[0]))
    return frozenset(finals)


def rhyme_letters_resolve_ok(letters: str) -> bool:
    return bool(rhyme_letter_final_options(letters))


def matches_rhyme_letters_at_position(word, pos: int, letters: str, db) -> bool:
    fragment = normalize_rhyme_letters(letters)
    if fragment == STANDALONE_NG:
        keys = rhyme_final_index_keys_per_position(get_word_jyutping(word) or "")
        if pos < len(keys) and keys[pos] & STANDALONE_NASAL_FINALS:
            return True
    options = rhyme_letter_final_options(letters)
    if not options:
        return False
    parts = get_rhyme_finals(word)
    if pos >= len(parts):
        return False
    if parts[pos] in options:
        return True
    jyut = get_word_jyutping(word)
    syls = parse_word_jyutping(jyut)
    if pos < len(syls) and syllable_matches_rhyme_fragment(syls[pos].letters, letters):
        return True
    return False


def matches_syllable_letters_at_position(word, pos: int, letters: str, db) -> bool:
    syls = parse_word_jyutping(get_word_jyutping(word))
    if pos >= len(syls):
        return False
    return syls[pos].letters == letters.lower()


def matches_initial_letters_at_position(word, pos: int, letter: str, db) -> bool:
    jyut = get_word_jyutping(word)
    if is_standalone_nasal_syllable_token(syllable_token_at(jyut, pos)):
        return False
    parts = get_word_parts(word, "initials")
    return pos < len(parts) and parts[pos] == letter.lower()


def matches_jyutping_anchor_at_position(
    word,
    pos: int,
    kind: str,
    value: str,
    db,
) -> bool:
    if kind == "rhyme_letters":
        return matches_rhyme_letters_at_position(word, pos, value, db)
    if kind == "syllable_letters":
        return matches_syllable_letters_at_position(word, pos, value, db)
    if kind == "initial_letters":
        return matches_initial_letters_at_position(word, pos, value, db)
    return False


def _apply_jyutping_anchor_code_slots(spec, parsed) -> None:
    from app.services.position_match import SlotConstraint
    from app.services.position_match.mask_adapter import append_code_digit_slots

    if parsed.code_slots:
        for pos, digit in parsed.code_slots:
            spec.slots.append(SlotConstraint(pos=pos, kind="code_digit", value=digit))
    elif parsed.code_prefix and parsed.width == len(parsed.code_prefix):
        append_code_digit_slots(spec, parsed.code_prefix)


def build_jyutping_dual_match_specs(parsed) -> tuple:
    """歧義粵拼錨 → 聲母維與韻母維 MatchSpec（ADR-0009）。"""
    from app.services.position_match import MatchSpec, SlotConstraint

    def _base():
        spec = MatchSpec(width=parsed.width)
        spec.mask = "?" * parsed.width
        _apply_jyutping_anchor_code_slots(spec, parsed)
        return spec

    initial = _base()
    initial.slots.append(
        SlotConstraint(
            pos=parsed.anchor_pos,
            kind="initial_letters",
            value=(parsed.dual_initial_value or parsed.anchor_value),
        )
    )
    final = _base()
    final.slots.append(
        SlotConstraint(
            pos=parsed.anchor_pos,
            kind="rhyme_letters",
            value=parsed.anchor_value,
        )
    )
    return initial, final


def to_match_spec(parsed):
    """ParsedQuery → MatchSpec for JYUTPING_ANCHOR（含 dual carrier）。"""
    from app.services.position_match import MatchSpec, SlotConstraint
    from app.services.query_types import JyutpingAnchorQuery, QueryKind

    if not isinstance(parsed, JyutpingAnchorQuery) or parsed.kind != QueryKind.JYUTPING_ANCHOR:
        return None
    if parsed.dual_phoneme:
        initial, final = build_jyutping_dual_match_specs(parsed)
        carrier = MatchSpec(width=parsed.width)
        _apply_jyutping_anchor_code_slots(carrier, parsed)
        carrier.extra["dual_phoneme"] = True
        carrier.extra["dual_initial_spec"] = initial
        carrier.extra["dual_final_spec"] = final
        return carrier
    spec = MatchSpec(width=parsed.width)
    spec.mask = "?" * parsed.width
    spec.slots.append(
        SlotConstraint(
            pos=parsed.anchor_pos,
            kind=parsed.anchor_kind,
            value=parsed.anchor_value,
        )
    )
    _apply_jyutping_anchor_code_slots(spec, parsed)
    return spec
