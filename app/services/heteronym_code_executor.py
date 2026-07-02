"""同音異讀 code/code 查詢執行。"""
from __future__ import annotations

from typing import List

from sqlalchemy.orm import Session

from app.domain.lexicon.heteronym_index import ensure_heteronym_index
from app.models.word import Word
from app.services.position_match.filters import matches_code_positions
from app.services.query_grammar.heteronym import code_template_to_required
from app.services.query_types import HeteronymCodeQuery
from app.services.word_serializer import paginate, serialize_word


def _tags_for_reading(
    code: str,
    jyutping: str,
    *,
    left_req: list,
    right_req: list,
    mode: str,
) -> list[str]:
    tags: list[str] = []
    if matches_code_positions(code, left_req, mode):
        tags.append("左")
    if matches_code_positions(code, right_req, mode):
        tags.append("右")
    return tags


def execute_heteronym_code_search(
    parsed: HeteronymCodeQuery,
    *,
    mode: str,
    limit: int,
    offset: int,
    db: Session,
) -> List[dict]:
    left_req = code_template_to_required(parsed.left_template)
    right_req = code_template_to_required(parsed.right_template)
    index = ensure_heteronym_index(db)
    width = parsed.width
    items: list[dict] = []

    for char, readings in index.items():
        if len(char) != width:
            continue
        left_jyuts = {jp for code, jp in readings if matches_code_positions(code, left_req, mode)}
        right_jyuts = {jp for code, jp in readings if matches_code_positions(code, right_req, mode)}
        if not left_jyuts or not right_jyuts:
            continue
        if left_jyuts == right_jyuts and len(left_jyuts) == 1:
            continue
        paired = any(
            j1 != j2
            for j1 in left_jyuts
            for j2 in right_jyuts
        )
        if not paired:
            continue

        rows = (
            db.query(Word)
            .filter(Word.char == char, Word.length == width)
            .order_by(Word.jyutping, Word.code)
            .all()
        )
        for row in rows:
            tags = _tags_for_reading(
                row.code or "",
                row.jyutping or "",
                left_req=left_req,
                right_req=right_req,
                mode=mode,
            )
            if not tags:
                continue
            payload = serialize_word(row)
            payload["heteronym_tags"] = tags
            items.append(payload)

    items.sort(key=lambda r: (r.get("char") or "", r.get("jyutping") or ""))
    return paginate(items, offset, limit)


__all__ = ["execute_heteronym_code_search"]
