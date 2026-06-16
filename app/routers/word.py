from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.word import Word
from app.schemas.word_schema import WordCreate, WordRead
from app.services.word_db_filters import apply_code_filter
from app.domain.lexicon.ranking import sort_search_results
from app.services.query_dispatch import SearchContext, execute_search, search_words
from app.startup.readiness_gate import require_search_ready
from app.services.word_serializer import deduplicate_words

router = APIRouter(prefix="/words", tags=["words"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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


@router.get("/search", response_model=list[WordRead])
@router.get("/search/", response_model=list[WordRead])
def search_words_endpoint(
    response: Response,
    q: str = None,
    code: str = None,
    char: str = None,
    mode: str = "m1",
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    if not q:
        require_search_ready()
        query = db.query(Word)
        query = apply_code_filter(query, code, mode)
        if char:
            query = query.filter(Word.char == char)
        results = query.all()
        return sort_search_results(deduplicate_words(results))[offset : offset + limit]
    result = execute_search(
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
    if result.total is not None:
        response.headers["X-Search-Total"] = str(result.total)
    if result.hint:
        response.headers["X-Search-Hint"] = result.hint
    if result.cache_path:
        response.headers["X-Search-Cache"] = result.cache_path
    return result.items


@router.get("/{char}", response_model=WordRead)
def get_word(char: str, db: Session = Depends(get_db)):
    word = db.query(Word).filter(Word.char == char).first()
    if word is None:
        raise HTTPException(status_code=404, detail="字詞未找到")
    return word


__all__ = ["router", "get_db", "search_words"]
