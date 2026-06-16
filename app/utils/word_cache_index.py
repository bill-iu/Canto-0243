"""詞庫快取索引 — CONTEXT § 詞庫快取索引；倒排索引與查詢取向量候選。"""
from __future__ import annotations

from collections import defaultdict
from typing import Callable

from app.utils.json_helpers import load_json_list

_COLD_BUILD_MIN_ROWS = 500

_length_buckets: dict = {}
_char_meta: dict = {}
_bucket_entry_index: dict = {}
_literal_index: dict = {}
_final_index: dict = {}
_initial_index: dict = {}
_code_digit_index: dict = {}


def _entry_key(entry: dict) -> tuple:
    return (entry.get("char") or "", entry.get("code") or "", entry.get("jyutping") or "")


def is_populated() -> bool:
    return bool(_length_buckets)


def export_state() -> dict:
    return {
        "length_buckets": _length_buckets,
        "bucket_entry_index": _bucket_entry_index,
        "char_meta": _char_meta,
        "literal_index": _literal_index,
        "final_index": _final_index,
        "initial_index": _initial_index,
        "code_digit_index": _code_digit_index,
    }


def install_state(state: dict) -> None:
    global _length_buckets, _char_meta, _bucket_entry_index
    global _literal_index, _final_index, _initial_index, _code_digit_index
    _length_buckets = state["length_buckets"]
    _bucket_entry_index = state["bucket_entry_index"]
    _char_meta = state["char_meta"]
    _literal_index = state["literal_index"]
    _final_index = state["final_index"]
    _initial_index = state["initial_index"]
    _code_digit_index = state["code_digit_index"]


def reset_index_for_tests() -> None:
    global _length_buckets, _char_meta, _bucket_entry_index
    global _literal_index, _final_index, _initial_index, _code_digit_index
    _length_buckets = {}
    _char_meta = {}
    _bucket_entry_index = {}
    _literal_index = {}
    _final_index = {}
    _initial_index = {}
    _code_digit_index = {}


def _row_field(obj, key: str, default=""):
    try:
        if hasattr(obj, "get"):
            return obj.get(key, default)
        return getattr(obj, key, default)
    except Exception:
        try:
            return obj[key] if key in obj else default
        except Exception:
            return default


def _row_to_entry(r) -> dict | None:
    if isinstance(r, (list, tuple)):
        if len(r) < 6:
            return None
        char, code, jyut, finals_raw, inits_raw, length = r[0], r[1], r[2], r[3], r[4], r[5]
    else:
        char = _row_field(r, "char", None)
        code = _row_field(r, "code", "")
        jyut = _row_field(r, "jyutping", "")
        finals_raw = _row_field(r, "finals", None)
        inits_raw = _row_field(r, "initials", None)
        length = _row_field(r, "length", None)
        if length is None and char:
            length = len(char)
    if not char:
        return None
    finals = load_json_list(finals_raw)
    inits = load_json_list(inits_raw)
    length = int(length) if length is not None else len(char or "")
    return {
        "char": char,
        "code": code or "",
        "jyutping": jyut or "",
        "finals": finals,
        "initials": inits,
        "length": length,
    }


def _append_to_indexes_into(
    literal_index: dict,
    final_index: dict,
    initial_index: dict,
    code_digit_index: dict,
    length: int,
    bucket_idx: int,
    entry: dict,
) -> None:
    char = entry.get("char") or ""
    for pos, ch in enumerate(char):
        literal_index[(length, pos, ch)].append(bucket_idx)
    for pos, final in enumerate(entry.get("finals") or []):
        if final:
            final_index[(length, pos, final)].append(bucket_idx)
    for pos, initial in enumerate(entry.get("initials") or []):
        if initial:
            initial_index[(length, pos, initial)].append(bucket_idx)
    code = entry.get("code") or ""
    for pos, digit in enumerate(code):
        if pos < length and digit.isdigit():
            code_digit_index[(length, pos, digit)].append(bucket_idx)


def _store_entry_into(
    length_buckets: dict,
    bucket_entry_index: dict,
    literal_index: dict,
    final_index: dict,
    initial_index: dict,
    code_digit_index: dict,
    entry: dict,
) -> bool:
    length = int(entry["length"])
    bucket = length_buckets.setdefault(length, [])
    idx_map = bucket_entry_index.setdefault(length, {})
    key = _entry_key(entry)
    if key in idx_map:
        bucket[idx_map[key]] = entry
        return False
    bucket_idx = len(bucket)
    idx_map[key] = bucket_idx
    bucket.append(entry)
    _append_to_indexes_into(
        literal_index, final_index, initial_index, code_digit_index, length, bucket_idx, entry
    )
    return True


def _upsert_char_meta(char_meta: dict, entry: dict) -> None:
    key = _entry_key(entry)
    ch = entry["char"]
    metas = char_meta.setdefault(ch, [])
    for meta_idx, existing in enumerate(metas):
        if _entry_key(existing) == key:
            metas[meta_idx] = entry
            return
    metas.append(entry)


def _populate_cold_build(
    row_list: list,
    *,
    report_every: int,
    on_progress: Callable[[float], None] | None,
) -> int:
    global _length_buckets, _char_meta, _bucket_entry_index
    global _literal_index, _final_index, _initial_index, _code_digit_index

    length_buckets: dict = {}
    bucket_entry_index: dict = {}
    char_meta: dict = {}
    literal_index: dict = defaultdict(list)
    final_index: dict = defaultdict(list)
    initial_index: dict = defaultdict(list)
    code_digit_index: dict = defaultdict(list)
    total = len(row_list)
    added = 0

    def _row_progress(done: int) -> None:
        if total <= 0 or on_progress is None:
            return
        on_progress(min(1.0, done / total))

    for row_idx, r in enumerate(row_list):
        entry = _row_to_entry(r)
        if not entry:
            continue
        is_new = _store_entry_into(
            length_buckets,
            bucket_entry_index,
            literal_index,
            final_index,
            initial_index,
            code_digit_index,
            entry,
        )
        if is_new:
            char_meta.setdefault(entry["char"], []).append(entry)
        else:
            _upsert_char_meta(char_meta, entry)
        added += 1
        if report_every and row_idx > 0 and row_idx % report_every == 0:
            _row_progress(row_idx)
    if total:
        _row_progress(total)

    _length_buckets = length_buckets
    _bucket_entry_index = bucket_entry_index
    _char_meta = char_meta
    _literal_index = dict(literal_index)
    _final_index = dict(final_index)
    _initial_index = dict(initial_index)
    _code_digit_index = dict(code_digit_index)
    return added


def _append_to_indexes(length: int, bucket_idx: int, entry: dict) -> None:
    char = entry.get("char") or ""
    for pos, ch in enumerate(char):
        _literal_index.setdefault((length, pos, ch), []).append(bucket_idx)
    finals = entry.get("finals") or []
    for pos, final in enumerate(finals):
        if final:
            _final_index.setdefault((length, pos, final), []).append(bucket_idx)
    initials = entry.get("initials") or []
    for pos, initial in enumerate(initials):
        if initial:
            _initial_index.setdefault((length, pos, initial), []).append(bucket_idx)
    code = entry.get("code") or ""
    for pos, digit in enumerate(code):
        if pos < length and digit.isdigit():
            _code_digit_index.setdefault((length, pos, digit), []).append(bucket_idx)


def _store_entry(entry: dict, *, index_new: bool, bucket_idx: int | None = None) -> None:
    length = int(entry["length"])
    bucket = _length_buckets.setdefault(length, [])
    idx_map = _bucket_entry_index.setdefault(length, {})
    key = _entry_key(entry)
    if key in idx_map:
        bucket[idx_map[key]] = entry
        return
    if bucket_idx is None:
        bucket_idx = len(bucket)
    idx_map[key] = bucket_idx
    if bucket_idx == len(bucket):
        bucket.append(entry)
    else:
        bucket[bucket_idx] = entry
    if index_new:
        _append_to_indexes(length, bucket_idx, entry)


def populate_from_rows(
    rows: list,
    *,
    on_progress: Callable[[float], None] | None = None,
) -> int:
    row_list = list(rows or [])
    total = len(row_list)
    report_every = max(2000, total // 40) if total else 0

    if total >= _COLD_BUILD_MIN_ROWS and not _length_buckets:
        return _populate_cold_build(row_list, report_every=report_every, on_progress=on_progress)

    added = 0

    def _row_progress(done: int) -> None:
        if total <= 0 or on_progress is None:
            return
        on_progress(min(1.0, done / total))

    for row_idx, r in enumerate(row_list):
        entry = _row_to_entry(r)
        if not entry:
            continue
        key = _entry_key(entry)
        length = entry["length"]
        idx_map = _bucket_entry_index.setdefault(length, {})
        is_new = key not in idx_map
        _store_entry(entry, index_new=is_new)
        _upsert_char_meta(_char_meta, entry)
        added += 1
        if report_every and row_idx > 0 and row_idx % report_every == 0:
            _row_progress(row_idx)
    if total:
        _row_progress(total)
    return added


def get_words_for_length(n: int) -> list:
    return _length_buckets.get(int(n) if n else 0, []) or []


def _wildcard_char(ch: str) -> bool:
    return len(ch) == 1 and ch in "_?%"


def _candidate_entry_key(word) -> tuple:
    if isinstance(word, dict):
        return _entry_key(word)
    return (
        getattr(word, "char", None) or "",
        getattr(word, "code", None) or "",
        getattr(word, "jyutping", None) or "",
    )


def get_phoneme_index_candidates(
    length: int,
    pos: int,
    anchor: str,
    constraint: str,
    db,
) -> list:
    if not is_populated() or not anchor:
        return []
    from app.domain.lexicon.reference_reading import anchor_phoneme_options

    options = anchor_phoneme_options(
        anchor,
        "final" if constraint == "final" else "initial",
        db,
        allow_inject=False,
    )
    if not options:
        return []
    bucket = _length_buckets.get(int(length)) or []
    if not bucket:
        return []
    index_map = _final_index if constraint == "final" else _initial_index
    allowed_idx: set[int] = set()
    for opt in options:
        allowed_idx |= set(index_map.get((length, pos, opt), ()))
    return [bucket[i] for i in sorted(allowed_idx)]


def get_mask_index_candidates(length: int, mask: str) -> list | None:
    if not is_populated() or not mask:
        return None
    bucket = _length_buckets.get(int(length))
    if not bucket:
        return []

    index_sets: list[set[int]] = []
    for pos, ch in enumerate(mask):
        if _wildcard_char(ch):
            continue
        if ch.isdigit():
            idx_set = set(_code_digit_index.get((length, pos, ch), ()))
        else:
            idx_set = set(_literal_index.get((length, pos, ch), ()))
        if not idx_set:
            return []
        index_sets.append(idx_set)

    if not index_sets:
        return list(bucket)

    matched = index_sets[0]
    for other in index_sets[1:]:
        matched &= other
    return [bucket[i] for i in sorted(matched)]


def narrow_candidates_by_phoneme_anchor(
    candidates: list,
    length: int,
    pos: int,
    anchor: str,
    constraint: str,
    db,
) -> list:
    phoneme_rows = get_phoneme_index_candidates(length, pos, anchor, constraint, db)
    if not phoneme_rows:
        return []
    if not candidates:
        return []
    if len(phoneme_rows) <= len(candidates):
        allowed_keys = {_candidate_entry_key(w) for w in phoneme_rows}
        return [w for w in candidates if _candidate_entry_key(w) in allowed_keys]
    allowed_keys = {_candidate_entry_key(w) for w in candidates}
    return [w for w in phoneme_rows if _candidate_entry_key(w) in allowed_keys]


def get_char_meta(ch: str):
    if not ch:
        return None
    metas = _char_meta.get(ch) or []
    return metas[0] if metas else None


def get_char_metas(ch: str) -> list:
    if not ch:
        return []
    return list(_char_meta.get(ch) or [])


def update_entry(
    char: str,
    code: str = "",
    jyutping: str = "",
    finals: object = None,
    initials: object = None,
    length: int | None = None,
) -> None:
    if not char:
        return
    f = load_json_list(finals)
    i = load_json_list(initials)
    ln = int(length) if length is not None else len(char)
    entry = {
        "char": char,
        "code": code or "",
        "jyutping": jyutping or "",
        "finals": f,
        "initials": i,
        "length": ln,
    }
    key = _entry_key(entry)
    idx_map = _bucket_entry_index.setdefault(ln, {})
    is_new = key not in idx_map
    _store_entry(entry, index_new=is_new)
    _upsert_char_meta(_char_meta, entry)


def get_stats() -> dict:
    lens = sorted(_length_buckets.keys())
    total = sum(len(v) for v in _length_buckets.values())
    return {
        "total_entries": total,
        "lengths": lens,
        "max_length": max(lens) if lens else 0,
        "meta_size": len(_char_meta),
        "indexed_literals": len(_literal_index),
    }
