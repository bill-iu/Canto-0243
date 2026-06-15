"""詞庫快取 facade — 向後相容匯出；索引／預載／磁碟已拆分至子模組。"""
from __future__ import annotations

from app.utils import word_cache_disk as disk
from app.utils import word_cache_index as index
from app.utils import word_cache_preload as preload

# --- 預載 lifecycle（adapter）---
begin_preload = preload.begin_preload
complete_preload = preload.complete_preload
fail_preload = preload.fail_preload
set_preload_progress = preload.set_preload_progress
get_preload_snapshot = preload.get_preload_snapshot
start_word_cache_preload_background = preload.start_background_preload
populate_word_cache_from_rows = preload.populate_from_rows

# --- 磁碟 adapter（測試與維護者工具）---
_disk_cache_path = disk.disk_cache_path
try_restore_word_cache_from_disk = disk.try_restore
persist_word_cache_to_disk = disk.persist

# --- 詞庫快取索引（查詢 API）---
get_words_for_length = index.get_words_for_length
get_char_meta = index.get_char_meta
get_char_metas = index.get_char_metas
update_word_in_cache = index.update_entry
get_word_cache_stats = index.get_stats


def get_mask_index_candidates(length: int, mask: str):
    if not is_word_cache_ready():
        return None
    return index.get_mask_index_candidates(length, mask)


def get_phoneme_index_candidates(length: int, pos: int, anchor: str, constraint: str, db):
    if not is_word_cache_ready():
        return []
    return index.get_phoneme_index_candidates(length, pos, anchor, constraint, db)


def narrow_candidates_by_phoneme_anchor(
    candidates: list,
    length: int,
    pos: int,
    anchor: str,
    constraint: str,
    db,
) -> list:
    if not is_word_cache_ready():
        return candidates
    return index.narrow_candidates_by_phoneme_anchor(
        candidates, length, pos, anchor, constraint, db
    )


def is_word_cache_ready() -> bool:
    return preload.is_preload_complete() and index.is_populated()


def reset_word_cache_for_tests() -> None:
    index.reset_index_for_tests()
    preload.reset_preload_for_tests()
