"""AUTO-GENERATED from contracts/relation-pool-ranking.json — do not edit.
Regenerate: python scripts/codegen_relation_pool_ranking.py
"""
from __future__ import annotations

from typing import Dict

SOURCE_BASE_RANK: Dict[str, int] = {
    "manual": 0,
    "manual_syn_cluster": 18,
    "manual_ant_mirror": 20,
    "cilin": 10,
    "antisem": 10,
    "project_ant": 12,
    "guotong": 15,
    "ant_cilin_exanded": 25,
    "ant_syn_bridge": 28,
    "cow": 20,
    "current_static": 15,
    "runtime_static": 80,
    "static_thesaurus": 80,
    "embedding_cosine": 60,
    "word_relations": 50,
}

RUNTIME_DERIVED_ANT_SOURCES = frozenset({
    "ant_syn_mirror",
    "ant_cilin_exanded",
})
