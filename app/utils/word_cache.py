from app.utils.json_helpers import load_json_list

_length_buckets: dict = {}
_char_meta: dict = {}
_bucket_entry_index: dict = {}


def _entry_key(entry: dict) -> tuple:
    return (entry.get("char") or "", entry.get("code") or "", entry.get("jyutping") or "")


def populate_word_cache_from_rows(rows: list) -> int:
    global _length_buckets, _char_meta, _bucket_entry_index
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
        bucket = _length_buckets.setdefault(length, [])
        idx_map = _bucket_entry_index.setdefault(length, {})
        key = _entry_key(entry)
        if key in idx_map:
            bucket[idx_map[key]] = entry
        else:
            idx_map[key] = len(bucket)
            bucket.append(entry)
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
    bucket = _length_buckets.setdefault(ln, [])
    idx_map = _bucket_entry_index.setdefault(ln, {})
    key = _entry_key(entry)
    if key in idx_map:
        bucket[idx_map[key]] = entry
    else:
        idx_map[key] = len(bucket)
        bucket.append(entry)
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
    }


def reset_word_cache_for_tests() -> None:
    """Clear in-memory cache (tests only)."""
    global _length_buckets, _char_meta, _bucket_entry_index
    _length_buckets = {}
    _char_meta = {}
    _bucket_entry_index = {}
