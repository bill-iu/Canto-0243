from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import re
import json

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
    import re
    import json
    from sqlalchemy import func

    if not q:
        query = db.query(Word)
        if code:
            variants = get_code_variants(code, mode)
            query = query.filter(Word.code.in_(variants))
        if char:
            query = query.filter(Word.char == char)
        results = query.order_by(Word.char).offset(offset).limit(limit).all()
        # 去重（以 id 為主）
        seen = set()
        unique = []
        for w in results:
            if w.id not in seen:
                seen.add(w.id)
                unique.append(w)
        return unique

    q = q.strip()

     # ==================== 等號韻搜尋（已修正重複問題版） ====================
    if "=" in q:
        match = re.match(r'^(\d*)(=)?([\u4e00-\u9fa5]+)?(=)?(\d*)$', q)
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

        try:
            target_initials = json.loads(target.initials) if target.initials else []
            target_finals = json.loads(target.finals) if target.finals else []
        except:
            return []

        target_length = len(target_str)
        expected_length = len(left_code) + len(right_code) or target_length

        query = db.query(Word)
        if full_code:
            variants = get_code_variants(full_code, mode)
            query = query.filter(Word.code.in_(variants))

        query = query.filter(func.length(Word.char) == expected_length)
        is_rhyme_match = right_equal
        start_pos = max(0, len(left_code) - target_length)

        if start_pos == 0 and target_length == expected_length:
            if is_rhyme_match:
                target_json = json.dumps(target_finals)
                query = query.filter(Word.finals == target_json)
            else:
                target_json = json.dumps(target_initials)
                query = query.filter(Word.initials == target_json)

            results = query.order_by(Word.char).offset(offset).limit(limit).all()

            # === 使用 char 去重，解決同字不同 code 的重複問題 ===
            seen = set()
            unique_results = []
            for word in results:
                if word.char not in seen:
                    seen.add(word.char)
                    unique_results.append(word)
            return unique_results

        # 複雜情況走 Python 迴圈（也建議加上 char 去重）
        candidates = query.order_by(Word.char).all()
        filtered = []
        for word in candidates:
            try:
                word_initials = json.loads(word.initials) if word.initials else []
                word_finals = json.loads(word.finals) if word.finals else []

                if is_rhyme_match:
                    match_ok = True
                    for i in range(target_length):
                        pos = start_pos + i
                        if pos < len(word_finals) and i < len(target_finals):
                            if target_finals[i] and target_finals[i] != word_finals[pos]:
                                match_ok = False
                                break
                    if match_ok:
                        filtered.append(word)
                else:
                    match_ok = True
                    for i in range(target_length):
                        pos = start_pos + i
                        if pos < len(word_initials) and i < len(target_initials):
                            if target_initials[i] and target_initials[i] != word_initials[pos]:
                                match_ok = False
                                break
                    if match_ok:
                        filtered.append(word)
            except:
                continue

        # Python 迴圈結果也做 char 去重
        seen = set()
        unique_filtered = []
        for word in filtered[offset:offset + limit]:
            if word.char not in seen:
                seen.add(word.char)
                unique_filtered.append(word)
        return unique_filtered
        
    # ==================== 2. 位置指定混合搜尋 ====================
    hybrid_match = re.match(r'^(\d+)([\u4e00-\u9fa5]+)(\d*)$', q)
    if hybrid_match:
        num_prefix = hybrid_match.group(1)
        ref_chars = hybrid_match.group(2)
        num_suffix = hybrid_match.group(3)

        full_code = num_prefix + num_suffix
        ref_pos = max(0, len(num_prefix) - 1)

        variants = get_code_variants(full_code, mode)
        query = db.query(Word).filter(Word.code.in_(variants))
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
                    except:
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
            except:
                continue

        return filtered[offset:offset + limit]

    # ==================== 3. 純數字 ====================
    if q.isdigit():
        variants = get_code_variants(q, mode)
        query = db.query(Word).filter(Word.code.in_(variants))
        query = query.filter(func.length(Word.char) == len(q))
        results = query.order_by(Word.char).offset(offset).limit(limit).all()
        seen = set()
        unique = [w for w in results if not (w.char in seen or seen.add(w.char))]
        return unique

    if re.match(r'^[\u4e00-\u9fa5]+$', q):
        results = db.query(Word).filter(Word.char == q).all()
        seen = set()
        unique = [w for w in results if not (w.char in seen or seen.add(w.char))]
        return unique

    return []