import json
import re
from typing import Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, literal, or_
from sqlalchemy.orm import Session

from app.database import SessionLocal, contains_substring, IS_POSTGRES
from app.models.word import Word
from app.schemas.word_schema import WordCreate, WordRead
from utils import (
    get_0243_code,
    get_code_variants,
    split_jyutping,
    get_text_embedding,
    cosine_similarity,
    load_json_list,
    get_words_for_length,
    get_char_meta,
)

# Back-compat alias for the many internal _load_json_list(...) calls throughout this file
_load_json_list = load_json_list
from collections import defaultdict

def _length_filter(length: int):
    """使用已回填的 Word.length（有 index），大幅加快 length 過濾查詢。
    現在 length 已全 populate，無需 fallback。
    """
    return Word.length == length


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


# _load_json_list moved to utils.py (public load_json_list) and aliased above for compat.
# Old body removed to avoid duplication. All prior call sites continue to work via the alias.


def _apply_code_filter(query, code: Optional[str], mode: str):
    if code:
        variants = get_code_variants(code, mode)
        query = query.filter(Word.code.in_(variants))
    return query


def _serialize_word(word: Word, *, display_text: Optional[str] = None, query_text: Optional[str] = None, result_type: str = "word") -> dict:
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
    return word.code or get_0243_code(word.jyutping or "") or ""


def _get_primary_codes(words: Iterable[Word]) -> List[str]:
    primary_codes = []
    for word in words:
        code_value = _get_word_sort_code(word)
        if code_value and code_value not in primary_codes:
            primary_codes.append(code_value)
    return primary_codes


def _build_similarity_query(db: Session, q: str, target_words: Optional[List[Word]]):
    if not target_words:
        return db.query(Word).order_by(Word.char, Word.code, Word.jyutping)

    target_word = target_words[0]
    target_codes = [code for code in _get_primary_codes(target_words) if code]
    target_finals_json = json.dumps(_load_json_list(target_word.finals))

    query = db.query(Word).filter(Word.char != q)

    shared_char_conditions = [contains_substring(Word.char, char) for char in dict.fromkeys(q) if char]
    if shared_char_conditions:
        shared_char_expr = or_(*shared_char_conditions)
    else:
        shared_char_expr = literal(False)

    same_rhyme_expr = Word.finals == target_finals_json
    same_code_expr = Word.code.in_(target_codes) if target_codes else literal(True)
    # 舊 similarity ranking 用：檢查 Word.char 是否為 q 的子字串（instr(q, Word.char) 語義）
    if IS_POSTGRES:
        query_substring_expr = func.strpos(func.literal(q), Word.char) > 0
    else:
        query_substring_expr = func.instr(q, Word.char) > 0
    primary_rank = case(
        (query_substring_expr, 0),
        ((shared_char_expr) & same_rhyme_expr, 1),
        (shared_char_expr, 2),
        (same_rhyme_expr, 3),
        else_=4,
    )
    same_code_rank = case((same_code_expr, 0), else_=1)
    return query.order_by(primary_rank, same_code_rank, Word.char, Word.code, Word.jyutping)


def _build_character_search_results(q: str, words: List[Word], related_words: Optional[List[Word]] = None, primary_codes: Optional[List[str]] = None) -> List[dict]:
    """建構 searching page 結果。
    sorting method（同 tier 下）：
      先顯示 code A 和 code B，然後對應的 jyutping A 和 jyutping B，
      然後 code A 的 tier 結果，然後 code B 的 tier 結果，
      然後下一個 tier，如此類推。
    這裡以每個 code 的小節方式輸出（code header + 對應 jyut + 該 code 在此 tier 的 words），
    並優先處理 primary codes (target 帶來的 A/B，例如 9 與 29 相關)。
    """
    results: List[dict] = []
    if primary_codes is None:
        primary_codes = _get_primary_codes(words)

    # 初始 headers：來自 target 的 codes (支援多 code 如 4/9 給 "到") 與 jyutpings
    for code_value in primary_codes:
        results.append({
            "char": code_value,
            "code": code_value or "",
            "jyutping": "",
            "display_text": code_value,
            "query_text": code_value,
            "result_type": "code",
            "id": None,
        })

    target_jyutpings: List[str] = []
    for word in words:
        j = (word.jyutping or "").strip()
        if j and j not in target_jyutpings:
            target_jyutpings.append(j)
    for jyutping_value in target_jyutpings:
        results.append({
            "char": jyutping_value,
            "code": "",
            "jyutping": jyutping_value or "",
            "display_text": jyutping_value,
            "query_text": jyutping_value,
            "result_type": "jyutping",
            "id": None,
        })

    seen: set[str] = set()
    # 先輸出 target 詞本身
    for word in _deduplicate_words(words):
        if word.char not in seen:
            seen.add(word.char)
            results.append(_serialize_word(word, display_text=word.char, query_text=word.char, result_type="word"))

    # 為 semantic similarity 排序準備 query embedding（兩個版本都支援）
    query_emb = get_text_embedding(q) if q else []

    related_words = related_words or []
    if not related_words:
        return results

    # 將 related 依 tier (primary_rank) 分組
    target_word = words[0] if words else None
    target_finals_json = json.dumps(_load_json_list(target_word.finals)) if target_word else "[]"
    q_chars = list(dict.fromkeys(q))

    tier_groups: dict[int, list[Word]] = defaultdict(list)
    for rw in related_words:
        rw_finals_json = json.dumps(_load_json_list(rw.finals))
        has_shared = any((ch in rw.char) for ch in q_chars if ch)
        is_substr = bool(rw.char) and (rw.char in q)
        is_same_rhyme = rw_finals_json == target_finals_json

        if is_substr:
            rank = 0
        elif has_shared and is_same_rhyme:
            rank = 1
        elif has_shared:
            rank = 2
        elif is_same_rhyme:
            rank = 3
        else:
            rank = 4

        if rw.char not in seen:
            tier_groups[rank].append(rw)

    # 每 tier：按 ordered code (primary A/B 優先) 逐 code 輸出：code header + 對應 jyut(s) + 該 code 的 words
    for rank in sorted(tier_groups.keys()):
        tier_ws = tier_groups[rank]
        if not tier_ws:
            continue

        # 建 group
        code_groups: dict[str, list[Word]] = defaultdict(list)
        for w in tier_ws:
            c = _get_word_sort_code(w)
            code_groups[c].append(w)

        # ordered: primary 裡在此 tier 有的先，然後其餘 code 字串排序
        codes_in_tier = [c for c in primary_codes if code_groups.get(c)]
        other_codes = sorted(c for c in code_groups.keys() if c not in primary_codes and code_groups.get(c))
        ordered_codes = codes_in_tier + other_codes

        for c in ordered_codes:
            # 顯示 code (A 或 B)
            results.append({
                "char": c,
                "code": c or "",
                "jyutping": "",
                "display_text": c,
                "query_text": c,
                "result_type": "code",
                "id": None,
            })
            # 對應的 jyutping (此 code 在 tier 內的)
            js_for_c: List[str] = []
            for w in code_groups.get(c, []):
                j = (w.jyutping or "").strip()
                if j and j not in js_for_c:
                    js_for_c.append(j)
            for jval in js_for_c:
                results.append({
                    "char": jval,
                    "code": "",
                    "jyutping": jval or "",
                    "display_text": jval,
                    "query_text": jval,
                    "result_type": "jyutping",
                    "id": None,
                })
            # 然後此 code 在此 tier 的結果
            for w in _deduplicate_words(code_groups.get(c, [])):
                if w.char not in seen:
                    seen.add(w.char)
                    results.append(_serialize_word(w, display_text=w.char, query_text=w.char, result_type="word"))

    return results


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

    # 1. 先顯示 code 24 和 code 29
    for c in codes:
        results.append({
            "char": c, "code": c, "jyutping": "",
            "display_text": c, "query_text": c,
            "result_type": "code", "id": None
        })

    # 2. 然後對應的 jyutping（code=24 的先，code=29 的後）
    for c in codes:
        for j in code_to_jyuts.get(c, []):
            results.append({
                "char": j, "code": "", "jyutping": j,
                "display_text": j, "query_text": j,
                "result_type": "jyutping", "id": None
            })

    seen: set[str] = set()

    # 查詢詞本身（「做到」）
    for w in _deduplicate_words(exact_matches):
        if w.char not in seen:
            seen.add(w.char)
            results.append(_serialize_word(w, display_text=w.char, query_text=w.char, result_type="word"))

    if not codes:
        return results

    # 為 semantic similarity 排序準備 query embedding（兩個版本都支援）
    # 只在 model 已 preload (by warmup) 時才 load，避免第一次 hanzi search 延遲 model load
    query_emb = []
    if q:
        if hasattr(get_text_embedding, "_model") and get_text_embedding._model is not None:
            query_emb = get_text_embedding(q)
        # else: skip for this search to keep fast; re-rank will be skipped until warmup done

    def _get_finals_json_for_code(c: str) -> Optional[str]:
        for w in exact_matches:
            if _get_word_sort_code(w) == c and w.finals:
                return w.finals
        return None

    # 3+4. 對每個 code：先 同 char + 同 rhyme（e.g. 24下的「做數」），再 純同 rhyme 不同 char（"24做到="）
    q_chars = list(dict.fromkeys(q))
    for c in codes:
        fin_json = _get_finals_json_for_code(c)
        if not fin_json:
            continue

        # 優化：只用一個 query 取 length + finals 候選（善用 index），然後 Python 拆 shared / pure
        # 避免原本的 or_ contains 子句導致較慢的查詢計劃
        qy = (db.query(Word)
              .filter(
                  _length_filter(len_q),
                  Word.finals == fin_json,
                  Word.code == c  # strict to this code, so all results have the target's codes
              )
              .order_by(Word.char, Word.jyutping)
              .limit(50))  # cap for instant
        candidates = _deduplicate_words(qy.all())
        shared_ws = [w for w in candidates if any(ch in w.char for ch in q_chars)]
        shared_set = set(shared_ws)  # for fast lookup
        pure_ws = [w for w in candidates if w not in shared_set]

        # shared (有共用字 + 同韻)
        for w in shared_ws:
            if w.char not in seen:
                seen.add(w.char)
                results.append(_serialize_word(w, display_text=w.char, query_text=w.char, result_type="word"))

        # 純同 rhyme（不同字）
        if query_emb:
            scored = []
            for w in pure_ws[:200]:  # cap re-rank
                w_emb = _load_json_list(getattr(w, "embedding", None) or "[]")
                score = cosine_similarity(query_emb, w_emb) if w_emb else 0.0
                if w.char not in seen:
                    scored.append((score, w))
            scored.sort(key=lambda x: -x[0])
            to_add = [w for s, w in scored]
        else:
            to_add = [w for w in pure_ws if w.char not in seen]
        for w in to_add:
            seen.add(w.char)
            results.append(_serialize_word(w, display_text=w.char, query_text=w.char, result_type="word"))

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
                    from utils import update_word_in_cache
                    update_word_in_cache(ref_row.char, getattr(ref_row, "code", ""), getattr(ref_row, "jyutping", ""), getattr(ref_row, "finals", None), getattr(ref_row, "initials", None), getattr(ref_row, "length", None))
                except Exception:
                    pass
    ref_val = ref_fins[0] if ref_fins else None

    if ref_val is not None:
        for c in codes:
            # 取該 code + 同長度的候選（數量有限），用小迴圈做 position 檢查（無法輕易全推給簡單 ORM）
            cands = (db.query(Word)
                     .filter(
                         _length_filter(len_q),
                         Word.code == c
                     )
                     .order_by(Word.char, Word.jyutping)
                     .limit(50)
                     .all())
            matched = []
            for w in cands:
                try:
                    wf = _load_json_list(w.finals)
                    if len(wf) > ref_pos and wf[ref_pos] == ref_val:
                        matched.append(w)
                except (TypeError, json.JSONDecodeError):
                    pass
            for w in _deduplicate_words(matched):
                if w.char not in seen:
                    seen.add(w.char)
                    results.append(_serialize_word(w, display_text=w.char, query_text=w.char, result_type="word"))

    # 6. 最後：q=24 / q=29 風格（只同 code 的詞，移除未指定 code 以避免無關結果如 "0尊"）
    # 當有 codes 時嚴格只取 target 的 codes；無 codes 時才包含未指定（相容舊行為）
    if codes:
        broad_cond = or_(*[Word.code == c for c in codes])
    else:
        broad_cond = or_(Word.code == '', Word.code.is_(None))
    qy = (db.query(Word)
          .filter(
              _length_filter(len_q),
              broad_cond
          )
          .order_by(Word.char, Word.jyutping)
          .limit(100))  # cap for instant; deep pages via load more if needed
    for w in _deduplicate_words(qy.all()):
        if w.char not in seen:
            seen.add(w.char)
            results.append(_serialize_word(w, display_text=w.char, query_text=w.char, result_type="word"))

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
        # Sync to mem cache immediately so subsequent mask/hybrid/"門0" etc see it without restart or full preload.
        try:
            from utils import update_word_in_cache
            update_word_in_cache(
                db_word.char,
                db_word.code or "",
                db_word.jyutping or "",
                db_word.finals,
                db_word.initials,
                db_word.length,
            )
        except Exception:
            pass
        return [db_word]
    except Exception as e:
        db.rollback()
        print(f"[ensure] DB insert failed for {text}: {e}")
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


@router.get("/search", response_model=list[WordRead])
@router.get("/search/", response_model=list[WordRead])
def search_words(
    q: str = None,
    code: str = None,
    char: str = None,
    mode: str = "m2",
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
        # Reuses _ensure + embedding + (preloaded) matrix + optional static thesaurus.
        return handle_syn_ant_search(q, db)

    if "=" in q:
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

        # Cap candidates (Python-side position match for = syntax)
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

        return _deduplicate_words(filtered[offset:offset + limit])

    hybrid_match = re.match(r'^(\d+)([一-龥]+)(\d*)$', q)
    if hybrid_match:
        num_prefix = hybrid_match.group(1)
        ref_chars = hybrid_match.group(2)
        num_suffix = hybrid_match.group(3)

        full_code = num_prefix + num_suffix
        ref_pos = max(0, len(num_prefix) - 1)

        query = db.query(Word)
        query = _apply_code_filter(query, full_code, mode)
        query = query.filter(_length_filter(len(full_code)))

        # Prefer cache for short full_code lengths (instant, pre-parsed); fallback with cap for correctness.
        candidates = get_words_for_length(len(full_code))
        used_cache = bool(candidates)
        if not used_cache:
            candidates = query.order_by(Word.char).limit(2000).all()

        target_finals = [None] * len(full_code)
        for i, c in enumerate(ref_chars):
            pos = ref_pos + i
            if 0 <= pos < len(full_code):
                meta = get_char_meta(c)
                t = None
                if meta and meta.get("finals"):
                    try:
                        target_finals[pos] = (meta["finals"][0] if meta["finals"] else None)
                    except Exception:
                        pass
                else:
                    t = db.query(Word).filter(Word.char == c).first()
                    if t and t.finals:
                        try:
                            fl = json.loads(t.finals)
                            target_finals[pos] = fl[0] if fl else None
                        except (TypeError, json.JSONDecodeError):
                            pass
                    if t:
                        try:
                            from utils import update_word_in_cache
                            update_word_in_cache(t.char, getattr(t, "code", ""), getattr(t, "jyutping", ""), getattr(t, "finals", None), getattr(t, "initials", None), getattr(t, "length", None))
                        except Exception:
                            pass

        filtered = []
        for word in candidates:
            if used_cache:
                if not word.get("finals"):
                    continue
                try:
                    word_finals = word.get("finals") or []
                except Exception:
                    continue
            else:
                if not word.finals:
                    continue
                try:
                    word_finals = json.loads(word.finals)
                except (TypeError, json.JSONDecodeError):
                    continue
            if len(word_finals) != len(full_code):
                continue

            match_ok = True
            for i, tf in enumerate(target_finals):
                if tf is None:
                    continue
                if i >= len(word_finals) or word_finals[i] != tf:
                    match_ok = False
                    break
            if match_ok:
                filtered.append(word)

        return filtered[offset:offset + limit]

    # Wildcard "_" search: "_" 表示該位置接受「任何 code（tone）」，只以對應位置的「押韻 (finals)」匹配 literal 漢字。
    # 例如 "_識_" → 長度3、第二個字 final 與「識」相同的所有詞；"好_" → 長度2、第一個字 final 與「好」相同。
    # 僅在 Python 端用 re 解析輸入 q（偵測 '_' 與模式），DB 查詢只用 length filter + 之後 Python position loop 比對 finals（完全不使用 regex 或複雜 expr 於 DB）。
    # 重用 hybrid 位置匹配的 same style（target_finals 預計算 + 迴圈檢查），效能特性一致。
    # Generalized wildcard + mixed support (digits + _ + chars), e.g. "_識_", "好_", "2好_", "_2識3", "好_2" etc.
    # - The entire q string acts as a position mask; len(q) == target word char length (N).
    # - Per position in the mask:
    #     digit (0-9): the word's code[pos] must match this digit (or m1/m2 variant per current mode)
    #     '_': any code at this position (the "wildcard" for code/tone)
    #     chars: position rhyme match using this chars's finals[0]; also used for priority sort
    # - DB query: **only** Word.length == N   (simple indexed filter, no regex, no complex expr — complies with friend feedback).
    # - All code-digit checks + finals position matching done in Python (same style as existing hybrid).
    # - Special sorting: results with exact char matches at the chars literal positions in the query mask are prioritized first
    #   (e.g. for "_識_", words where the 2nd char *is literally "識"* come before other words that only share the 'ik' final at pos 1).
    # - regex only for parsing the user input q (detect mask + classify positions). Never pushed to DB.
    # Support mixed hanzi+digit patterns (e.g. "門0", "好23") in addition to explicit _ wildcards.
    # "門0" means: pos0 rhymes with 門 (use 門's final at that position), pos1 code[pos]== '0' (or m1/m2 variant).
    # The generalized mask logic below already handles digits (for exact code pos), hanzi (for rhyme/pos final match),
    # and _ (any at pos). We now enter it for any mixed hanzi+digit mask (no _ required).
    is_potential_mask = bool(re.match(r"^[0-9_一-龥]+$", q))
    contains_wild_or_digit = any(c == '_' or c.isdigit() for c in q)
    contains_hanzi = any(not c.isdigit() and c != '_' for c in q)
    if is_potential_mask and (contains_wild_or_digit and contains_hanzi or "_" in q):
        mask = q
        expected_len = len(mask)
        if expected_len == 0:
            return []

        target_finals = [None] * expected_len
        required_codes = [None] * expected_len  # digit str or None
        literal_positions: list[tuple[int, str]] = []  # (pos, chars) for priority sort — exact char matches at these positions win

        for i, ch in enumerate(mask):
            if ch == "_":
                continue
            elif ch.isdigit():
                required_codes[i] = ch
            else:
                # chars: collect final for rhyme + record for "exact literal" priority.
                # Use in-mem cache first (preloaded + pre-parsed) for instant; fallback to DB/ensure only on miss.
                # After ensure, update cache so this new literal participates in future same-length masks instantly.
                meta = get_char_meta(ch)
                ref = None
                if meta and meta.get("finals"):
                    target_finals[i] = meta["finals"][0] if meta["finals"] else None
                    ref = meta  # for append below
                else:
                    ref = db.query(Word).filter(Word.char == ch).first()
                    if not ref:
                        refs = _ensure_word_in_db(db, ch)
                        ref = refs[0] if refs else None
                    if ref and ref.finals:
                        try:
                            fl = json.loads(ref.finals)
                            target_finals[i] = fl[0] if fl else None
                        except (TypeError, json.JSONDecodeError):
                            pass
                    # Sync to cache for this + future queries (new hanzi from ensure now in mem for mask)
                    if ref:
                        try:
                            from utils import update_word_in_cache
                            update_word_in_cache(
                                ref.char,
                                getattr(ref, "code", "") or "",
                                getattr(ref, "jyutping", "") or "",
                                getattr(ref, "finals", None),
                                getattr(ref, "initials", None),
                                getattr(ref, "length", None),
                            )
                        except Exception:
                            pass  # non-fatal; cache miss just means next time falls back again
                literal_positions.append((i, ch))

        # Prefer preloaded in-mem cache (populated at startup with pre-parsed finals; no json.loads, no full row materialization).
        # This makes length=N broad filters for mask/hybrid/"門0" etc. instant even for N=2 with 10k+ entries.
        # If cache empty (preload not done yet, or test :memory: DB), fallback to the original DB path (correctness preserved).
        candidates = get_words_for_length(expected_len)
        used_cache = bool(candidates)
        if not used_cache:
            # DB layer: plain length filter only. Any _ (or mixed codes) means we cannot safely narrow...
            # (kept verbatim for fallback path + comments explaining why no cap)
            query = db.query(Word).filter(_length_filter(expected_len))
            candidates = query.order_by(Word.char).all()

        filtered = []
        for word in candidates:
            if used_cache:
                # dict entries from cache: already pre-parsed, no json, direct access
                if not word.get("finals") or not word.get("code"):
                    continue
                word_finals = word.get("finals") or []
                word_code_str = word.get("code") or ""
                # For return we keep the dict (dedup supports it); downstream only needs .char or ["char"]
            else:
                if not word.finals or not word.code:
                    continue
                try:
                    word_finals = json.loads(word.finals)
                except (TypeError, json.JSONDecodeError):
                    continue
                word_code_str = word.code or ""
            if len(word_finals) != expected_len or len(word_code_str) != expected_len:
                continue

            match_ok = True
            for i in range(expected_len):
                # Digit-specified code position (respect mode via variants for m1/m2)
                req_digit = required_codes[i]
                if req_digit is not None:
                    allowed = get_code_variants(req_digit, mode)
                    if i >= len(word_code_str) or word_code_str[i] not in allowed:
                        match_ok = False
                        break
                # Hanzi-specified rhyme position
                tf = target_finals[i]
                if tf is not None:
                    if i >= len(word_finals) or word_finals[i] != tf:
                        match_ok = False
                        break
            if match_ok:
                filtered.append(word)

        # Priority sort for the requested "sorting method":
        # Exact matches on the literal chars supplied in the query mask come first.
        # (e.g. _識_ → "*識*" words before other ik-rhyme words at that position.)
        # Secondary: lexical by char (stable-ish within priority groups).
        # Supports both ORM Word (fallback) and dict (cache path).
        def _wildcard_priority_key(w):
            if isinstance(w, dict):
                char = w.get("char", "") or ""
                jy = w.get("jyutping", "") or ""
            else:
                char = getattr(w, "char", "") or ""
                jy = getattr(w, "jyutping", "") or ""
            exact_count = sum(1 for pos, ch in literal_positions if pos < len(char) and char[pos] == ch)
            return (-exact_count, char, jy)

        filtered.sort(key=_wildcard_priority_key)

        return _deduplicate_words(filtered)[offset:offset + limit]

    if q.isdigit():
        query = db.query(Word)
        query = _apply_code_filter(query, q, mode)
        query = query.filter(_length_filter(len(q)))
        results = query.order_by(Word.char).offset(offset).limit(limit).all()
        return _deduplicate_words(results)

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
        return built[offset:offset + limit]

    if re.search(r'[a-zA-Z]', q):
        # Cap to keep instant even for broad jyut fragments (rare path); slice after.
        results = db.query(Word).filter(Word.jyutping.ilike(f"%{q}%")).order_by(Word.char).limit(500).all()
        return _deduplicate_words(results)[offset:offset + limit]

    return []


# ==================== Independent 近義/反義詞查找 (mode='syn') ====================
# Early branched from search_words. Pure hanzi focus. No code/length/final logic.
# Blend: static vendor (cilin high-quality groups + antisem/guotong clean tables) + our preloaded emb matrix (vectorized).
# Optional: near-synonym package (try/except) for LLM MLM generation when installed & cached.
# Returns items compatible with WordRead (char+code+jyutping required by the endpoint response_model)
# plus the extra "relation" field that the syn-mode frontend uses to split columns.
# code/jyutping are empty for syn results (not relevant in this mode).
# Always fast after preload (<0.1s matrix @); _ensure ensures new query words get embedding.

def _syn_result(char: str, relation: str) -> dict:
    """Helper to produce a dict that satisfies the endpoint's WordRead response model
    while carrying the 'relation' flag the syn frontend relies on.
    code/jyutping are meaningless for syn results so left empty.
    """
    return {
        "char": char,
        "code": "",
        "jyutping": "",
        "display_text": char,
        "query_text": char,
        "result_type": "syn",
        "relation": relation,
    }


def handle_syn_ant_search(q: str, db: "Session") -> list[dict]:
    if not q or not re.search(r'[\u4e00-\u9fff]', q):
        return []
    q = q.strip()

    # Ensure the query word exists (and has embedding) so it participates in matrix / future clicks
    _ensure_word_in_db(db, q)

    q_emb = get_text_embedding(q)
    if not q_emb:
        # Fallback: at least echo the query as syn (no ants)
        return [_syn_result(q, "syn")]

    # Static thesaurus first (curated, high precision when data present)
    try:
        from utils import get_synonyms, get_antonyms, get_synonym_index
        static_syns = get_synonyms(q)[:12]
        static_ants = get_antonyms(q)[:8]
    except Exception:
        static_syns = []
        static_ants = []

    chars, emb_mat = get_synonym_index()
    if not chars or emb_mat is None or len(chars) == 0:
        # Pure static or minimal echo
        out = []
        seen = set()
        for w in static_syns:
            if w not in seen:
                seen.add(w)
                out.append(_syn_result(w, "syn"))
        for w in static_ants:
            if w not in seen:
                seen.add(w)
                out.append(_syn_result(w, "ant"))
        if not out:
            out = [_syn_result(q, "syn")]
        return out

    import numpy as np
    qv = np.asarray(q_emb, dtype=np.float32)
    # emb_mat rows are already normalized (by preload); qv from get_text_embedding is also normalized
    sims = emb_mat @ qv   # (N,)

    k = 12
    syn_thresh = 0.55
    ant_k = 8
    ant_max = 0.28

    # Near synonyms: high sim, exclude self, prefer static then vector
    order = np.argsort(sims)[::-1]
    vec_syns = []
    for idx in order:
        if len(vec_syns) >= k:
            break
        c = chars[idx]
        if c == q:
            continue
        s = float(sims[idx])
        if s >= syn_thresh:
            vec_syns.append(c)

    # Blend: static first (curated), then fill with high vec (dedup)
    syns = []
    seen = set()
    for w in static_syns + vec_syns:
        if w not in seen and w != q:
            seen.add(w)
            syns.append(_syn_result(w, "syn"))
            if len(syns) >= k:
                break

    # Antonyms
    ants = []
    seen_ant = set()
    for w in static_ants:
        if w not in seen_ant and w != q:
            seen_ant.add(w)
            ants.append(_syn_result(w, "ant"))
            if len(ants) >= ant_k:
                break

    # Vector low-sim as weak antonym fallback / supplement (only if few static)
    if len(ants) < ant_k:
        low_order = np.argsort(sims)
        for idx in low_order:
            if len(ants) >= ant_k:
                break
            c = chars[idx]
            if c == q or c in seen_ant:
                continue
            s = float(sims[idx])
            if s <= ant_max:
                seen_ant.add(c)
                ants.append(_syn_result(c, "ant"))

    # Optional near-synonym (5th GitHub) — LLM MLM gen when available (heavy models, first-run HF download)
    # Guarded: never blocks core path. If present and FLAG set, union a few more.
    try:
        import os
        if os.environ.get("FLAG_MLM_ANTONYM") == "1":
            from near_synonym import mlm_synonyms, mlm_antonyms  # type: ignore
            for w in (mlm_synonyms(q) or [])[:6]:
                ww = w[0] if isinstance(w, (list, tuple)) else w
                if ww and ww != q and ww not in seen:
                    seen.add(ww)
                    syns.append(_syn_result(ww, "syn"))
            for w in (mlm_antonyms(q) or [])[:4]:
                ww = w[0] if isinstance(w, (list, tuple)) else w
                if ww and ww != q and ww not in seen_ant:
                    seen_ant.add(ww)
                    ants.append(_syn_result(ww, "ant"))
    except Exception:
        pass  # silent — feature works without this package

    # Final dedup + order (static/curated first already reflected)
    out = []
    seen_final = set()
    for item in syns + ants:
        c = item["char"]
        if c not in seen_final:
            seen_final.add(c)
            out.append(item)
    return out[: (k + ant_k)]
