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

    if not q:
        query = db.query(Word)
        if code:
            variants = get_code_variants(code, mode)
            query = query.filter(Word.code.in_(variants))
        if char:
            query = query.filter(Word.char == char)
        return query.order_by(Word.char).offset(offset).limit(limit).all()

    q = q.strip()

    # ==================== 1. 等號韻搜尋（傳統 + 位置指定聲母） ====================
    if "=" in q:
        match = re.match(r'^(\d*)(=)?([\u4e00-\u9fa5]+)?(=)?(\d*)$', q)
        if not match:
            return []

        left_code = match.group(1) or ""
        target_str = match.group(3) or ""
        right_code = match.group(5) or ""

        full_code = left_code + right_code
        print(f"等號韻: {q} → code={full_code} | 目標={target_str}")

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

        target_length = len(full_code) or 1
        is_position_mode = bool(left_code or right_code)
        match_position = max(0, len(left_code) - 1) if is_position_mode else 0

        query = db.query(Word)
        if full_code:
            variants = get_code_variants(full_code, mode)
            query = query.filter(Word.code.in_(variants))

        candidates = query.filter(
            Word.char.op('REGEXP')(rf'^[\u4e00-\u9fa5]{{{target_length}}}$')
        ).order_by(Word.char).all()

        print(f"候選詞數量: {len(candidates)} | 位置模式: {is_position_mode} | 匹配位置: {match_position}")

        filtered = []
        for word in candidates:
            try:
                word_initials = json.loads(word.initials) if word.initials else []
                word_finals = json.loads(word.finals) if word.finals else []

                if is_position_mode:
                    # 位置指定聲母模式
                    if (match_position < len(word_initials) and 
                        len(target_initials) > 0 and
                        target_initials[0] == word_initials[match_position]):
                        filtered.append(word)
                else:
                    # 傳統等號韻：完整序列匹配（韻母優先）
                    match_ok = True
                    for i in range(min(len(target_finals), len(word_finals))):
                        if target_finals[i] and target_finals[i] != word_finals[i]:
                            match_ok = False
                            break
                    if match_ok:
                        filtered.append(word)
            except:
                continue

        print(f"等號韻最終找到 {len(filtered)} 筆結果")
        return filtered[offset:offset + limit]

    # ==================== 2. 位置指定混合搜尋（純數字+漢字，匹配韻母） ====================
    hybrid_match = re.match(r'^(\d+)([\u4e00-\u9fa5]+)(\d*)$', q)
    if hybrid_match:
        num_prefix = hybrid_match.group(1)
        ref_chars = hybrid_match.group(2)
        num_suffix = hybrid_match.group(3)

        full_code = num_prefix + num_suffix
        print(f"位置指定混合搜尋: {q} → code={full_code} | 參考字={ref_chars}")

        variants = get_code_variants(full_code, mode)
        query = db.query(Word).filter(Word.code.in_(variants))
        candidates = query.order_by(Word.char).all()

        # 位置計算：漢字出現在第幾個位置
        ref_pos = max(0, len(num_prefix) - 1)

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

        print(f"位置指定混合搜尋找到 {len(filtered)} 筆結果")
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