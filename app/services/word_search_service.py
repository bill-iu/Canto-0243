from __future__ import annotations

import json
import re
from typing import List, Optional

from sqlalchemy.orm import Session

from utils import get_code_variants, load_json_list

from app.models.word import Word
from app.services.code_aware_ranker import build_code_aware_results
from app.services.mask_search import word_matches_last_final
from app.services.phoneme_lookup import final_options_for_char
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_ensure_service import ensure_word_in_db
from app.services.query_engine import QueryEngine, SearchContext
from app.services.word_serializer import (
    deduplicate_words,
    get_primary_codes,
    get_word_text,
    paginate,
    serialize_page,
    serialize_word,
)

def handle_equals_syntax(q: str, code: Optional[str], mode: str, limit: int, offset: int, db):  # untyped db to avoid FastAPI treating it as a response field during module import
    """Legacy framed equals: left = initial (=锚), right = final (锚=), whole-word template."""
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

    target_rows = db.query(Word).filter(Word.char == target_str).all()
    if not target_rows:
        target_rows = ensure_word_in_db(db, target_str)
    target = target_rows[0] if target_rows else None
    if not target:
        return []

    target_initials = load_json_list(target.initials)
    target_finals = load_json_list(target.finals)

    target_length = len(target_str)
    expected_length = len(left_code) + len(right_code) or target_length

    query = db.query(Word)
    query = apply_code_filter(query, full_code, mode)
    query = query.filter(length_filter(expected_length))
    is_rhyme_match = right_equal
    # Code 夾單字錨（2=我3 / 2我=3）：左碼約束首字、右碼約束尾字，錨點音韻比對首字（pos 0）。
    if target_length == 1 and left_code and right_code:
        start_pos = 0
    else:
        start_pos = max(0, len(left_code) - target_length)

    if start_pos == 0 and target_length == expected_length:
        target_parts = target_finals if is_rhyme_match else target_initials
        target_json = json.dumps(target_parts)
        compare_field = Word.finals if is_rhyme_match else Word.initials
        query = query.filter(compare_field == target_json)

        results = query.order_by(Word.char).offset(offset).limit(limit).all()
        return serialize_page(deduplicate_words(results), offset, limit)

    candidates = query.order_by(Word.char).limit(2000).all()
    filtered = []
    target_parts = target_finals if is_rhyme_match else target_initials
    # Code 夾住錨點（2=我3 / 2我=3）：「我」為聲母/韻母錨，不要求結果含字面錨字。
    phoneme_anchor_only = bool(left_code and right_code)
    for word in candidates:
        char_text = get_word_text(word)
        if not phoneme_anchor_only and target_str and target_str not in char_text:
            continue
        word_parts = load_json_list(word.finals if is_rhyme_match else word.initials)
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

    return serialize_page(deduplicate_words(filtered), offset, limit)

def handle_pure_digit_query(q: str, code: Optional[str], mode: str, limit: int, offset: int, db: "Session") -> List[dict]:
    """處理純數字查詢（如 "23"）。"""
    query = db.query(Word)
    query = apply_code_filter(query, q, mode)
    query = query.filter(length_filter(len(q)))
    results = query.order_by(Word.char).offset(offset).limit(limit).all()
    return [serialize_word(w) for w in deduplicate_words(results)]


def handle_pure_canto_query(q: str, code: Optional[str], mode: str, limit: int, offset: int, db: "Session") -> List[dict]:
    """處理純粵字（漢字）查詢。
    包含自動 _ensure 新詞 + 使用 code-aware 排序建構器。
    """
    # 對純漢字 q，先測試資料庫；若無則用 pycantonese 生成並注入
    raw_targets: List[Word] = []
    if re.search(r'[\u4e00-\u9fff]', q):
        raw_targets = ensure_word_in_db(db, q)
    if not raw_targets:
        raw_targets = db.query(Word).filter(Word.char == q).all()
    target_words = deduplicate_words(raw_targets)
    # 使用 raw 以收集同字不同讀音的全部 code (例如 到 的 4 與 9)
    primary_codes = get_primary_codes(raw_targets) if raw_targets else []

    if target_words:
        # 使用專門的 code-aware 排序（只允許查詢詞自己擁有的 0243 code 與 jyutping 當 header，
        # 各段都用 ORM filter + order_by + 同長度限制，過濾無關結果）
        built = build_code_aware_results(q, raw_targets, db)
        return paginate(built, offset, limit)

    return []


def handle_jyut_fragment_query(q: str, limit: int, offset: int, db: "Session") -> List[dict]:
    """處理粵拼片段查詢（含字母的）。"""
    # Cap to keep instant even for broad jyut fragments (rare path); slice after.
    results = db.query(Word).filter(Word.jyutping.ilike(f"%{q}%")).order_by(Word.char).limit(500).all()
    return paginate(deduplicate_words(results), offset, limit)


def words_for_relation_chars(
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
        query = query.filter(Word.code.in_(variants), length_filter(len(code_prefix)))

    words = query.all()
    words.sort(key=lambda w: (char_order.get(w.char or "", 10**9), w.code or "", w.jyutping or ""))
    return serialize_page(words, offset, limit, result_type="word")


def handle_relation_lookup_syntax(
    parsed: dict,
    mode: str,
    limit: int,
    offset: int,
    db: Session,
) -> List[dict]:
    from app.services.syn_ant_service import search_relation_chars

    word = parsed["word"]
    relation_type = parsed["kind"]
    ensure_word_in_db(db, word)
    ranked_chars = search_relation_chars(db, word, relation_type)
    return words_for_relation_chars(
        db,
        ranked_chars,
        code_prefix=parsed.get("code_prefix"),
        mode=mode,
        limit=limit,
        offset=offset,
    )


def handle_antonym_compound_syntax(
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

    query = db.query(Word).filter(Word.char.in_(list(candidates)), length_filter(2))
    code_prefix = parsed.get("code_prefix")
    if code_prefix:
        variants = get_code_variants(code_prefix, mode)
        query = query.filter(Word.code.in_(variants))

    last_final_options: Optional[set[str]] = None
    rhyme_char = parsed.get("rhyme_char")
    if rhyme_char:
        last_final_options = final_options_for_char(rhyme_char, db)
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
        if not word_matches_last_final(word, last_final_options):
            continue
        if ch in seen_chars:
            continue
        seen_chars.add(ch)
        results.append(word)

    return serialize_page(results, offset, limit, result_type="word")


def search_words(
    q: str = None,
    code: str = None,
    char: str = None,
    mode: str = "m1",
    limit: int = 100,
    offset: int = 0,
    *,
    db: Session,
):
    return QueryEngine().execute(
        SearchContext(
            q=q,
            code=code,
            char=char,
            mode=mode,
            limit=limit,
            offset=offset,
            db=db,
        )
    )


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
    ensure_word_in_db(db, q)
    return search_syn_ant(db, q, limit=limit, offset=offset)