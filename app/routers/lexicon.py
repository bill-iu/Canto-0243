"""詞庫勘誤 queue API。"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.lexicon_schema import LexiconCorrectionCreate, LexiconCorrectionQueued
from app.services.lexicon_correction_queue import LexiconCorrectionQueueError, queue_lexicon_correction
from app.utils.jyutping_codec import get_0243_code
from ingest.lexicon_corrections import DEFAULT_TSV

router = APIRouter(prefix="/lexicon", tags=["lexicon"])

_ERROR_STATUS = {
    "duplicate": 409,
    "missing_char": 400,
    "missing_value": 400,
    "invalid_action": 400,
}


def get_corrections_path() -> Path:
    return DEFAULT_TSV


@router.post("/corrections", response_model=LexiconCorrectionQueued)
def queue_correction(
    body: LexiconCorrectionCreate,
    path: Path = Depends(get_corrections_path),
) -> LexiconCorrectionQueued:
    try:
        result = queue_lexicon_correction(
            char=body.char,
            code=body.code,
            jyutping=body.jyutping,
            action=body.action,
            value=body.value,
            note=body.note,
            path=path,
        )
    except LexiconCorrectionQueueError as exc:
        status = _ERROR_STATUS.get(exc.code, 400)
        raise HTTPException(status_code=status, detail=exc.message) from exc

    row = result.row
    return LexiconCorrectionQueued(
        message=result.message,
        pending_count=result.pending_count,
        char=row.char,
        code=row.code,
        jyutping=row.jyutping,
        action=row.action,
        value=row.value,
        note=row.note,
    )


@router.get("/code-preview")
def preview_code(jyutping: str) -> dict[str, str]:
    literal = (jyutping or "").strip()
    if not literal:
        raise HTTPException(status_code=400, detail="請提供粵拼")
    return {"code": get_0243_code(literal)}


__all__ = ["router", "get_corrections_path"]
