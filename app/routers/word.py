import json
import re
from typing import Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, literal, or_
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.word import Word
from app.schemas.word_schema import WordCreate, WordRead
from utils import get_0243_code, get_code_variants

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
        if word.char not in seen:
            seen.add(word.char)
            unique.append(word)
    return unique


def _load_json_list(value: Optional[object]) -> List[object]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


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


def _build_similarity_query(db: Session, q: str, target_word: Optional[Word]):
    if not target_word:
        return db.query(Word).order_by(Word.char, Word.code, Word.jyutping)

    target_code = _get_word_sort_code(target_word)
    target_finals_json = json.dumps(_load_json_list(target_word.finals))

    query = db.query(Word).filter(Word.char != q)

    shared_char_conditions = [func.instr(Word.char, char) > 0 for char in dict.fromkeys(q) if char]
    if shared_char_conditions:
        shared_char_expr = or_(*shared_char_conditions)
    else:
        shared_char_expr = literal(False)

    same_rhyme_expr = Word.finals == target_finals_json
    same_code_expr = Word.code == target_code if target_code else literal(True)
    primary_rank = case(
        ((shared_char_expr) & same_rhyme_expr, 0),
        (same_rhyme_expr, 1),
        else_=2,
    )
    same_code_rank = case((same_code_expr, 0), else_=1)
    return query.order_by(primary_rank, same_code_rank, Word.char, Word.code, Word.jyutping)


def _build_character_search_results(q: str, words: List[Word], related_words: Optional[List[Word]] = None) -> List[dict]:
    results: List[dict] = []
    codes = []
    jyutpings = []

    for word in words:
        code_value = word.code or get_0243_code(word.jyutping or "") or ""
        if code_value and code_value not in codes:
            codes.append(code_value)
        if word.jyutping and word.jyutping not in jyutpings:
            jyutpings.append(word.jyutping)

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

    for jyutping_value in jyutpings:
        results.append({
            "char": jyutping_value,
            "code": "",
            "jyutping": jyutping_value or "",
            "display_text": jyutping_value,
            "query_text": jyutping_value,
            "result_type": "jyutping",
            "id": None,
        })

    seen_chars = set()
    for word in _deduplicate_words(words):
        if word.char not in seen_chars:
            seen_chars.add(word.char)
            results.append(_serialize_word(word, display_text=word.char, query_text=word.char, result_type="word"))

    for word in related_words or []:
        if word.char not in seen_chars:
            seen_chars.add(word.char)
            results.append(_serialize_word(word, display_text=word.char, query_text=word.char, result_type="word"))

    return results


@router.post("/", response_model=WordRead)
def create_word(word: WordCreate, db: Session = Depends(get_db)):
    db_word = Word(**word.dict())
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
        query = query.filter(func.length(Word.char) == expected_length)
        is_rhyme_match = right_equal
        start_pos = max(0, len(left_code) - target_length)

        if start_pos == 0 and target_length == expected_length:
            target_parts = target_finals if is_rhyme_match else target_initials
            target_json = json.dumps(target_parts)
            compare_field = Word.finals if is_rhyme_match else Word.initials
            query = query.filter(compare_field == target_json)

            results = query.order_by(Word.char).offset(offset).limit(limit).all()
            return _deduplicate_words(results)

        candidates = query.order_by(Word.char).all()
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
        query = query.filter(func.length(Word.char) == len(full_code))

        candidates = query.order_by(Word.char).all()

        target_finals = [None] * len(full_code)
        for i, c in enumerate(ref_chars):
            pos = ref_pos + i
            if 0 <= pos < len(full_code):
                t = db.query(Word).filter(Word.char == c).first()
                if t and t.finals:
                    try:
                        fl = json.loads(t.finals)
                        target_finals[pos] = fl[0] if fl else None
                    except (TypeError, json.JSONDecodeError):
                        pass

        filtered = []
        for word in candidates:
            if not word.finals:
                continue
            try:
                word_finals = json.loads(word.finals)
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
            except (TypeError, json.JSONDecodeError):
                continue

        return filtered[offset:offset + limit]

    if q.isdigit():
        query = db.query(Word)
        query = _apply_code_filter(query, q, mode)
        query = query.filter(func.length(Word.char) == len(q))
        results = query.order_by(Word.char).offset(offset).limit(limit).all()
        return _deduplicate_words(results)

    exact_matches = db.query(Word).filter(Word.char == q).all()
    if exact_matches:
        target_word = exact_matches[0]
        related_results = _build_similarity_query(db, q, target_word).offset(offset).limit(limit).all()
        related_results = _deduplicate_words(related_results)
        return _build_character_search_results(q, [target_word], related_results)[offset:offset + limit]

    if re.search(r'[a-zA-Z]', q):
        results = db.query(Word).filter(Word.jyutping.ilike(f"%{q}%")) .order_by(Word.char).all()
        return _deduplicate_words(results)[offset:offset + limit]

    return []
