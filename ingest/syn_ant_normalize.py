from __future__ import annotations

import json
import re
from typing import Dict, Iterable, List, Optional, Set

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
MAX_WORD_LEN = 12


def clean_term(text: str) -> str:
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r"[（(].*?[）)]", "", t)
    t = re.sub(r"\s+", "", t)
    return t


def is_valid_term(text: str) -> bool:
    if not text or len(text) > MAX_WORD_LEN:
        return False
    if not CJK_RE.search(text):
        return False
    if re.search(r"[0-9A-Za-z_]", text):
        return False
    return True


def normalize_edges(
    edges: Iterable[dict],
    *,
    db_chars: Optional[Set[str]] = None,
    allow_external: bool = True,
) -> List[dict]:
    db_chars = db_chars or set()
    out: List[dict] = []
    seen: Set[tuple] = set()

    for e in edges or []:
        head = clean_term(e.get("head") or "")
        tail = clean_term(e.get("tail") or "")
        rtype = (e.get("relation_type") or "").strip()
        if not is_valid_term(head) or not is_valid_term(tail) or head == tail:
            continue
        if rtype not in ("syn", "ant", "semantic_related"):
            continue

        in_db_head = head in db_chars
        in_db_tail = tail in db_chars
        if not allow_external and not (in_db_head and in_db_tail):
            continue

        key = (head, tail, rtype)
        if key in seen:
            continue
        seen.add(key)

        bonus = 0.0
        if in_db_head:
            bonus += 0.05
        if in_db_tail:
            bonus += 0.05

        out.append({
            "head": head,
            "tail": tail,
            "relation_type": rtype,
            "source": e.get("source") or "unknown",
            "confidence": min(1.0, float(e.get("confidence") or 0.5) + bonus),
            "source_rank": int(e.get("source_rank") or 50),
            "evidence": e.get("evidence") or {},
            "license_tag": e.get("license_tag") or e.get("source") or "unknown",
            "in_db_head": in_db_head,
            "in_db_tail": in_db_tail,
        })
    return out


def merge_staging_edges(edges: Iterable[dict]) -> List[dict]:
    """Merge duplicate (head,tail,type) from multiple sources."""
    bucket: Dict[tuple, dict] = {}
    for e in edges or []:
        key = (e["head"], e["tail"], e["relation_type"])
        if key not in bucket:
            bucket[key] = dict(e)
            bucket[key]["sources"] = [e.get("source")]
            continue
        cur = bucket[key]
        cur["confidence"] = min(1.0, float(cur.get("confidence") or 0) + float(e.get("confidence") or 0) * 0.25)
        cur["source_rank"] = min(int(cur.get("source_rank") or 99), int(e.get("source_rank") or 99))
        srcs = cur.setdefault("sources", [])
        if e.get("source") and e["source"] not in srcs:
            srcs.append(e["source"])
        cur["source"] = "+".join(sorted(set(srcs)))
    return list(bucket.values())
