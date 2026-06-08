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

    # ==================== 1. 等號韻搜尋 (香港=) ====================
    if "=" in q:
        # ...（保持原本等號韻邏輯不變）
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

        filtered = [w for w in candidates if 
                    ((is_rhyme_match and w.finals and json.loads(w.finals) == target_list) or
                     (not is_rhyme_match and w.initials and json.loads(w.initials) == target_list))]
        return filtered[offset:offset + limit]

       # ==================== 2. 位置指定混合搜尋 ====================
    hybrid_match = re.match(r'^(\d+)([\u4e00-\u9fa5]+)(\d*)$', q)
    if hybrid_match:
        num_prefix = hybrid_match.group(1)
        ref_chars = hybrid_match.group(2)
        num_suffix = hybrid_match.group(3)

        full_code = num_prefix + num_suffix
        print(f"位置指定搜尋: {q} → code={full_code} | 參考字={ref_chars}")

        variants = get_code_variants(full_code, mode)
        query = db.query(Word).filter(Word.code.in_(variants))

        candidates = query.order_by(Word.char).all()

        # === 關鍵修正：漢字位置 = len(num_prefix) - 1 ===
        ref_pos = len(num_prefix) - 1   # 這裡改成 -1
        if ref_pos < 0:
            ref_pos = 0

        target_finals = [None] * len(full_code)

        for i, c in enumerate(ref_chars):
            pos = ref_pos + i
            if 0 <= pos < len(full_code):
                target = db.query(Word).filter(Word.char == c).first()
                if target and target.finals:
                    try:
                        fl = json.loads(target.finals)
                        target_finals[pos] = fl[0] if fl else None
                    except:
                        pass

        print(f"目標位置韻母: {target_finals}")

        filtered = []
        for word in candidates:
            if not word.finals:
                continue
            try:
                word_finals = json.loads(word.finals)
                if len(word_finals) != len(full_code):
                    continue
                
                match = True
                for i, target_final in enumerate(target_finals):
                    if target_final is None:
                        continue
                    if i >= len(word_finals) or word_finals[i] != target_final:
                        match = False
                        break
                if match:
                    filtered.append(word)
            except:
                continue

        print(f"位置指定搜尋找到 {len(filtered)} 筆結果")
        return filtered[offset:offset + limit]

    # ==================== 3. 純數字 ====================
    if q.isdigit():
        variants = get_code_variants(q, mode)
        query = db.query(Word).filter(Word.code.in_(variants))
        return query.order_by(Word.char).offset(offset).limit(limit).all()

    # 4. 純漢字
    if re.match(r'^[\u4e00-\u9fa5]+$', q):
        return db.query(Word).filter(Word.char == q).all()

    return []