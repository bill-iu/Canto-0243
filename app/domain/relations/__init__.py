"""關係領域：canonical 儲存、字面索引、關係圖、寫入 word_relations。

近反義池投影在 app.domain.relation_pool（C7）。此 package 唔再 barrel-export 池 API，
避免 relation_pool → derived_ant → relations.__init__ 循環。
"""

from app.domain.relations.canonical import (
    canonical_relation_dict,
    canonical_word_ids,
    relation_storage_key,
)
from app.domain.relations.char_index import get_char_to_ids, get_char_to_primary_id
from app.domain.relations.graph import CharRelationGraph, ANT_SYN_MIRROR_SOURCE
from app.domain.relations.store import (
    insert_relation_candidates,
    insert_relation_records,
    insert_relations,
)
from app.domain.relations.syn_neighbors import one_hop_syn_neighbors

__all__ = [
    "ANT_SYN_MIRROR_SOURCE",
    "CharRelationGraph",
    "canonical_relation_dict",
    "canonical_word_ids",
    "relation_storage_key",
    "get_char_to_ids",
    "get_char_to_primary_id",
    "insert_relation_candidates",
    "insert_relation_records",
    "insert_relations",
    "one_hop_syn_neighbors",
]
