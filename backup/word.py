from fastapi import APIRouter, Depends, HTTPException
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

@router.get("/search", response_model=list[WordRead])   # 無斜線
@router.get("/search/", response_model=list[WordRead])  # 有斜線
def search_words(
    q: str = None,
    code: str = None,
    char: str = None,
    mode: str = "m2",
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_d
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
    query = db.query(Word)

    # ==================== 1. 等號韻搜尋 (最高優先) ====================
    if "=" in q:
        import re
        import json
        
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

        if code_part:
            variants = get_code_variants(code_part, mode)
            query = query.filter(Word.code.in_(variants))

        # 精確字數 + 完整序列匹配
        candidates = query.filter(
            Word.char.op('REGEXP')(rf'^[\u4e00-\u9fff]{{{target_length}}}$')
        ).order_by(Word.char).all()

        filtered = []
        for word in candidates:
            try:
                if is_rhyme_match and word.finals:
                    if json.loads(word.finals) == target_list:
                        filtered.append(word)
                elif not is_rhyme_match and word.initials:
                    if json.loads(word.initials) == target_list:
                        filtered.append(word)
            except:
                continue

        print(f"[{mode}] 等號韻完整匹配 → 目標: {target_str} | 長度: {target_length} | 找到 {len(filtered)} 筆")
        return filtered[offset:offset + limit]

    # ==================== 2. 純數字搜尋 ====================
    if q.isdigit():
        variants = get_code_variants(q, mode)
        query = query.filter(Word.code.in_(variants))
        print(f"純數字搜尋: {q} → variants: {variants}")
        return query.order_by(Word.char).offset(offset).limit(limit).all()

    # ==================== 3. 數字 + 漢字 混合搜尋 (如 23就) ====================
    import re
    hybrid_match = re.match(r'^(\d+)([\u4e00-\u9fa5]+)$', q)
    if hybrid_match:
        num_part = hybrid_match.group(1)
        char_part = hybrid_match.group(2)
        
        variants = get_code_variants(num_part, mode)
        query = query.filter(Word.code.in_(variants))
        
        # 目前先只做 code 過濾（可後續再加尾字韻母過濾）
        print(f"混合搜尋: 數字={num_part} + 漢字={char_part}")
        return query.order_by(Word.char).offset(offset).limit(limit).all()

    # ==================== 4. 純漢字搜尋 ====================
    if re.match(r'^[\u4e00-\u9fa5]+$', q):
        query = query.filter(Word.char == q)
        return query.all()

    # 其他情況
    return []