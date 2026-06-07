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
    if not q:
        query = db.query(Word)
        if code:
            variants = get_code_variants(code, mode)
            query = query.filter(Word.code.in_(variants))
        if char:
            query = query.filter(Word.char == char)
        return query.order_by(Word.char).offset(offset).limit(limit).all()

    q = q.strip()

    # 1. 等號韻搜尋 (香港=)
    if "=" in q:
        # ... (保持你目前等號韻的邏輯不變，這部分先不改)
        parts = q.split("=", 1)
        left = parts[0].strip()
        right = parts[1].strip() if len(parts) > 1 else ""

        code_part = None
        code_match = re.match(r'^(\d+)', left)
        if code_match:
            code_part = code_match.group(1)
            left = left[len(code_part):].strip()

        is_rhyme_match = len(right) == 0
        target_str = right if right else left

        if not target_str:
            return []

        target = db.query(Word).filter(Word.char == target_str).first()
        if not target:
            return []

        try:
            if is_rhyme_match:
                target_list = json.loads(target.finals)
            else:
                target_list = json.loads(target.initials)
            target_length = len(target_list)
        except:
            return []

        query = db.query(Word)
        if code_part:
            variants = get_code_variants(code_part, mode)
            query = query.filter(Word.code.in_(variants))

        candidates = query.filter(
            Word.char.op('REGEXP')(rf'^[\u4e00-\u9fff]{{{target_length}}}$')
        ).order_by(Word.char).all()

        filtered = []
        for word in candidates:
            try:
                if is_rhyme_match and word.finals and json.loads(word.finals) == target_list:
                    filtered.append(word)
                elif not is_rhyme_match and word.initials and json.loads(word.initials) == target_list:
                    filtered.append(word)
            except:
                continue
        return filtered[offset:offset + limit]

    # 2. 純數字搜尋
    if q.isdigit():
        variants = get_code_variants(q, mode)
        query = db.query(Word).filter(Word.code.in_(variants))
        return query.order_by(Word.char).offset(offset).limit(limit).all()

    # 3. 混合搜尋：數字 + 漢字 (23開、230開 等)
    import re
    hybrid_match = re.match(r'^(\d+)([\u4e00-\u9fa5]+)$', q)
    if hybrid_match:
        num_part = hybrid_match.group(1)
        char_part = hybrid_match.group(2)
        
        # 先過濾 code
        variants = get_code_variants(num_part, mode)
        query = db.query(Word).filter(Word.code.in_(variants))

        # 取得目標尾字的最後一個韻母
        target_char = char_part[-1]
        target = db.query(Word).filter(Word.char == target_char).first()
        target_final = None
        if target and target.finals:
            try:
                finals_list = json.loads(target.finals)
                if finals_list:
                    target_final = finals_list[-1]
            except:
                pass

        # 取出候選詞
        candidates = query.order_by(Word.char).all()

        # 過濾：尾字韻母必須相同
        filtered = []
        for word in candidates:
            if word.finals:
                try:
                    finals_list = json.loads(word.finals)
                    if finals_list and finals_list[-1] == target_final:
                        filtered.append(word)
                except:
                    continue

        print(f"混合搜尋: {q} | 目標尾韻: {target_final} | 找到 {len(filtered)} 筆")
        return filtered[offset:offset + limit]

    # 4. 純漢字
    if re.match(r'^[\u4e00-\u9fa5]+$', q):
        return db.query(Word).filter(Word.char == q).all()

    return []