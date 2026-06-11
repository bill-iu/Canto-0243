from __future__ import annotations

import json
import re
from typing import Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.word import Word
from app.schemas.word_schema import WordCreate, WordRead
from utils import (
    get_0243_code,
    get_code_variants,
    split_jyutping,
    # get_text_embedding / cosine_similarity 已從頂層移除（redesign：避免任何意外觸發模型載入）。
    # 如需在極少數遺留 semantic re-rank 路徑使用，請在函數內部做：
    #   from utils import get_text_embedding, cosine_similarity
    #   並先檢查 utils.get_text_embedding.is_ready()
    load_json_list,
    get_words_for_length,
    get_char_meta,
    get_char_metas,
)

# Back-compat alias for the many internal _load_json_list(...) calls throughout this file
_load_json_list = load_json_list
from collections import defaultdict

# === Naming Convention (enforced) ===
# 禁止使用 "hanzi"。處理粵語字符相關邏輯時必須使用 "canto" 或 "chars"。
# 詳見 README.md「命名慣例」小節與 WORKLOG.md 最新條目。
# Never introduce identifiers or functions named with "hanzi". Use "canto" or "chars".
# (Review cleanup: explanatory mentions of "hanzi" in comments kept only for history; all logic paths use canto/chars.)

WILDCARD_CHARS = frozenset("_?%")
CODE_TAIL_MIDDLE = "\u00b7"  # ·

CODE_TAIL_RE = re.compile(rf"^(\d+){re.escape(CODE_TAIL_MIDDLE)}(.+)$")
AT_TAIL_RE = re.compile(r"^(\d+)@([一-龥])$")
SLOT_CHARS_RE = r"[0-9_?%]"

RELATION_LOOKUP_RE = re.compile(r"^(\d*)([~!])([\u4e00-\u9fff]+)$")
COMPOUND_ANT_RE = re.compile(r"^(\d*)!!([\u4e00-\u9fff])?$")


def _is_wildcard_char(ch: str) -> bool:
    return len(ch) == 1 and ch in WILDCARD_CHARS


def _parse_mask_query(mask: str) -> tuple[int, list[Optional[str]], list[tuple[int, str]]]:
    """Split mask into length, per-position code digits, and literal canto positions."""
    expected_len = len(mask)
    required_codes: list[Optional[str]] = [None] * expected_len
    literal_positions: list[tuple[int, str]] = []
    for idx, ch in enumerate(mask):
        if _is_wildcard_char(ch):
            continue
        if ch.isdigit():
            required_codes[idx] = ch
            continue
        literal_positions.append((idx, ch))
    return expected_len, required_codes, literal_positions


def _mask_char_glob_pattern(mask: str) -> str:
    """Build SQLite GLOB for Word.char: wildcard/digit slots -> ?, literals unchanged."""
    return "".join(
        "?" if (_is_wildcard_char(ch) or ch.isdigit()) else ch
        for ch in mask
    )


def _matches_mask_literal_chars(word_char: str, mask: str) -> bool:
    """True when every non-wildcard, non-digit mask slot equals the word character."""
    if len(word_char) != len(mask):
        return False
    for idx, ch in enumerate(mask):
        if _is_wildcard_char(ch) or ch.isdigit():
            continue
        if word_char[idx] != ch:
            return False
    return True


def _looks_like_mask_query(q: str) -> bool:
    """True when q uses position mask syntax (digits / canto / wildcards)."""
    if not q or CODE_TAIL_MIDDLE in q or "@" in q:
        return False
    if _parse_rhyme_anchor_query(q):
        return False
    if not re.match(r"^[0-9_?%一-龥]+$", q):
        return False
    has_wild = any(_is_wildcard_char(c) for c in q)
    has_digit = any(c.isdigit() for c in q)
    has_canto = any(not c.isdigit() and not _is_wildcard_char(c) for c in q)
    return has_wild or (has_digit and has_canto)


def _initial_options_for_char(ch: str, db) -> set[str]:
    options: set[str] = set()
    for meta in get_char_metas(ch):
        initials = meta.get("initials") or []
        if initials:
            options.add(initials[0])
    if options:
        return options
    rows = db.query(Word).filter(Word.char == ch).all()
    if not rows:
        rows = _ensure_word_in_db(db, ch)
    for row in rows:
        initials = _load_json_list(getattr(row, "initials", None))
        if initials:
            options.add(initials[0])
        _sync_word_to_cache(row)
    return options


def _is_framed_equals_query(q: str) -> bool:
    """Legacy framed equals: 香港=, 2=我3, 23就= — not query-level rhyme anchors."""
    if CODE_TAIL_MIDDLE in q or "@" in q:
        return False
    match = re.match(r"^(\d*)(=)?([一-龥]+)(=)?(\d*)$", q)
    if not match:
        return False
    target = match.group(3) or ""
    if not target:
        return False
    left_code = match.group(1) or ""
    right_code = match.group(5) or ""
    right_equal = bool(match.group(4))
    inner_equal = bool(match.group(2))
    if right_equal and len(target) >= 2:
        return True
    if right_equal and left_code and len(target) == 1:
        return True
    if inner_equal and left_code and right_code:
        return True
    return False


def _parse_rhyme_anchor_query(q: str) -> Optional[dict]:
    """Query-level rhyme anchor: 香=? / ?就= / =香? / ?=就 (no ·)."""
    if not q or CODE_TAIL_MIDDLE in q or "@" in q or _is_framed_equals_query(q):
        return None

    m = re.match(rf"^({SLOT_CHARS_RE}+)([一-龥])=$", q)
    if m:
        slots, anchor = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "final",
            "anchor_pos": width - 1,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }

    m = re.match(rf"^([一-龥])=({SLOT_CHARS_RE}+)$", q)
    if m:
        anchor, slots = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "final",
            "anchor_pos": 0,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }

    m = re.match(rf"^=([一-龥])({SLOT_CHARS_RE}+)$", q)
    if m:
        anchor, slots = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "initial",
            "anchor_pos": 0,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }

    m = re.match(rf"^({SLOT_CHARS_RE}+)=([一-龥])$", q)
    if m:
        slots, anchor = m.group(1), m.group(2)
        width = len(slots) + 1
        return {
            "constraint": "initial",
            "anchor_pos": width - 1,
            "anchor": anchor,
            "slots": slots,
            "width": width,
        }
    return None


def _parse_code_tail_query(q: str) -> Optional[dict]:
    if CODE_TAIL_MIDDLE not in q:
        return None
    m = CODE_TAIL_RE.match(q)
    if not m:
        return None
    code_digits = m.group(1)
    tail = m.group(2)
    width = len(code_digits) + 1

    m2 = re.match(r"^([一-龥])=$", tail)
    if m2:
        return {
            "code_digits": code_digits,
            "width": width,
            "constraint": "final",
            "anchor": m2.group(1),
            "anchor_pos": width - 1,
        }

    m2 = re.match(r"^=([一-龥])$", tail)
    if m2:
        return {
            "code_digits": code_digits,
            "width": width,
            "constraint": "initial",
            "anchor": m2.group(1),
            "anchor_pos": width - 1,
        }

    m2 = re.match(r"^([一-龥])$", tail)
    if m2:
        return {
            "code_digits": code_digits,
            "width": width,
            "constraint": "literal",
            "anchor": m2.group(1),
            "anchor_pos": width - 1,
        }
    return None


def _parse_at_tail_query(q: str) -> Optional[dict]:
    m = AT_TAIL_RE.match(q)
    if not m:
        return None
    return {
        "code_digits": m.group(1),
        "literal_char": m.group(2),
        "width": len(m.group(1)),
    }


def _build_mask_from_slots(slots: str, width: int, anchor_pos: int) -> str:
    """Build a literal-mask string with anchor position as wildcard."""
    chars = ["?"] * width
    if anchor_pos == 0:
        for i, ch in enumerate(slots, start=1):
            chars[i] = ch
    else:
        for i, ch in enumerate(slots):
            chars[i] = ch
    return "".join(chars)


def _matches_phoneme_at_position(
    word,
    pos: int,
    anchor: str,
    *,
    constraint: str,
    db,
) -> bool:
    if constraint == "final":
        options = _final_options_for_char(anchor, db)
        parts = _get_word_parts(word, "finals")
    else:
        options = _initial_options_for_char(anchor, db)
        parts = _get_word_parts(word, "initials")
    if not options or pos >= len(parts):
        return False
    return parts[pos] in options


def _filter_words_by_code_and_mask(
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
) -> list:
    required_codes: list[Optional[str]] = [None] * width
    if code_digits:
        for i, d in enumerate(code_digits):
            required_codes[i] = d

    filtered = []
    for word in candidates:
        word_char = _get_word_text(word)
        if len(word_char) != width:
            continue
        if mask and not _matches_mask_literal_chars(word_char, mask):
            continue
        if literal_char is not None and word_char[-1] != literal_char:
            continue
        word_code_str = _get_word_sort_code(word)
        word_finals = _get_word_parts(word, "finals")
        if not word_code_str or not word_finals:
            continue
        if not _matches_code_positions(word_code_str, required_codes, mode):
            continue
        if anchor_pos is not None and anchor and constraint:
            if not _matches_phoneme_at_position(
                word, anchor_pos, anchor, constraint=constraint, db=db,
            ):
                continue
        filtered.append(word)
    return filtered


def _get_length_candidates(db, width: int, mask: str):
    candidates = get_words_for_length(width)
    if candidates:
        return [w for w in candidates if _matches_mask_literal_chars(_get_word_text(w), mask)], True
    glob_pat = _mask_char_glob_pattern(mask)
    query = db.query(Word).filter(
        _length_filter(width),
        Word.char.op("GLOB")(glob_pat),
    )
    return query.order_by(Word.char, Word.jyutping).all(), False


def _handle_rhyme_anchor_query(parsed: dict, mode: str, limit: int, offset: int, db):
    width = parsed["width"]
    mask = _build_mask_from_slots(parsed["slots"], width, parsed["anchor_pos"])
    candidates, _ = _get_length_candidates(db, width, mask)
    filtered = _filter_words_by_code_and_mask(
        candidates,
        width=width,
        code_digits="",
        mode=mode,
        mask=mask,
        db=db,
        anchor_pos=parsed["anchor_pos"],
        anchor=parsed["anchor"],
        constraint=parsed["constraint"],
    )
    filtered.sort(key=lambda w: (_get_word_text(w), _get_word_jyutping(w)))
    return _serialize_page(filtered, offset, limit)


def _handle_code_tail_query(parsed: dict, mode: str, limit: int, offset: int, db):
    width = parsed["width"]
    code_digits = parsed["code_digits"]
    anchor_pos = parsed["anchor_pos"]
    constraint = parsed["constraint"]
    anchor = parsed["anchor"]

    if constraint == "literal":
        mask = _build_mask_from_slots("", width, anchor_pos)
        mask = mask[:anchor_pos] + anchor
        literal_char = anchor
        phoneme = None
    else:
        mask = _build_mask_from_slots("", width, anchor_pos)
        literal_char = None
        phoneme = constraint

    candidates, _ = _get_length_candidates(db, width, mask)
    filtered = _filter_words_by_code_and_mask(
        candidates,
        width=width,
        code_digits=code_digits,
        mode=mode,
        mask=mask,
        db=db,
        anchor_pos=anchor_pos if phoneme else None,
        anchor=anchor if phoneme else None,
        constraint=phoneme,
        literal_char=literal_char,
    )
    filtered.sort(key=lambda w: (_get_word_text(w), _get_word_jyutping(w)))
    return _serialize_page(filtered, offset, limit)


def _handle_at_tail_query(parsed: dict, mode: str, limit: int, offset: int, db):
    width = parsed["width"]
    code_digits = parsed["code_digits"]
    literal = parsed["literal_char"]
    mask = "?" * (width - 1) + literal
    candidates, _ = _get_length_candidates(db, width, mask)
    filtered = _filter_words_by_code_and_mask(
        candidates,
        width=width,
        code_digits=code_digits,
        mode=mode,
        mask=mask,
        db=db,
        literal_char=literal,
    )
    filtered.sort(key=lambda w: (_get_word_text(w), _get_word_jyutping(w)))
    return _serialize_page(filtered, offset, limit)


def _length_filter(length: int):
    """Prefer indexed Word.length, while keeping old / partially backfilled DBs correct."""
    return or_(
        Word.length == length,
        and_(or_(Word.length.is_(None), Word.length == 0), func.length(Word.char) == length),
    )


router = APIRouter(prefix="/words", tags=["words"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _deduplicate_words(words: Iterable[Word]) -> List[Word]:
    seen = set()
    unique = []
    for word in words:
        if isinstance(word, dict):
            c = word.get("char")
        else:
            c = getattr(word, "char", None)
        if c and c not in seen:
            seen.add(c)
            unique.append(word)
    return unique


def _paginate(items: List, offset: int, limit: int) -> List:
    if offset < 0:
        offset = 0
    return items[offset:offset + limit]


def _serialize_page(words: Iterable, offset: int, limit: int, **serialize_kw) -> List[dict]:
    page = _paginate(_deduplicate_words(words), offset, limit)
    return [_serialize_word(w, **serialize_kw) for w in page]


def _sync_word_to_cache(row) -> None:
    try:
        from utils import update_word_in_cache
        update_word_in_cache(
            row.char,
            getattr(row, "code", "") or "",
            getattr(row, "jyutping", "") or "",
            getattr(row, "finals", None),
            getattr(row, "initials", None),
            getattr(row, "length", None),
        )
    except Exception:
        pass


def _try_query_embedding(q: str) -> list:
    if not q:
        return []
    try:
        from utils import get_text_embedding
        if get_text_embedding.is_ready():
            return get_text_embedding(q)
    except Exception:
        pass
    return []


def _append_code_jyutping_headers(
    results: List[dict],
    codes: List[str],
    *,
    code_to_jyuts: Optional[dict] = None,
) -> None:
    code_to_jyuts = code_to_jyuts or {}
    for code_value in codes:
        results.append({
            "char": code_value,
            "code": code_value or "",
            "jyutping": "",
            "display_text": code_value,
            "query_text": code_value,
            "result_type": "code",
            "id": None,
        })
    seen_jyuts: set[str] = set()
    for code_value in codes:
        for jyutping_value in code_to_jyuts.get(code_value, []):
            j = (jyutping_value or "").strip()
            if not j or j in seen_jyuts:
                continue
            seen_jyuts.add(j)
            results.append({
                "char": j,
                "code": "",
                "jyutping": j or "",
                "display_text": j,
                "query_text": j,
                "result_type": "jyutping",
                "id": None,
            })


# _load_json_list moved to utils.py (public load_json_list) and aliased above for compat.
# Old body removed to avoid duplication. All prior call sites continue to work via the alias.


def _apply_code_filter(query, code: Optional[str], mode: str):
    if code:
        variants = get_code_variants(code, mode)
        query = query.filter(Word.code.in_(variants))
    return query


def _serialize_word(word: Word, *, display_text: Optional[str] = None, query_text: Optional[str] = None, result_type: str = "word") -> dict:
    if isinstance(word, dict):
        char_value = word.get("char") or ""
        jyutping_value = word.get("jyutping") or ""
        code_value = word.get("code") or get_0243_code(jyutping_value) or ""
        return {
            "char": char_value,
            "code": code_value or "",
            "jyutping": jyutping_value,
            "display_text": display_text or char_value,
            "query_text": query_text or char_value,
            "result_type": result_type,
            "id": word.get("id"),
        }

    code_value = word.code or get_0243_code(word.jyutping or "") or ""
    return {
        "char": word.char,
        "code": code_value or "",
        "jyutping": word.jyutping or "",
        "display_text": display_text or word.char,
        "query_text": query_text or word.char,
        "result_type": result_type,
        "id": getattr(word, "id", None),
    }


def _get_word_sort_code(word: Optional[Word]) -> str:
    if not word:
        return ""
    if isinstance(word, dict):
        return word.get("code") or get_0243_code(word.get("jyutping") or "") or ""
    return word.code or get_0243_code(word.jyutping or "") or ""


def _get_primary_codes(words: Iterable[Word]) -> List[str]:
    primary_codes = []
    for word in words:
        code_value = _get_word_sort_code(word)
        if code_value and code_value not in primary_codes:
            primary_codes.append(code_value)
    return primary_codes


def _build_code_aware_results(q: str, exact_matches: List[Word], db: Session) -> List[dict]:
    """專為 exact 漢字搜尋設計的排序建構器（searching page）。

    只使用「直接屬於查詢詞本身」的 0243 codes 與 jyutping 作為 header。
    強制同長度 (filter different word lengths)。
    盡量用 ORM 的 filter + order_by 產生各段結果，減少 Python 後處理 loop。

    順序（以「做到」為例）：
    - 24, 29 兩個 code header
    - code=24 對應的 jyutping, code=29 對應的 jyutping
    - 查詢詞本身
    - 同 code、同長度、至少共用一個 char + 同 rhyme 的詞（如「做數」），先 24 段再 29 段
    - 同 code、同長度、同 rhyme 的「不同 char」詞（相當於 24做到= / 29做到= 的結果）
    - 「24到」/「29到」風格（以尾字「到」的 final 做 position match）
    - 最後 q=24 / q=29 風格：該 code 下所有同長度詞
    """
    if not exact_matches:
        return []

    results: List[dict] = []
    len_q = len(q)

    # 只收集該詞直接擁有的 digit codes（例如 24、29），以數值排序確保 24 在 29 之前
    codes: List[str] = []
    code_to_jyuts: dict[str, List[str]] = defaultdict(list)
    for w in exact_matches:
        c = _get_word_sort_code(w)
        if c and c.isdigit() and c not in codes:
            codes.append(c)
        j = (w.jyutping or "").strip()
        if c and j and j not in code_to_jyuts[c]:
            code_to_jyuts[c].append(j)
    codes = sorted(codes, key=int)

    _append_code_jyutping_headers(results, codes, code_to_jyuts=code_to_jyuts)

    seen: set[str] = set()

    # 查詢詞本身（「做到」）
    for w in _deduplicate_words(exact_matches):
        if w.char not in seen:
            seen.add(w.char)
            results.append(_serialize_word(w, display_text=w.char, query_text=w.char, result_type="word"))

    if not codes:
        return results

    # 為 semantic similarity 排序準備 query embedding（redesign 後）
    # 只有模型已經 ready（極少數情況，通常是 ingest 後手動啟用）才會有值。
    # 正常 runtime 永遠不會觸發載入。
    query_emb = _try_query_embedding(q)

    def _get_finals_json_for_code(c: str) -> Optional[str]:
        for w in exact_matches:
            if _get_word_sort_code(w) == c and w.finals:
                return w.finals
        return None

    cached_candidates = [
        w for w in get_words_for_length(len_q)
        if _get_word_sort_code(w) in set(codes)
    ]
    if cached_candidates:
        code_candidates = sorted(cached_candidates, key=lambda w: (_get_word_text(w), _get_word_jyutping(w)))
    else:
        code_candidates = (
            db.query(Word)
            .filter(
                _length_filter(len_q),
                Word.code.in_(codes),
            )
            .order_by(Word.char, Word.jyutping)
            .limit(500)
            .all()
        )
    candidates_by_code: dict[str, list] = defaultdict(list)
    for candidate in code_candidates:
        candidates_by_code[_get_word_sort_code(candidate)].append(candidate)

    # 3+4. 對每個 code：先 同 char + 同 rhyme（e.g. 24下的「做數」），再 純同 rhyme 不同 char（"24做到="）
    q_chars = list(dict.fromkeys(q))
    for c in codes:
        fin_json = _get_finals_json_for_code(c)
        if not fin_json:
            continue

        target_finals = _load_json_list(fin_json)
        candidates = [
            w for w in candidates_by_code.get(c, [])
            if _get_word_parts(w, "finals") == target_finals
        ][:50]
        candidates = _deduplicate_words(candidates)
        shared_ws = [w for w in candidates if any(ch in _get_word_text(w) for ch in q_chars)]
        shared_chars = {_get_word_text(w) for w in shared_ws}
        pure_ws = [w for w in candidates if _get_word_text(w) not in shared_chars]

        # shared (有共用字 + 同韻)
        for w in shared_ws:
            char_value = _get_word_text(w)
            if char_value not in seen:
                seen.add(char_value)
                results.append(_serialize_word(w, display_text=char_value, query_text=char_value, result_type="word"))

        # 純同 rhyme（不同字）
        if query_emb:
            try:
                from utils import cosine_similarity
                scored = []
                for w in pure_ws[:200]:  # cap re-rank
                    w_emb = _load_json_list(getattr(w, "embedding", None) or "[]")
                    score = cosine_similarity(query_emb, w_emb) if w_emb else 0.0
                    if _get_word_text(w) not in seen:
                        scored.append((score, w))
                scored.sort(key=lambda x: -x[0])
                to_add = [w for s, w in scored]
            except Exception:
                to_add = [w for w in pure_ws if w.char not in seen]
        else:
            to_add = [w for w in pure_ws if _get_word_text(w) not in seen]
        for w in to_add:
            char_value = _get_word_text(w)
            seen.add(char_value)
            results.append(_serialize_word(w, display_text=char_value, query_text=char_value, result_type="word"))

    # 5. "24到" / "29到" 風格：用尾字的 final 做對應位置的 rhyme match
    last_ch = q[-1] if q else ""
    ref_fins: List[str] = []
    ref_pos = max(0, len_q - 1) if len_q > 0 else 0
    if last_ch:
        meta = get_char_meta(last_ch)
        ref_row = None
        if meta and meta.get("finals"):
            ref_fins = meta.get("finals") or []
        else:
            ref_row = db.query(Word).filter(Word.char == last_ch).first()
            if ref_row:
                ref_fins = _load_json_list(ref_row.finals)
            if ref_row:
                try:
                    _sync_word_to_cache(ref_row)
                except Exception:
                    pass
    ref_val = ref_fins[0] if ref_fins else None

    if ref_val is not None:
        for c in codes:
            matched = []
            for w in candidates_by_code.get(c, [])[:50]:
                try:
                    wf = _get_word_parts(w, "finals")
                    if len(wf) > ref_pos and wf[ref_pos] == ref_val:
                        matched.append(w)
                except (TypeError, json.JSONDecodeError):
                    pass
            for w in _deduplicate_words(matched):
                char_value = _get_word_text(w)
                if char_value not in seen:
                    seen.add(char_value)
                    results.append(_serialize_word(w, display_text=char_value, query_text=char_value, result_type="word"))

    # 6. 最後：q=24 / q=29 風格（只同 code 的詞，移除未指定 code 以避免無關結果如 "0尊"）
    # 當有 codes 時嚴格只取 target 的 codes；無 codes 時才包含未指定（相容舊行為）
    for w in _deduplicate_words(code_candidates[:100]):
        char_value = _get_word_text(w)
        if char_value not in seen:
            seen.add(char_value)
            results.append(_serialize_word(w, display_text=char_value, query_text=char_value, result_type="word"))

    return results


def _ensure_word_in_db(db: Session, text: str) -> List[Word]:
    """先測試資料庫有沒有該詞語(精確 char 匹配)。如果沒有且為漢字詞語，則使用 pycantonese 生成 jyutping，
    計算 code 與 initials/finals/tones，注入資料庫後返回新 entry。支援 pyjyutping 作為 fallback。
    """
    if not text or not text.strip():
        return []
    text = text.strip()
    existing = db.query(Word).filter(Word.char == text).all()
    if existing:
        return existing
    # 是否包含漢字
    if not re.search(r'[\u4e00-\u9fff]', text):
        return []
    jyut_str = ""
    # 優先 pycantonese
    try:
        import pycantonese
        jyut_list = pycantonese.characters_to_jyutping(text)
        if jyut_list:
            jyut_str = " ".join([item[1] for item in jyut_list if item and len(item) > 1 and item[1]])
    except Exception as e:
        print(f"[ensure] pycantonese error for {text}: {e}")
    if not jyut_str:
        # fallback
        try:
            from pyjyutping import jyutping as pyjy
            cand = pyjy.convert(text)
            if cand:
                jyut_str = cand
        except Exception:
            pass
    if not jyut_str:
        return []
    code_val = get_0243_code(jyut_str) or ""
    try:
        initials, finals, tones = split_jyutping(jyut_str)
    except Exception:
        initials = finals = tones = "[]"
    db_word = Word(
        char=text,
        code=code_val,
        jyutping=jyut_str,
        initials=initials,
        finals=finals,
        tones=tones,
        length=len(text),
        meaning=None,
    )
    db.add(db_word)
    try:
        db.commit()
        db.refresh(db_word)
        print(f"[ensure] injected into DB: '{text}' (code={code_val}, jyut={jyut_str})")
        _sync_word_to_cache(db_word)
        return [db_word]
    except Exception as e:  # P1 fix: keep message but ensure type is visible
        db.rollback()
        print(f"[ensure] DB insert failed for {text}: {type(e).__name__}: {e}")
        return []


@router.post("/", response_model=WordRead)
def create_word(word: WordCreate, db: Session = Depends(get_db)):
    data = word.dict()
    db_word = Word(**data)
    if db_word.length is None:
        db_word.length = len(db_word.char or "")
    db.add(db_word)
    db.commit()
    db.refresh(db_word)
    return db_word


@router.get("/{char}", response_model=WordRead)
def get_word(char: str, db: Session = Depends(get_db)):
    word = db.query(Word).filter(Word.char == char).first()
    if word is None:
        raise HTTPException(status_code=404, detail="字詞未找到")
    return word


def _handle_equals_syntax(q: str, code: Optional[str], mode: str, limit: int, offset: int, db):  # untyped db to avoid FastAPI treating it as a response field during module import
    """處理「左碼=目標=右碼」等號韻語法。"""
    match = re.match(r'^(\d*)(=)?([一-龥]+)?(=)?(\d*)$', q)
    if not match:
        return []

    left_code = match.group(1) or ""
    target_str = match.group(3) or ""
    right_code = match.group(5) or ""
    right_equal = bool(match.group(4))

    full_code = left_code + right_code

    if not target_str:
        return []

    target = db.query(Word).filter(Word.char == target_str).first()
    if not target:
        return []

    target_initials = _load_json_list(target.initials)
    target_finals = _load_json_list(target.finals)

    target_length = len(target_str)
    expected_length = len(left_code) + len(right_code) or target_length

    query = db.query(Word)
    query = _apply_code_filter(query, full_code, mode)
    query = query.filter(_length_filter(expected_length))
    is_rhyme_match = right_equal
    start_pos = max(0, len(left_code) - target_length)

    if start_pos == 0 and target_length == expected_length:
        target_parts = target_finals if is_rhyme_match else target_initials
        target_json = json.dumps(target_parts)
        compare_field = Word.finals if is_rhyme_match else Word.initials
        query = query.filter(compare_field == target_json)

        results = query.order_by(Word.char).offset(offset).limit(limit).all()
        return _deduplicate_words(results)

    candidates = query.order_by(Word.char).limit(2000).all()
    filtered = []
    target_parts = target_finals if is_rhyme_match else target_initials
    for word in candidates:
        word_parts = _load_json_list(word.finals if is_rhyme_match else word.initials)
        if not word_parts:
            continue
        match_ok = True
        for i in range(target_length):
            pos = start_pos + i
            if pos < len(word_parts) and i < len(target_parts):
                if target_parts[i] and target_parts[i] != word_parts[pos]:
                    match_ok = False
                    break
        if match_ok:
            filtered.append(word)

    return _paginate(_deduplicate_words(filtered), offset, limit)


def _get_word_parts(word, field: str) -> list:
    if isinstance(word, dict):
        return word.get(field) or []
    return _load_json_list(getattr(word, field, None))


def _get_word_text(word) -> str:
    if isinstance(word, dict):
        return word.get("char") or ""
    return getattr(word, "char", "") or ""


def _get_word_jyutping(word) -> str:
    if isinstance(word, dict):
        return word.get("jyutping") or ""
    return getattr(word, "jyutping", "") or ""


def _final_options_for_char(ch: str, db) -> set[str]:
    """Return possible first finals for a literal char, using cache before DB."""
    options: set[str] = set()
    for meta in get_char_metas(ch):
        finals = meta.get("finals") or []
        if finals:
            options.add(finals[0])
    if options:
        return options

    rows = db.query(Word).filter(Word.char == ch).all()
    if not rows:
        rows = _ensure_word_in_db(db, ch)
    for row in rows:
        finals = _load_json_list(getattr(row, "finals", None))
        if finals:
            options.add(finals[0])
        _sync_word_to_cache(row)
    return options


def _get_candidates_for_length(
    db: Session,
    length: int,
    *,
    code: Optional[str] = None,
    mode: str = "m1",
    fallback_limit: int = 2000,
):
    candidates = get_words_for_length(length)
    if candidates:
        return candidates, True
    query = db.query(Word).filter(_length_filter(length))
    if code:
        query = _apply_code_filter(query, code, mode)
    return query.order_by(Word.char, Word.jyutping).limit(fallback_limit).all(), False


def _build_final_options_at_positions(
    ref_chars: str,
    start_pos: int,
    width: int,
    db,
) -> list[Optional[set[str]]]:
    target_final_options: list[Optional[set[str]]] = [None] * width
    for i, ch in enumerate(ref_chars):
        pos = start_pos + i
        if 0 <= pos < width:
            options = _final_options_for_char(ch, db)
            if options:
                target_final_options[pos] = options
    return target_final_options


def _word_matches_last_final(word, final_options: Optional[set[str]]) -> bool:
    if not final_options:
        return True
    word_finals = _get_word_parts(word, "finals")
    return len(word_finals) >= 2 and word_finals[-1] in final_options


def _matches_code_positions(code_str: str, required_codes: list[Optional[str]], mode: str) -> bool:
    if len(code_str) != len(required_codes):
        return False
    for idx, req_digit in enumerate(required_codes):
        if req_digit is None:
            continue
        if code_str[idx] not in set(get_code_variants(req_digit, mode)):
            return False
    return True


def _matches_final_options(word_finals: list, target_final_options: list[Optional[set[str]]]) -> bool:
    if len(word_finals) != len(target_final_options):
        return False
    for idx, options in enumerate(target_final_options):
        if not options:
            continue
        if idx >= len(word_finals) or word_finals[idx] not in options:
            return False
    return True


def _matches_hybrid_ref_chars(
    word_char: str,
    word_finals: list,
    ref_chars: str,
    start_pos: int,
    target_final_options: list[Optional[set[str]]],
) -> bool:
    """Rhyme match at ref positions, or literal match (so 23就 includes 23@就 results)."""
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


def _mask_priority_key(word, literal_positions: list[tuple[int, str]]):
    char = _get_word_text(word)
    jyutping = _get_word_jyutping(word)
    exact_count = sum(1 for pos, ch in literal_positions if pos < len(char) and char[pos] == ch)
    return (-exact_count, char, jyutping)


def _handle_hybrid_syntax(q: str, code: Optional[str], mode: str, limit: int, offset: int, db):  # untyped db to avoid FastAPI treating it as a response field during module import
    """處理 hybrid（數字前綴 + 粵字 + 數字後綴）語法。"""
    hybrid_match = re.match(r'^(\d+)([一-龥]+)(\d*)$', q)
    if not hybrid_match:
        return []

    num_prefix = hybrid_match.group(1)
    ref_chars = hybrid_match.group(2)
    num_suffix = hybrid_match.group(3)

    full_code = num_prefix + num_suffix
    ref_pos = max(0, len(num_prefix) - 1)

    candidates, used_cache = _get_candidates_for_length(
        db, len(full_code), code=full_code, mode=mode,
    )
    target_final_options = _build_final_options_at_positions(
        ref_chars, ref_pos, len(full_code), db,
    )

    filtered = []
    allowed_full_codes = set(get_code_variants(full_code, mode))
    for word in candidates:
        if used_cache:
            if not word.get("finals") or not word.get("code"):
                continue
            word_finals = word.get("finals") or []
            word_code_str = word.get("code") or ""
        else:
            if not word.finals or not word.code:
                continue
            try:
                word_finals = json.loads(word.finals)
            except (TypeError, json.JSONDecodeError):
                continue
            word_code_str = word.code or ""
        if word_code_str not in allowed_full_codes:
            continue
        word_char = word.get("char") if used_cache else (word.char or "")
        if _matches_hybrid_ref_chars(
            word_char, word_finals, ref_chars, ref_pos, target_final_options,
        ):
            filtered.append(word)

    return _paginate(_deduplicate_words(filtered), offset, limit)


def _handle_mask_wildcard_query(q: str, code: Optional[str], mode: str, limit: int, offset: int, db):
    """Handle mask queries: literal canto chars match by position first, then code digits."""
    mask = q
    expected_len, required_codes, literal_positions = _parse_mask_query(mask)
    if expected_len == 0:
        return []

    glob_pat = _mask_char_glob_pattern(mask)
    candidates = get_words_for_length(expected_len)
    used_cache = bool(candidates)
    if used_cache:
        candidates = [
            w for w in candidates
            if _matches_mask_literal_chars(_get_word_text(w), mask)
        ]
    else:
        query = db.query(Word).filter(
            _length_filter(expected_len),
            Word.char.op("GLOB")(glob_pat),
        )
        code_filter = "".join(required_codes) if all(req is not None for req in required_codes) else None
        if code_filter:
            query = _apply_code_filter(query, code_filter, mode)
        candidates = query.order_by(Word.char, Word.jyutping).all()

    filtered = []
    for word in candidates:
        word_char = _get_word_text(word)
        if not _matches_mask_literal_chars(word_char, mask):
            continue
        word_code_str = _get_word_sort_code(word)
        word_finals = _get_word_parts(word, "finals")
        if not word_code_str or not word_finals:
            continue
        if not _matches_code_positions(word_code_str, required_codes, mode):
            continue
        filtered.append(word)

    filtered.sort(key=lambda item: _mask_priority_key(item, literal_positions))
    return _serialize_page(filtered, offset, limit)


def _handle_pure_digit_query(q: str, code: Optional[str], mode: str, limit: int, offset: int, db: "Session") -> List[dict]:
    """處理純數字查詢（如 "23"）。"""
    query = db.query(Word)
    query = _apply_code_filter(query, q, mode)
    query = query.filter(_length_filter(len(q)))
    results = query.order_by(Word.char).offset(offset).limit(limit).all()
    return _deduplicate_words(results)


def _handle_pure_canto_query(q: str, code: Optional[str], mode: str, limit: int, offset: int, db: "Session") -> List[dict]:
    """處理純粵字（漢字）查詢。
    包含自動 _ensure 新詞 + 使用 code-aware 排序建構器。
    """
    # 對純漢字 q，先測試資料庫；若無則用 pycantonese 生成並注入
    raw_targets: List[Word] = []
    if re.search(r'[\u4e00-\u9fff]', q):
        raw_targets = _ensure_word_in_db(db, q)
    if not raw_targets:
        raw_targets = db.query(Word).filter(Word.char == q).all()
    target_words = _deduplicate_words(raw_targets)
    # 使用 raw 以收集同字不同讀音的全部 code (例如 到 的 4 與 9)
    primary_codes = _get_primary_codes(raw_targets) if raw_targets else []

    if target_words:
        # 使用專門的 code-aware 排序（只允許查詢詞自己擁有的 0243 code 與 jyutping 當 header，
        # 各段都用 ORM filter + order_by + 同長度限制，過濾無關結果）
        built = _build_code_aware_results(q, raw_targets, db)
        return _paginate(built, offset, limit)

    return []


def _handle_jyut_fragment_query(q: str, limit: int, offset: int, db: "Session") -> List[dict]:
    """處理粵拼片段查詢（含字母的）。"""
    # Cap to keep instant even for broad jyut fragments (rare path); slice after.
    results = db.query(Word).filter(Word.jyutping.ilike(f"%{q}%")).order_by(Word.char).limit(500).all()
    return _paginate(_deduplicate_words(results), offset, limit)


def _parse_relation_syntax(q: str) -> Optional[dict]:
    """Parse 0243 relation syntax: ~syn, !ant, !! compound, optional digit code prefix."""
    compound = COMPOUND_ANT_RE.match(q)
    if compound:
        prefix = compound.group(1) or ""
        rhyme_char = compound.group(2) or None
        return {
            "kind": "compound_ant",
            "code_prefix": prefix or None,
            "rhyme_char": rhyme_char,
        }

    lookup = RELATION_LOOKUP_RE.match(q)
    if lookup:
        prefix = lookup.group(1) or ""
        op = lookup.group(2)
        word = lookup.group(3)
        return {
            "kind": "syn" if op == "~" else "ant",
            "code_prefix": prefix or None,
            "word": word,
        }
    return None


def _words_for_relation_chars(
    db: Session,
    ranked_chars: List[str],
    *,
    code_prefix: Optional[str],
    mode: str,
    limit: int,
    offset: int,
) -> List[dict]:
    """Map ranked relation chars to Word rows, optionally filtered by 0243 code prefix."""
    if not ranked_chars:
        return []

    char_order = {ch: idx for idx, ch in enumerate(dict.fromkeys(ranked_chars))}
    query = db.query(Word).filter(Word.char.in_(list(char_order.keys())))
    if code_prefix:
        variants = get_code_variants(code_prefix, mode)
        query = query.filter(Word.code.in_(variants), _length_filter(len(code_prefix)))

    words = query.all()
    words.sort(key=lambda w: (char_order.get(w.char or "", 10**9), w.code or "", w.jyutping or ""))
    return _serialize_page(words, offset, limit, result_type="word")


def _handle_relation_lookup_syntax(
    parsed: dict,
    mode: str,
    limit: int,
    offset: int,
    db: Session,
) -> List[dict]:
    from app.services.syn_ant_service import search_relation_chars

    word = parsed["word"]
    relation_type = parsed["kind"]
    _ensure_word_in_db(db, word)
    ranked_chars = search_relation_chars(db, word, relation_type)
    return _words_for_relation_chars(
        db,
        ranked_chars,
        code_prefix=parsed.get("code_prefix"),
        mode=mode,
        limit=limit,
        offset=offset,
    )


def _handle_antonym_compound_syntax(
    parsed: dict,
    mode: str,
    limit: int,
    offset: int,
    db: Session,
) -> List[dict]:
    from app.services.syn_ant_service import build_char_antonym_pairs

    ant_pairs = build_char_antonym_pairs(db)
    if not ant_pairs:
        return []

    candidates: set[str] = set()
    for a, b in ant_pairs:
        if len(a) == 1 and len(b) == 1:
            candidates.add(a + b)
            candidates.add(b + a)
    if not candidates:
        return []

    query = db.query(Word).filter(Word.char.in_(list(candidates)), _length_filter(2))
    code_prefix = parsed.get("code_prefix")
    if code_prefix:
        variants = get_code_variants(code_prefix, mode)
        query = query.filter(Word.code.in_(variants))

    last_final_options: Optional[set[str]] = None
    rhyme_char = parsed.get("rhyme_char")
    if rhyme_char:
        last_final_options = _final_options_for_char(rhyme_char, db)
        if not last_final_options:
            return []

    results: List[Word] = []
    seen_chars: set[str] = set()
    for word in query.order_by(Word.char, Word.code, Word.jyutping).all():
        ch = word.char or ""
        if len(ch) != 2:
            continue
        if (ch[0], ch[1]) not in ant_pairs and (ch[1], ch[0]) not in ant_pairs:
            continue
        if not _word_matches_last_final(word, last_final_options):
            continue
        if ch in seen_chars:
            continue
        seen_chars.add(ch)
        results.append(word)

    return _serialize_page(results, offset, limit, result_type="word")


@router.get("/search", response_model=list[WordRead])
@router.get("/search/", response_model=list[WordRead])
def search_words(
    q: str = None,
    code: str = None,
    char: str = None,
    mode: str = "m1",   # 改為 m1 作為更合理的預設（許多用戶從 m1 開始）
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    if not q:
        query = db.query(Word)
        query = _apply_code_filter(query, code, mode)
        if char:
            query = query.filter(Word.char == char)
        results = query.order_by(Word.char).offset(offset).limit(limit).all()
        return _deduplicate_words(results)

    q = q.strip()

    if mode == 'syn':
        # Independent syn/ant mode: bypass all code/rhyme/hybrid/wildcard paths.
        return handle_syn_ant_search(q, db, limit=limit, offset=offset)

    relation_parsed = _parse_relation_syntax(q)
    if relation_parsed:
        if relation_parsed["kind"] == "compound_ant":
            return _handle_antonym_compound_syntax(relation_parsed, mode, limit, offset, db)
        return _handle_relation_lookup_syntax(relation_parsed, mode, limit, offset, db)

    if _is_framed_equals_query(q):
        return _handle_equals_syntax(q, code, mode, limit, offset, db)

    code_tail_parsed = _parse_code_tail_query(q)
    if code_tail_parsed:
        return _handle_code_tail_query(code_tail_parsed, mode, limit, offset, db)

    at_tail_parsed = _parse_at_tail_query(q)
    if at_tail_parsed:
        return _handle_at_tail_query(at_tail_parsed, mode, limit, offset, db)

    rhyme_anchor_parsed = _parse_rhyme_anchor_query(q)
    if rhyme_anchor_parsed:
        return _handle_rhyme_anchor_query(rhyme_anchor_parsed, mode, limit, offset, db)

    hybrid_match = re.match(r'^(\d+)([一-龥]+)(\d*)$', q)
    if hybrid_match and not hybrid_match.group(3):
        return _handle_hybrid_syntax(q, code, mode, limit, offset, db)

    if _looks_like_mask_query(q):
        return _handle_mask_wildcard_query(q, code, mode, limit, offset, db)

    if q.isdigit():
        return _handle_pure_digit_query(q, code, mode, limit, offset, db)

    # 純粵字（含自動 ensure 新詞 + code-aware 排序）
    # 內部已處理「只有含中文才 _ensure」，非中文時直接查字表
    res = _handle_pure_canto_query(q, code, mode, limit, offset, db)
    if res:
        return res

    if re.search(r'[a-zA-Z]', q):
        return _handle_jyut_fragment_query(q, limit, offset, db)

    return []


# ==================== Independent 近義/反義詞查找 (mode='syn') ====================
# Early branched from search_words. Pure canto focus. No code/length/final logic.
# Blend: precomputed WordRelation (from generate_relationships.py using static+optional-embed at ingest)
# + static vendor thesaurus (cilin groups + antisem/guotong) loaded at startup (no ML at runtime).
# Returns items compatible with WordRead (char+code+jyutping required by the endpoint response_model)
# plus the extra "relation" field that the syn-mode frontend uses to split columns.
# code/jyutping are empty for syn results (not relevant in this mode).
# _ensure ensures the query word itself is in DB (for future relations). No runtime embedding.


def handle_syn_ant_search(
    q: str,
    db: "Session",
    *,
    limit: int = 160,
    offset: int = 0,
) -> list[dict]:
    from app.services.syn_ant_service import search_syn_ant
    if not q or not re.search(r'[\u4e00-\u9fff]', q):
        return []
    q = q.strip()
    _ensure_word_in_db(db, q)
    return search_syn_ant(db, q, limit=limit, offset=offset)
