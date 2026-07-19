"""Resolve editable line slots without guessing missing Cantonese readings."""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata
from typing import Literal

from app.domain.lexicon.reference_reading import (
    equals_authoritative_row,
    select_authoritative_pronunciation_row,
)
from app.domain.lexicon.word_row import get_word_jyutping, get_word_parts
from app.models.word import Word
from app.utils.jyutping_codec import split_jyutping_parts


@dataclass(frozen=True)
class LineReadingChoice:
    jyutping: str
    code: str
    initial: str
    final: str


@dataclass(frozen=True)
class LineReadingSlot:
    surface: str
    kind: Literal["resolved", "unresolved", "punctuation"]
    choices: tuple[LineReadingChoice, ...]
    needs_choice: bool


def _is_punctuation(surface: str) -> bool:
    return bool(surface) and unicodedata.category(surface)[0] in {"P", "Z"}


def _choice(row) -> LineReadingChoice:
    jyutping = get_word_jyutping(row).strip()
    initials = get_word_parts(row, "initials")
    finals = get_word_parts(row, "finals")
    if not initials or not finals:
        parsed_initials, parsed_finals, _tones = split_jyutping_parts(jyutping)
        initials = initials or parsed_initials
        finals = finals or parsed_finals
    return LineReadingChoice(
        jyutping=jyutping,
        code=(getattr(row, "code", None) or "").strip(),
        initial=initials[0] if initials else "",
        final=finals[0] if finals else "",
    )


def _authoritative_order(rows: list) -> list:
    remaining = list(rows)
    ordered = []
    while remaining:
        selected = select_authoritative_pronunciation_row(remaining)
        if selected is None:
            break
        ordered.append(selected)
        remaining.remove(selected)
    return ordered


def _resolve_slot(surface: str, db, *, allow_inject: bool) -> LineReadingSlot:
    # The authoritative resolver owns admission/injection and pronunciation ranking.
    equals_authoritative_row(surface, db, allow_inject=allow_inject)
    rows = db.query(Word).filter(Word.char == surface).all()

    choices: list[LineReadingChoice] = []
    seen: set[tuple[str, str, str, str]] = set()
    for row in _authoritative_order(rows):
        choice = _choice(row)
        key = (choice.jyutping, choice.code, choice.initial, choice.final)
        if not choice.jyutping or key in seen:
            continue
        seen.add(key)
        choices.append(choice)

    if not choices:
        kind = "punctuation" if _is_punctuation(surface) else "unresolved"
        return LineReadingSlot(surface, kind, (), False)

    material = {(item.code, item.initial, item.final) for item in choices}
    needs_choice = len(material) > 1
    if not needs_choice:
        choices = choices[:1]
    return LineReadingSlot(surface, "resolved", tuple(choices), needs_choice)


def resolve_line_readings(surface: str, db, *, allow_inject: bool = True) -> tuple[LineReadingSlot, ...]:
    """Resolve each Unicode code point independently; unresolved slots remain editable."""
    return tuple(_resolve_slot(value, db, allow_inject=allow_inject) for value in surface)


__all__ = [
    "LineReadingChoice",
    "LineReadingSlot",
    "resolve_line_readings",
]
