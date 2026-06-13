from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.routers.word import get_db
from app.schemas.relation_schema import ManualRelationCreate, ManualRelationResult
from app.services.manual_relation_service import (
    ManualRelationError,
    create_creator_manual_relation,
    revoke_creator_manual_relation,
)

router = APIRouter(prefix="/relations", tags=["relations"])

_ERROR_STATUS = {
    "already_exists": 409,
    "not_found": 404,
    "not_in_lexicon": 404,
    "self_relation": 400,
    "missing_literal": 400,
    "invalid_relation_type": 400,
}


def _result_message(result: dict) -> str:
    direct = int(result.get("direct") or 0)
    expand = int(result.get("expand") or 0)
    skipped = int(result.get("skipped") or 0)
    parts = [f"已新增 {direct} 條關係"]
    if expand:
        parts.append(f"{expand} 條衍生關係")
    if skipped:
        parts.append(f"{skipped} 條已存在已跳過")
    return "、".join(parts)


def _revoke_message(result: dict) -> str:
    direct = int(result.get("direct") or 0)
    expand = int(result.get("expand") or 0)
    parts = [f"已撤回 {direct} 條關係"]
    if expand:
        parts.append(f"{expand} 條衍生關係")
    return "、".join(parts)


@router.post("/manual", response_model=ManualRelationResult)
def create_manual_relation(
    body: ManualRelationCreate,
    db: Session = Depends(get_db),
) -> ManualRelationResult:
    try:
        result = create_creator_manual_relation(
            db,
            seed_char=body.seed_char,
            opposite_char=body.opposite_char,
            relation_type=body.relation_type,
        )
    except ManualRelationError as exc:
        status = _ERROR_STATUS.get(exc.code, 400)
        raise HTTPException(status_code=status, detail=exc.message) from exc

    return ManualRelationResult(
        direct=result["direct"],
        expand=result["expand"],
        skipped=result["skipped"],
        message=_result_message(result),
    )


@router.post("/manual/revoke", response_model=ManualRelationResult)
def revoke_manual_relation(
    body: ManualRelationCreate,
    db: Session = Depends(get_db),
) -> ManualRelationResult:
    try:
        result = revoke_creator_manual_relation(
            db,
            seed_char=body.seed_char,
            opposite_char=body.opposite_char,
            relation_type=body.relation_type,
        )
    except ManualRelationError as exc:
        status = _ERROR_STATUS.get(exc.code, 400)
        raise HTTPException(status_code=status, detail=exc.message) from exc

    return ManualRelationResult(
        direct=result["direct"],
        expand=result["expand"],
        skipped=0,
        message=_revoke_message(result),
    )


__all__ = ["router"]
