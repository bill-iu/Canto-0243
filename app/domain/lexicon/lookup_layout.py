"""詞條 lookup 版面 — 純漢字精確查詢的多段結果編排。"""

from __future__ import annotations

import json
from collections import defaultdict
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.lexicon.ranking import search_result_sort_key
from app.models.word import Word
from app.services.word_db_filters import length_filter
from app.services.word_serializer import (
    deduplicate_words,
    get_word_jyutping,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
    serialize_word,
)
from app.utils.embedding import cosine_similarity, get_text_embedding
from app.utils.json_helpers import load_json_list
from app.utils.word_cache import get_char_meta, get_words_for_length


def _try_query_embedding(q: str) -> list:
    if not q:
        return []
    try:
        if get_text_embedding.is_ready():
            return get_text_embedding(q)
    except Exception:
        pass
    return []


def _collect_codes_and_jyuts(exact_matches: List[Word]) -> tuple[List[str], dict[str, List[str]]]:
    codes: List[str] = []
    code_to_jyuts: dict[str, List[str]] = defaultdict(list)
    for w in exact_matches:
        c = get_word_sort_code(w)
        if c and c.isdigit() and c not in codes:
            codes.append(c)
        j = (get_word_jyutping(w) or "").strip()
        if c and j and j not in code_to_jyuts[c]:
            code_to_jyuts[c].append(j)
    return sorted(codes, key=int), code_to_jyuts


def _append_code_headers(
    results: List[dict],
    codes: List[str],
    *,
    code_to_jyuts: dict[str, List[str]],
) -> None:
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


def _append_words(results: List[dict], seen: set[str], words: List[Word]) -> None:
    for w in deduplicate_words(words):
        char_value = get_word_text(w)
        if char_value in seen:
            continue
        seen.add(char_value)
        results.append(serialize_word(w, display_text=char_value, query_text=char_value, result_type="word"))


def _load_code_candidates(len_q: int, codes: List[str], db: Session) -> list:
    cached = [w for w in get_words_for_length(len_q) if get_word_sort_code(w) in set(codes)]
    if cached:
        return sorted(cached, key=search_result_sort_key)
    rows = (
        db.query(Word)
        .filter(length_filter(len_q), Word.code.in_(codes))
        .order_by(Word.char, Word.jyutping)
        .limit(500)
        .all()
    )
    return sorted(rows, key=search_result_sort_key)


def _finals_json_for_code(exact_matches: List[Word], code: str) -> Optional[str]:
    for w in exact_matches:
        if get_word_sort_code(w) != code:
            continue
        finals_raw = w.finals if not isinstance(w, dict) else w.get("finals")
        if finals_raw:
            return finals_raw if isinstance(finals_raw, str) else json.dumps(finals_raw)
    return None


def resolve_tail_rhyme_ref(*, last_ch: str, len_q: int) -> tuple[Optional[str], int]:
    """尾字韻錨：只讀快取 meta，不觸 DB 或快取寫入。"""
    ref_pos = max(0, len_q - 1) if len_q > 0 else 0
    if not last_ch:
        return None, ref_pos
    meta = get_char_meta(last_ch)
    if meta and meta.get("finals"):
        ref_fins = meta.get("finals") or []
        return (ref_fins[0] if ref_fins else None), ref_pos
    return None, ref_pos


def resolve_tail_rhyme_ref_from_db(
    db: Session,
    *,
    last_ch: str,
    len_q: int,
) -> tuple[Optional[str], int]:
    """尾字韻錨 DB 回退；呼叫端負責 warm_ref_char_for_lookup。"""
    ref_pos = max(0, len_q - 1) if len_q > 0 else 0
    if not last_ch:
        return None, ref_pos
    ref_val, pos = resolve_tail_rhyme_ref(last_ch=last_ch, len_q=len_q)
    if ref_val is not None:
        return ref_val, pos
    ref_row = db.query(Word).filter(Word.char == last_ch).first()
    if not ref_row:
        return None, ref_pos
    ref_fins = load_json_list(ref_row.finals)
    return (ref_fins[0] if ref_fins else None), ref_pos


def _rank_pure_rhyme_words(pure_ws: List[Word], seen: set[str], query_emb: list) -> List[Word]:
    candidates = [w for w in pure_ws if get_word_text(w) not in seen][:200]
    if not query_emb:
        return candidates
    try:
        scored = []
        for w in candidates:
            w_emb = load_json_list(getattr(w, "embedding", None) or "[]")
            score = cosine_similarity(query_emb, w_emb) if w_emb else 0.0
            scored.append((score, w))
        scored.sort(key=lambda x: -x[0])
        return [w for _, w in scored]
    except Exception:
        return candidates


def _append_per_code_rhyme_sections(
    results: List[dict],
    seen: set[str],
    *,
    q: str,
    codes: List[str],
    exact_matches: List[Word],
    candidates_by_code: dict[str, list],
    query_emb: list,
) -> None:
    q_chars = list(dict.fromkeys(q))
    for code in codes:
        fin_json = _finals_json_for_code(exact_matches, code)
        if not fin_json:
            continue
        target_finals = load_json_list(fin_json)
        pool = [
            w for w in candidates_by_code.get(code, [])
            if get_word_parts(w, "finals") == target_finals
        ][:50]
        pool = deduplicate_words(pool)
        shared = [w for w in pool if any(ch in get_word_text(w) for ch in q_chars)]
        shared_chars = {get_word_text(w) for w in shared}
        pure = [w for w in pool if get_word_text(w) not in shared_chars]
        _append_words(results, seen, shared)
        _append_words(results, seen, _rank_pure_rhyme_words(pure, seen, query_emb))


def _append_tail_rhyme_section(
    results: List[dict],
    seen: set[str],
    *,
    codes: List[str],
    candidates_by_code: dict[str, list],
    ref_val: Optional[str],
    ref_pos: int,
) -> None:
    if ref_val is None:
        return
    for code in codes:
        matched = []
        for w in candidates_by_code.get(code, [])[:50]:
            try:
                wf = get_word_parts(w, "finals")
                if len(wf) > ref_pos and wf[ref_pos] == ref_val:
                    matched.append(w)
            except (TypeError, json.JSONDecodeError):
                pass
        _append_words(results, seen, matched)


def build_lookup_layout(q: str, exact_matches: List[Word], db: Session) -> List[dict]:
    """純漢字精確查詢的多段版面（code header → 本詞 → 同韻段 → 尾字韻 → 同碼餘下）。"""
    if not exact_matches:
        return []

    results: List[dict] = []
    seen: set[str] = set()
    len_q = len(q)
    codes, code_to_jyuts = _collect_codes_and_jyuts(exact_matches)

    _append_code_headers(results, codes, code_to_jyuts=code_to_jyuts)
    _append_words(results, seen, exact_matches)

    if not codes:
        return results

    code_candidates = _load_code_candidates(len_q, codes, db)
    candidates_by_code: dict[str, list] = defaultdict(list)
    for candidate in code_candidates:
        candidates_by_code[get_word_sort_code(candidate)].append(candidate)

    _append_per_code_rhyme_sections(
        results,
        seen,
        q=q,
        codes=codes,
        exact_matches=exact_matches,
        candidates_by_code=candidates_by_code,
        query_emb=_try_query_embedding(q),
    )

    ref_val, ref_pos = resolve_tail_rhyme_ref_from_db(
        db, last_ch=q[-1] if q else "", len_q=len_q
    )
    _append_tail_rhyme_section(
        results,
        seen,
        codes=codes,
        candidates_by_code=candidates_by_code,
        ref_val=ref_val,
        ref_pos=ref_pos,
    )
    _append_words(results, seen, code_candidates[:100])
    return results