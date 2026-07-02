"""近反義關係查詢 executor：PoolSnapshot 之後的 Word 列投影。"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.services.query_parse import RelationLookupQuery
from app.domain.relations.pool_projection import project_relation_pool, relation_pool_page
from app.domain.relations.pool import PoolSnapshot
from app.domain.thesaurus.port import ThesaurusPort, default_thesaurus_port
from app.services.word_db_filters import apply_code_filter, length_filter
from app.services.word_serializer import serialize_page
from app.utils.jyutping_codec import get_code_variants

from app.models.word import Word


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


def words_for_relation_chars(
    db: Session,
    ranked_chars: List[str],
    *,
    code_prefix: Optional[str],
    mode: str,
    limit: int,
    offset: int,
) -> List[dict]:
    """Map ranked relation chars to Word rows, optionally filtered by 0243 code prefix.
    
    NOTE: This function is kept for backward compatibility.
    New code should use words_for_relation_pool() instead for better performance.
    """
    if not ranked_chars:
        return []

    char_order = {ch: idx for idx, ch in enumerate(dict.fromkeys(ranked_chars))}
    query = db.query(Word).filter(Word.char.in_(list(char_order.keys())))
    if code_prefix:
        variants = get_code_variants(code_prefix, mode)
        query = query.filter(Word.code.in_(variants), length_filter(len(code_prefix)))

    words = query.all()
    words.sort(key=lambda w: (char_order.get(w.char or "", 10**9), w.code or "", w.jyutping or ""))
    return serialize_page(words, offset, limit, result_type="word")


def words_for_relation_pool_from_items(
    items: List[dict],
    *,
    code_prefix: Optional[str],
    mode: str,
    limit: int,
    offset: int,
    query_text: str,
) -> List[dict]:
    """從 PoolSnapshot items 直接生成詞條列表，無需再查 DB。
    
    此為 N+1 修復的核心函數：PoolSnapshot items 已包含完整 word 資料（char, code, jyutping），
    直接轉換為詞條格式，避免重複查詢 DB。
    
    Args:
        items: PoolSnapshot 中的 syns/ants/semantic items 列表
        code_prefix: 可選的 0243 碼前綴，用於過濾
        mode: 0243 搜尋模式（m1/m2）
        limit: 分頁大小
        offset: 分頁偏移
        query_text: 查詢文字，用於 result 中的 query_text
    
    Returns:
        List[dict] 詞條格式的結果列表
    """
    if not items:
        return []
    
    # 過濾掉無效或重複
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
    if code_prefix:
        variants = get_code_variants(code_prefix, mode)
        # 過濾出符合 code_prefix 的 items
        filtered_items = []
        for item in unique_items:
            char = item.get("char") or ""
            code = item.get("code") or ""
            if code in variants and len(char) == len(code_prefix):
                filtered_items.append(item)
        unique_items = filtered_items
    
    # 按 _sort 分數排序
    unique_items.sort(key=lambda x: x.get("_sort", 99))
    
    # 轉換格式
    word_dicts = [_pool_item_to_word_dict(item, query_text) for item in unique_items]
    
    # 手動分頁
    start = offset
    end = offset + limit
    return word_dicts[start:end]


def words_for_relation_pool(
    pool: PoolSnapshot,
    *,
    code_prefix: Optional[str],
    mode: str,
    limit: int,
    offset: int,
    query_text: str,
) -> List[dict]:
    """從 PoolSnapshot 直接生成詞條列表，無需再查 DB。
    
    此為 N+1 修復的核心函數：PoolSnapshot 已包含完整 word 資料（char, code, jyutping），
    直接轉換為詞條格式，避免重複查詢 DB。
    
    Args:
        pool: PoolSnapshot 物件，已包含 syns/ants/semantic 完整資料
        code_prefix: 可選的 0243 碼前綴，用於過濾
        mode: 0243 搜尋模式（m1/m2）
        limit: 分頁大小
        offset: 分頁偏移
        query_text: 查詢文字，用於 result 中的 query_text
    
    Returns:
        List[dict] 詞條格式的結果列表
    """
    # 合併所有 relation 類型
    all_items = pool.syns + pool.ants + pool.semantic
    return words_for_relation_pool_from_items(
        all_items,
        code_prefix=code_prefix,
        mode=mode,
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
        """~ / ! 近反義關係查詢：直接使用 PoolSnapshot，無需再查 DB。
        
        N+1 修復：改為直接使用 PoolSnapshot 的完整資料，避免重複查詢。
        
        原來流程：
            relation_pool_chars() → 查 DB 取 chars
            words_for_relation_chars() → 再查 DB 取 Word
        
        新流程：
            project_relation_pool() → 查 DB 取 PoolSnapshot（已包含完整 Word 資料）
            words_for_relation_pool() → 直接轉換格式，無需再查 DB
        """
        pool = project_relation_pool(
            self._db,
            parsed.word.strip(),
            thesaurus=self._thesaurus,
        )
        
        # 根據 relation_kind 獲取對應的 items
        if parsed.relation_kind == "syn":
            # 只需要同義詞
            all_items = pool.syns
        elif parsed.relation_kind == "ant":
            all_items = pool.ants
        else:
            all_items = pool.syns + pool.ants + pool.semantic
        
        return words_for_relation_pool_from_items(
            all_items,
            code_prefix=parsed.code_prefix,
            mode=mode,
            limit=limit,
            offset=offset,
            query_text=parsed.word,
        )


__all__ = [
    "RelationSyntaxExecutor",
    "words_for_relation_chars",
    "words_for_relation_pool",
    "words_for_relation_pool_from_items",
    "_pool_item_to_word_dict",
]
