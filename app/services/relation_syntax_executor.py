"""近反義關係查詢 executor：PoolSnapshot 之後的 Word 列投影。"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.services.query_parse import RelationLookupQuery
from app.domain.relation_pool import PoolSnapshot, project_relation_pool, relation_pool_page
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port
from app.models.word import Word
from app.services.position_match.filters.f1_slot_code import matches_code_positions
from app.services.position_match.mask_adapter import required_codes_from_digit_string


def _seed_has_code_prefix(
    db: Session,
    seed: str,
    code_prefix: str,
    mode: str,
) -> bool:
    """碼前綴約束種子字面讀音（如 33!開心），唔篩結果詞碼。PR-A：逐格 digit。"""
    text = (seed or "").strip()
    required = required_codes_from_digit_string(code_prefix)
    if not text or not required or len(text) != len(required):
        return False
    rows = db.query(Word).filter(Word.char == text).all()
    return any(matches_code_positions(row.code or "", required, mode) for row in rows)


def _pool_item_to_word_dict(item: dict, query_text: str) -> dict:
    """將 PoolSnapshot item 轉為詞條搜尋結果格式。

    PoolSnapshot item 已包含 char, code, jyutping 等資料，
    直接轉換為詞條格式，無需再查 DB。
    """
    return {
        "char": item.get("char") or "",
        "code": item.get("code") or "",
        "jyutping": item.get("jyutping") or "",
        "display_text": item.get("char") or "",
        "query_text": query_text,
        "result_type": "word",
        "id": None,  # PoolSnapshot 不包含 DB id
    }


def _words_for_relation_items(
    items: List[dict],
    *,
    limit: int,
    offset: int,
    query_text: str,
) -> List[dict]:
    """關係語法投影：PoolSnapshot item -> 詞條結果，唔再查 DB。"""
    if not items:
        return []

    seen = set()
    unique_items = []
    for item in items:
        char = item.get("char") or ""
        if not char or char in seen:
            continue
        seen.add(char)
        unique_items.append(item)

    # 關係語法（~ / !）只投影收錄字面，靜態未收錄候選留俾近反義模式
    unique_items = [item for item in unique_items if item.get("in_db")]
    if not unique_items:
        return []

    unique_items.sort(key=lambda x: x.get("_sort", 99))
    word_dicts = [_pool_item_to_word_dict(item, query_text) for item in unique_items]
    start = offset
    end = offset + limit
    return word_dicts[start:end]


def _pool_items_for_kind(pool: PoolSnapshot, relation_kind: str) -> List[dict]:
    if relation_kind == "syn":
        return pool.syns
    if relation_kind == "ant":
        return pool.ants
    return pool.syns + pool.ants + pool.semantic


def _words_for_relation_kind(
    pool: PoolSnapshot,
    relation_kind: str,
    *,
    limit: int,
    offset: int,
    query_text: str,
) -> List[dict]:
    return _words_for_relation_items(
        _pool_items_for_kind(pool, relation_kind),
        limit=limit,
        offset=offset,
        query_text=query_text,
    )


class RelationSyntaxExecutor:
    """Per-request executor for 近反義模式 and ~ / ! 關係查詢。"""

    def __init__(self, db: Session, thesaurus: Optional[ThesaurusPort] = None):
        self._db = db
        self._thesaurus = thesaurus or default_thesaurus_port()

    def syn_mode_page(self, query: str, *, limit: int, offset: int) -> List[dict]:
        """mode=syn：full syn + ant + semantic 分頁列（近反義模式）。"""
        if not query or not re.search(r"[\u4e00-\u9fff]", query):
            return []
        return relation_pool_page(
            self._db,
            query.strip(),
            limit=limit,
            offset=offset,
            thesaurus=self._thesaurus,
        )

    def relation_lookup_page(
        self,
        parsed: RelationLookupQuery,
        *,
        mode: str,
        limit: int,
        offset: int,
    ) -> List[dict]:
        """~ / ! 近反義關係查詢：PoolSnapshot 投影為詞條結果。"""
        pool = project_relation_pool(
            self._db,
            parsed.word.strip(),
            thesaurus=self._thesaurus,
        )

        if parsed.code_prefix and not _seed_has_code_prefix(
            self._db, parsed.word, parsed.code_prefix, mode
        ):
            return []

        return _words_for_relation_kind(
            pool,
            parsed.relation_kind,
            limit=limit,
            offset=offset,
            query_text=parsed.word,
        )


__all__ = [
    "RelationSyntaxExecutor",
]
