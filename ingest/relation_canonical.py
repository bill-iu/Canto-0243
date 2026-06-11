"""Canonical ordering for undirected word_relations (smaller word id first)."""
from __future__ import annotations

import json
import time
from typing import Tuple

DEBUG_LOG = "debug-c269d0.log"
SESSION_ID = "c269d0"


def canonical_word_ids(a: int, b: int) -> Tuple[int, int]:
    """Always store the lower word id in word_id column."""
    if a <= b:
        return a, b
    return b, a


def relation_storage_key(word_id: int, related_id: int, relation_type: str) -> Tuple[int, int, str]:
    w, r = canonical_word_ids(word_id, related_id)
    return w, r, relation_type


def canonical_relation_dict(rel: dict) -> dict:
    w, r = canonical_word_ids(int(rel["word_id"]), int(rel["related_id"]))
    out = dict(rel)
    out["word_id"] = w
    out["related_id"] = r
    return out


def _debug_log(hypothesis_id: str, location: str, message: str, data: dict, run_id: str = "pre-fix") -> None:
    # #region agent log
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": SESSION_ID,
                "runId": run_id,
                "hypothesisId": hypothesis_id,
                "location": location,
                "message": message,
                "data": data,
                "timestamp": int(time.time() * 1000),
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass
    # #endregion
