"""Apply declarative lexicon corrections to merged candidates before persist."""
from __future__ import annotations

from app.lexicon.candidates import LexiconCandidate
from app.lexicon.corrections import LexiconCorrection
from app.utils.jyutping_codec import get_0243_code


def _matches(candidate: LexiconCandidate, corr: LexiconCorrection) -> bool:
    if candidate.char != corr.char or candidate.jyutping != corr.old_jyutping:
        return False
    if corr.old_code and candidate.code != corr.old_code:
        return False
    return True


def _find_index(candidates: list[LexiconCandidate], corr: LexiconCorrection) -> int:
    for i, c in enumerate(candidates):
        if _matches(c, corr):
            return i
    return -1


def apply_lexicon_overlay(
    candidates: list[LexiconCandidate],
    corrections: list[LexiconCorrection],
) -> list[LexiconCandidate]:
    out = list(candidates)
    for corr in corrections:
        i = _find_index(out, corr)
        if i < 0:
            continue
        cur = out[i]
        if corr.action == "delete":
            out.pop(i)
            continue
        if corr.action == "set_code":
            if not corr.old_code:
                raise ValueError(f"set_code requires old_code for {corr.char!r}")
            if not corr.value:
                raise ValueError(f"set_code requires value for {corr.char!r}")
            out[i] = cur.with_reading(cur.jyutping, corr.value)
            continue
        if corr.action == "set_jyutping":
            if not corr.value:
                raise ValueError(f"set_jyutping requires value for {corr.char!r}")
            code = get_0243_code(corr.value) or ""
            out[i] = cur.with_reading(corr.value, code)
            continue
        raise ValueError(f"unknown action {corr.action!r}")
    return out
