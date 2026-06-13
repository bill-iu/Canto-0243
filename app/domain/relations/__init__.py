"""關係領域：canonical 儲存、字面索引、寫入 word_relations。"""

from app.domain.relations.canonical import (
    canonical_relation_dict,
    canonical_word_ids,
    relation_storage_key,
)
from app.domain.relations.char_index import get_char_to_ids, get_char_to_primary_id
from app.domain.relations.pool_chars import relation_chars_for_seed
from app.domain.relations.store import (
    fetch_existing_relation_keys,
    insert_relation_candidates,
    insert_relations,
)

__all__ = [
    "canonical_relation_dict",
    "canonical_word_ids",
    "relation_storage_key",
    "fetch_existing_relation_keys",
    "get_char_to_ids",
    "get_char_to_primary_id",
    "insert_relation_candidates",
    "insert_relations",
    "relation_chars_for_seed",
]
