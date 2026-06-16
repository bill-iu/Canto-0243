from __future__ import annotations

import json
from collections import defaultdict
from typing import List, Optional

from sqlalchemy.orm import Session

from app.utils.embedding import cosine_similarity, get_text_embedding
from app.utils.json_helpers import load_json_list
from app.utils.word_cache import get_char_meta, get_words_for_length

from app.models.word import Word
from app.services.word_db_filters import length_filter
from app.domain.lexicon.ranking import search_result_sort_key
from app.services.word_ensure_service import sync_word_to_cache
from app.services.word_serializer import (
    deduplicate_words,
    get_primary_codes,
    get_word_jyutping,
    get_word_parts,
    get_word_sort_code,
    get_word_text,
    serialize_word,
)

def try_query_embedding(q: str) -> list:
    if not q:
        return []
    try:
        if get_text_embedding.is_ready():
            return get_text_embedding(q)
    except Exception:
        pass
    return []

def append_code_jyutping_headers(
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

def collect_codes_and_jyuts_from_exact(exact_matches: List[Word]) -> tuple[List[str], dict[str, List[str]]]:
    """只收集該詞直接擁有的 digit codes（例如 24、29），以數值排序確保 24 在 29 之前。
    同時建立 code -> jyutping list（供 header 使用）。
    """
    codes: List[str] = []
    code_to_jyuts: dict[str, List[str]] = defaultdict(list)
    for w in exact_matches:
        c = get_word_sort_code(w)
        if c and c.isdigit() and c not in codes:
            codes.append(c)
        j = (w.jyutping or "").strip()
        if c and j and j not in code_to_jyuts[c]:
            code_to_jyuts[c].append(j)
    codes = sorted(codes, key=int)
    return codes, code_to_jyuts


def build_code_aware_results(q: str, exact_matches: List[Word], db: Session) -> List[dict]:
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

    codes, code_to_jyuts = collect_codes_and_jyuts_from_exact(exact_matches)
    append_code_jyutping_headers(results, codes, code_to_jyuts=code_to_jyuts)

    seen: set[str] = set()

    # 查詢詞本身（「做到」）
    for w in deduplicate_words(exact_matches):
        char_value = get_word_text(w)
        if char_value not in seen:
            seen.add(char_value)
            results.append(serialize_word(w, display_text=char_value, query_text=char_value, result_type="word"))

    if not codes:
        return results

    # 為 semantic similarity 排序準備 query embedding（redesign 後）
    # 只有模型已經 ready（極少數情況，通常是 ingest 後手動啟用）才會有值。
    # 正常 runtime 永遠不會觸發載入。
    query_emb = try_query_embedding(q)

    def get_finals_json_for_code(c: str) -> Optional[str]:
        for w in exact_matches:
            if get_word_sort_code(w) != c:
                continue
            finals_raw = w.finals if not isinstance(w, dict) else w.get("finals")
            if finals_raw:
                return finals_raw if isinstance(finals_raw, str) else json.dumps(finals_raw)
        return None

    cached_candidates = [
        w for w in get_words_for_length(len_q)
        if get_word_sort_code(w) in set(codes)
    ]
    if cached_candidates:
        code_candidates = sorted(cached_candidates, key=search_result_sort_key)
    else:
        code_candidates = (
            db.query(Word)
            .filter(
                length_filter(len_q),
                Word.code.in_(codes),
            )
            .order_by(Word.char, Word.jyutping)
            .limit(500)
            .all()
        )
        code_candidates = sorted(code_candidates, key=search_result_sort_key)
    candidates_by_code: dict[str, list] = defaultdict(list)
    for candidate in code_candidates:
        candidates_by_code[get_word_sort_code(candidate)].append(candidate)

    # 3+4. 對每個 code：先 同 char + 同 rhyme（e.g. 24下的「做數」），再 純同 rhyme 不同 char（"24做到="）
    q_chars = list(dict.fromkeys(q))
    for c in codes:
        fin_json = get_finals_json_for_code(c)
        if not fin_json:
            continue

        target_finals = load_json_list(fin_json)
        candidates = [
            w for w in candidates_by_code.get(c, [])
            if get_word_parts(w, "finals") == target_finals
        ][:50]
        candidates = deduplicate_words(candidates)
        shared_ws = [w for w in candidates if any(ch in get_word_text(w) for ch in q_chars)]
        shared_chars = {get_word_text(w) for w in shared_ws}
        pure_ws = [w for w in candidates if get_word_text(w) not in shared_chars]

        # shared (有共用字 + 同韻)
        for w in shared_ws:
            char_value = get_word_text(w)
            if char_value not in seen:
                seen.add(char_value)
                results.append(serialize_word(w, display_text=char_value, query_text=char_value, result_type="word"))

        # 純同 rhyme（不同字）
        if query_emb:
            try:
                scored = []
                for w in pure_ws[:200]:  # cap re-rank
                    w_emb = load_json_list(getattr(w, "embedding", None) or "[]")
                    score = cosine_similarity(query_emb, w_emb) if w_emb else 0.0
                    if get_word_text(w) not in seen:
                        scored.append((score, w))
                scored.sort(key=lambda x: -x[0])
                to_add = [w for s, w in scored]
            except Exception:
                # 語意重排失敗時安全 fallback（行為與無 embedding 時一致）
                to_add = [w for w in pure_ws if get_word_text(w) not in seen]
        else:
            to_add = [w for w in pure_ws if get_word_text(w) not in seen]
        for w in to_add:
            char_value = get_word_text(w)
            seen.add(char_value)
            results.append(serialize_word(w, display_text=char_value, query_text=char_value, result_type="word"))

    # 5. "24到" / "29到" 風格：用尾字的 final 做對應位置的 rhyme match
    ref_val, ref_pos = get_ref_final_for_position_rhyme(q, db, last_ch=q[-1] if q else "", len_q=len_q)
    if ref_val is not None:
        for c in codes:
            matched = []
            for w in candidates_by_code.get(c, [])[:50]:
                try:
                    wf = get_word_parts(w, "finals")
                    if len(wf) > ref_pos and wf[ref_pos] == ref_val:
                        matched.append(w)
                except (TypeError, json.JSONDecodeError):
                    # 單筆 finals 解析失敗時跳過該筆，不影響其他結果
                    pass
            for w in deduplicate_words(matched):
                char_value = get_word_text(w)
                if char_value not in seen:
                    seen.add(char_value)
                    results.append(serialize_word(w, display_text=char_value, query_text=char_value, result_type="word"))

    # 6. 最後：q=24 / q=29 風格（只同 code 的詞，移除未指定 code 以避免無關結果如 "0尊"）
    # 當有 codes 時嚴格只取 target 的 codes；無 codes 時才包含未指定（相容舊行為）
    for w in deduplicate_words(code_candidates[:100]):
        char_value = get_word_text(w)
        if char_value not in seen:
            seen.add(char_value)
            results.append(serialize_word(w, display_text=char_value, query_text=char_value, result_type="word"))

    return results


def get_ref_final_for_position_rhyme(q: str, db: Session, *, last_ch: str, len_q: int) -> tuple[Optional[str], int]:
    """計算「24到」類 position rhyme 所需的 ref final 與位置。
    獨立抽出以降低主函式複雜度，並集中快取/回退邏輯。
    """
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
                ref_fins = load_json_list(ref_row.finals)
            if ref_row:
                try:
                    sync_word_to_cache(ref_row)
                except Exception:
                    # 快取同步失敗不影響主流程（已記錄診斷即可）
                    pass
    ref_val = ref_fins[0] if ref_fins else None
    return ref_val, ref_pos
