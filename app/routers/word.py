import json
import re
from typing import Iterable, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.word import Word
from app.schemas.word_schema import WordCreate, WordRead
from utils import get_code_variants

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

    if re.match(r'^[一-龥]+$', q):
        results = db.query(Word).filter(Word.char == q).all()
        return _deduplicate_words(results)

    return []
