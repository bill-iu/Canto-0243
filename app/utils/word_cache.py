from __future__ import annotations

import threading

from app.utils.json_helpers import load_json_list

_length_buckets: dict = {}
_char_meta: dict = {}
_bucket_entry_index: dict = {}
_literal_index: dict = {}
_final_index: dict = {}
_initial_index: dict = {}
_code_digit_index: dict = {}

_preload_lock = threading.Lock()
_preload_start_lock = threading.Lock()
_preload_thread_started = False
_preload_state = {
    "status": "pending",
    "progress": 0.0,
    "error": None,
}


def _entry_key(entry: dict) -> tuple:
    return (entry.get("char") or "", entry.get("code") or "", entry.get("jyutping") or "")


def _set_preload_status(*, status: str | None = None, progress: float | None = None, error: str | None = None) -> None:
    with _preload_lock:
        if status is not None:
            _preload_state["status"] = status
        if progress is not None:
            _preload_state["progress"] = progress
        if error is not None:
            _preload_state["error"] = error


def set_preload_progress(progress: float) -> None:
    _set_preload_status(progress=progress)


def begin_preload() -> None:
    _set_preload_status(status="loading", progress=0.0, error=None)


def complete_preload() -> None:
    _set_preload_status(status="ready", progress=1.0, error=None)


def fail_preload(message: str) -> None:
    _set_preload_status(status="failed", error=message)


def is_word_cache_ready() -> bool:
    with _preload_lock:
        return _preload_state["status"] == "ready" and bool(_length_buckets)


def get_preload_snapshot() -> dict:
    with _preload_lock:
        status = _preload_state["status"]
        return {
            "ready": status == "ready" and bool(_length_buckets),
            "status": status,
            "progress": float(_preload_state["progress"]),
            "error": _preload_state["error"],
        }


def start_word_cache_preload_background() -> None:
    """Start word-cache preload in the current process (uvicorn worker / lifespan)."""
    global _preload_thread_started
    with _preload_start_lock:
        with _preload_lock:
            if _preload_thread_started or _preload_state["status"] in ("loading", "ready"):
                return
        _preload_thread_started = True

    def _preload_word_cache() -> None:
        from app.database import SessionLocal
        from app.models.word import Word

        begin_preload()
        try:
            db = SessionLocal()
            try:
                set_preload_progress(0.15)
                rows = (
                    db.query(
                        Word.char,
                        Word.code,
                        Word.jyutping,
                        Word.finals,
                        Word.initials,
                        Word.length,
                    )
                    .filter(Word.length <= 10)
                    .all()
                )
            finally:
                db.close()

            set_preload_progress(0.55)
            populate_word_cache_from_rows(rows)
            complete_preload()
        except Exception as e:
            fail_preload(str(e))
            print(
                "[word_cache] Word meta cache preload failed "
                "(mask/hybrid fall back to DB .all() + json per row): "
                f"{e}"
            )

    threading.Thread(target=_preload_word_cache, daemon=True).start()


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


def populate_word_cache_from_rows(rows: list) -> int:
    global _length_buckets, _char_meta, _bucket_entry_index
    global _literal_index, _final_index, _initial_index, _code_digit_index
    added = 0
    for r in rows or []:
        if isinstance(r, (list, tuple)):
            char, code, jyut, finals_raw, inits_raw, length = r[0], r[1], r[2], r[3], r[4], r[5]
        else:
            def _g(obj, k, default=""):
                try:
                    if hasattr(obj, "get"):
                        return obj.get(k, default)
                    return getattr(obj, k, default)
                except Exception:
                    try:
                        return obj[k] if k in obj else default
                    except Exception:
                        return default

            char = _g(r, "char", None)
            code = _g(r, "code", "")
            jyut = _g(r, "jyutping", "")
            finals_raw = _g(r, "finals", None)
            inits_raw = _g(r, "initials", None)
            length = _g(r, "length", None)
            if length is None and char:
                length = len(char)
        if not char:
            continue
        finals = load_json_list(finals_raw)
        inits = load_json_list(inits_raw)
        length = int(length) if length is not None else len(char or "")
        entry = {
            "char": char,
            "code": code or "",
            "jyutping": jyut or "",
            "finals": finals,
            "initials": inits,
            "length": length,
        }
        key = _entry_key(entry)
        idx_map = _bucket_entry_index.setdefault(length, {})
        is_new = key not in idx_map
        _store_entry(entry, index_new=is_new)
        metas = _char_meta.setdefault(char, [])
        for idx, existing in enumerate(metas):
            if _entry_key(existing) == key:
                metas[idx] = entry
                break
        else:
            metas.append(entry)
        added += 1
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


def narrow_candidates_by_phoneme_anchor(
    candidates: list,
    length: int,
    pos: int,
    anchor: str,
    constraint: str,
    db,
) -> list:
    """Intersect candidates with (length, pos, final|initial) inverted index."""
    if not is_word_cache_ready():
        return candidates
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


def get_phoneme_index_candidates(
    length: int,
    pos: int,
    anchor: str,
    constraint: str,
    db,
) -> list:
    """Direct lookup: all bucket rows matching anchor phoneme options at pos."""
    if not is_word_cache_ready() or not anchor:
        return []
    from app.services.phoneme_lookup import final_options_for_char, initial_options_for_char

    options = (
        final_options_for_char(anchor, db)
        if constraint == "final"
        else initial_options_for_char(anchor, db)
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
    """Narrow length bucket via literal / code-digit inverted indexes (same pass as populate)."""
    if not is_word_cache_ready() or not mask:
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


def get_char_meta(ch: str):
    if not ch:
        return None
    metas = _char_meta.get(ch) or []
    return metas[0] if metas else None


def get_char_metas(ch: str) -> list:
    if not ch:
        return []
    return list(_char_meta.get(ch) or [])


def update_word_in_cache(char: str, code: str = "", jyutping: str = "", finals: object = None, initials: object = None, length: int = None):
    global _length_buckets, _char_meta, _bucket_entry_index
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
    metas = _char_meta.setdefault(char, [])
    for idx, existing in enumerate(metas):
        if _entry_key(existing) == key:
            metas[idx] = entry
            break
    else:
        metas.append(entry)


def get_word_cache_stats() -> dict:
    lens = sorted(_length_buckets.keys())
    total = sum(len(v) for v in _length_buckets.values())
    return {
        "total_entries": total,
        "lengths": lens,
        "max_length": max(lens) if lens else 0,
        "meta_size": len(_char_meta),
        "indexed_literals": len(_literal_index),
    }


def reset_word_cache_for_tests() -> None:
    """Clear in-memory cache (tests only)."""
    global _length_buckets, _char_meta, _bucket_entry_index
    global _literal_index, _final_index, _initial_index, _code_digit_index
    global _preload_thread_started
    _length_buckets = {}
    _char_meta = {}
    _bucket_entry_index = {}
    _literal_index = {}
    _final_index = {}
    _initial_index = {}
    _code_digit_index = {}
    _preload_thread_started = False
    with _preload_lock:
        _preload_state["status"] = "pending"
        _preload_state["progress"] = 0.0
        _preload_state["error"] = None
