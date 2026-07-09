"""
音素欄位緊湊化（CONTEXT §；ADR-0037）— S1 十進位 id + '.'；K1 字典序 vocab。
Storage: initials/finals columns hold compact strings, not JSON arrays.
"""
from __future__ import annotations

import hashlib
from typing import Iterable, List, Literal, Optional, Sequence

PhonemeDim = Literal["final", "initial"]

# K1: lexicographic freeze from production lyrics.db unique set (2026-07); id 0 = empty token.
# Unknown tokens at encode → raise (fail build-db).
FINALS_VOCAB: tuple[str, ...] = (
    "",
    "a",
    "aa",
    "aai",
    "aak",
    "aam",
    "aan",
    "aang",
    "aap",
    "aat",
    "aau",
    "ai",
    "ak",
    "am",
    "an",
    "ang",
    "ap",
    "at",
    "au",
    "e",
    "ei",
    "ek",
    "em",
    "en",
    "eng",
    "eoi",
    "eon",
    "eot",
    "ep",
    "et",
    "eu",
    "i",
    "ik",
    "iks",
    "im",
    "in",
    "ing",
    "ip",
    "it",
    "iu",
    "o",
    "oe",
    "oek",
    "oeng",
    "oet",
    "oi",
    "ok",
    "on",
    "ong",
    "op",
    "ot",
    "ou",
    "u",
    "ui",
    "uk",
    "un",
    "ung",
    "ut",
    "yu",
    "yun",
    "yut",
)

INITIALS_VOCAB: tuple[str, ...] = (
    "",
    "!",
    "!t",
    "!zh",
    "b",
    "c",
    "d",
    "f",
    "g",
    "gw",
    "h",
    "hm",
    "hng",
    "j",
    "k",
    "kw",
    "l",
    "m",
    "n",
    "ng",
    "p",
    "s",
    "t",
    "w",
    "z",
)

PHONEME_VOCAB_VERSION = "j2.v1"

_FINAL_TO_ID = {t: i for i, t in enumerate(FINALS_VOCAB)}
_INITIAL_TO_ID = {t: i for i, t in enumerate(INITIALS_VOCAB)}
_ID_TO_FINAL = {i: t for i, t in enumerate(FINALS_VOCAB)}
_ID_TO_INITIAL = {i: t for i, t in enumerate(INITIALS_VOCAB)}


def phoneme_vocab_fingerprint() -> str:
    """Stable short hash of vocab tables + version (for lexicon_meta)."""
    payload = PHONEME_VOCAB_VERSION + "\0" + "\n".join(FINALS_VOCAB) + "\0" + "\n".join(INITIALS_VOCAB)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _maps(dim: PhonemeDim) -> tuple[dict[str, int], dict[int, str]]:
    if dim == "final":
        return _FINAL_TO_ID, _ID_TO_FINAL
    return _INITIAL_TO_ID, _ID_TO_INITIAL


def encode_phoneme_list(parts: Sequence[str], dim: PhonemeDim) -> str:
    """List of tokens → S1 compact string. Empty list → \"\"."""
    if not parts:
        return ""
    to_id, _ = _maps(dim)
    ids: list[str] = []
    for p in parts:
        token = "" if p is None else str(p)
        if token not in to_id:
            raise ValueError(f"unknown {dim} phoneme token {token!r} (not in vocab {PHONEME_VOCAB_VERSION})")
        ids.append(str(to_id[token]))
    return ".".join(ids)


def decode_phoneme_field(raw: Optional[object], dim: PhonemeDim) -> List[str]:
    """
    Compact field → token list.
    Accepts already-decoded list (word_cache entries).
    M1: JSON arrays rejected (return []).
    """
    if raw is None or raw == "":
        return []
    if isinstance(raw, list):
        return [str(x) if x is not None else "" for x in raw]
    if not isinstance(raw, str):
        return []
    s = raw.strip()
    if not s:
        return []
    # M1: reject legacy JSON storage
    if s[0] == "[":
        return []
    _, id_to = _maps(dim)
    out: list[str] = []
    for part in s.split("."):
        if part == "":
            # "1..2" invalid — treat as empty token only if single empty segment from "0"?
            # S1 never emits empty segments; skip bad
            continue
        try:
            idx = int(part)
        except ValueError:
            return []
        if idx not in id_to:
            return []
        out.append(id_to[idx])
    return out


def encode_phoneme_parts_from_jyutping_lists(
    initials: Sequence[str],
    finals: Sequence[str],
) -> tuple[str, str]:
    return encode_phoneme_list(initials, "initial"), encode_phoneme_list(finals, "final")


def is_compact_phoneme_field(raw: Optional[object]) -> bool:
    if raw is None or raw == "":
        return True
    if isinstance(raw, list):
        return True
    if not isinstance(raw, str):
        return False
    s = raw.strip()
    if not s:
        return True
    if s[0] == "[":
        return False
    return all(p.isdigit() for p in s.split(".") if p != "")


def sql_finals_span_patterns(encoded_span: str, *, width: int, start_pos: int) -> list[str]:
    """
    P1: delimiter-safe equality/LIKE patterns for a consecutive finals id span.
    encoded_span e.g. '14.40.52' for three syllables.
    """
    if not encoded_span or width < 1:
        return []
    end = start_pos + encoded_span.count(".") + 1  # syllable count
    # patterns for whole-field alignment
    if start_pos == 0 and end >= width:
        return [encoded_span]
    patterns: list[str] = []
    if start_pos == 0:
        # prefix of field: span then optional more
        patterns.append(encoded_span)
        patterns.append(encoded_span + ".%")
    elif end >= width:
        # suffix
        patterns.append("%." + encoded_span)
        patterns.append(encoded_span)  # exact if whole remaining equals
    else:
        patterns.append("%." + encoded_span + ".%")
        patterns.append("%." + encoded_span)
        patterns.append(encoded_span + ".%")
    return patterns


__all__ = [
    "FINALS_VOCAB",
    "INITIALS_VOCAB",
    "PHONEME_VOCAB_VERSION",
    "PhonemeDim",
    "decode_phoneme_field",
    "encode_phoneme_list",
    "encode_phoneme_parts_from_jyutping_lists",
    "is_compact_phoneme_field",
    "phoneme_vocab_fingerprint",
    "sql_finals_span_patterns",
]
