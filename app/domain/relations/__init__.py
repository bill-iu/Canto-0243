"""關係領域：canonical 儲存、字面索引、近反義池、關係圖、寫入 word_relations。"""

from app.domain.relations.canonical import (
    canonical_relation_dict,
    canonical_word_ids,
    relation_storage_key,
)
from app.domain.relations.char_index import get_char_to_ids, get_char_to_primary_id
from app.domain.relations.graph import CharRelationGraph, ANT_SYN_MIRROR_SOURCE
from app.domain.relations.pool import PoolSnapshot, build_pool, DEFAULT_PAGE_SIZE
from app.domain.relations.pool_projection import (
    project_relation_pool,
    relation_chars_for_seed,
    relation_pool_chars,
    relation_pool_page,
)
from app.domain.relations.store import (
    insert_relation_candidates,
    insert_relation_records,
    insert_relations,
)
from app.domain.relations.syn_neighbors import one_hop_syn_neighbors

__all__ = [
    "ANT_SYN_MIRROR_SOURCE",
    "CharRelationGraph",
    "DEFAULT_PAGE_SIZE",
    "PoolSnapshot",
    "build_pool",
    "canonical_relation_dict",
    "canonical_word_ids",
    "relation_storage_key",
    "get_char_to_ids",
    "get_char_to_primary_id",
    "insert_relation_candidates",
    "insert_relations",
    "one_hop_syn_neighbors",
    "project_relation_pool",
    "relation_chars_for_seed",
    "relation_pool_chars",
    "relation_pool_page",
]
