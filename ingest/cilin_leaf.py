"""Cilin leaf synonym groups (level-5 codes ending with '=')."""
from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Set, Tuple

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# Leaf synonym code: Aa01A01=, Ca01B01=, etc.
CILIN_LEAF_CODE_RE = re.compile(r"^[A-Z][a-z]\d{2}[A-Z]\d{2}=$")


def patch_opencc_for_cilin() -> None:
    """cilin package requests OpenCC('s2t.json'); opencc-python-reimplemented uses 's2t'."""
    import opencc

    _orig = opencc.OpenCC

    def _OpenCC(config: str = "s2t"):
        if config in ("s2t.json", "s2twp.json", "s2tw.json"):
            config = config.replace(".json", "")
        return _orig(config)

    opencc.OpenCC = _OpenCC  # type: ignore[method-assign]


def _key_to_code(key: tuple) -> str:
    if len(key) == 5:
        return key[0] + key[1] + key[2] + key[3] + key[4]
    return "".join(str(part) for part in key)


def is_cilin_leaf_code(code: str) -> bool:
    return bool(CILIN_LEAF_CODE_RE.match(code or ""))


def export_leaf_lines_from_api(trad: bool = True) -> List[str]:
    """Export sorted leaf synonym groups via Cilin(trad=True) API."""
    patch_opencc_for_cilin()
    from cilin import Cilin

    c = Cilin(trad=trad)
    lines: List[str] = []
    level5 = c.keys.get(5) or []
    for key in sorted(level5, key=lambda k: _key_to_code(k)):
        code = _key_to_code(key)
        if not is_cilin_leaf_code(code):
            continue
        members = sorted(c.get_members(key))
        if members:
            lines.append(f"{code} {' '.join(members)}")
    return lines


def parse_leaf_group_line(line: str) -> Optional[Tuple[str, List[str]]]:
    """Return (code, words) for a leaf line, or None if not a leaf synonym group."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = line.split()
    if len(parts) < 2:
        return None
    code = parts[0]
    if not is_cilin_leaf_code(code):
        return None
    words = [p for p in parts[1:] if CJK_RE.search(p)]
    if len(words) < 2:
        return None
    return code, words


def parse_leaf_groups(lines: List[str]) -> List[Tuple[str, List[str]]]:
    groups: List[Tuple[str, List[str]]] = []
    for line in lines:
        parsed = parse_leaf_group_line(line)
        if parsed:
            groups.append(parsed)
    return groups


def canonical_char_pair(a: str, b: str) -> Tuple[str, str]:
    return (a, b) if a <= b else (b, a)


def groups_to_syn_edges(
    groups: List[Tuple[str, List[str]]],
    source: str,
    *,
    source_rank: int = 55,
    confidence: float = 0.85,
) -> List[dict]:
    """Emit n-choose-2 undirected char pairs per leaf group (no bidirectional duplicates)."""
    edges: List[dict] = []
    seen: Set[Tuple[str, str]] = set()
    for code, words in groups:
        for w, other in itertools.combinations(words, 2):
            head, tail = canonical_char_pair(w, other)
            key = (head, tail)
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "head": head,
                "tail": tail,
                "relation_type": "syn",
                "source": source,
                "confidence": confidence,
                "source_rank": source_rank,
                "evidence": {"group": code},
                "license_tag": source,
            })
    return edges


def iter_cilin_leaf_line_chunks(path: Path, chunk_size: int = 300) -> Iterator[List[str]]:
    """Yield only leaf synonym lines from a Cilin file, in chunks."""
    chunk: List[str] = []
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            with path.open("r", encoding=enc) as f:
                for raw in f:
                    parsed = parse_leaf_group_line(raw)
                    if not parsed:
                        continue
                    code, words = parsed
                    chunk.append(f"{code} {' '.join(words)}")
                    if len(chunk) >= chunk_size:
                        yield chunk
                        chunk = []
            break
        except UnicodeDecodeError:
            chunk = []
            continue
    if chunk:
        yield chunk


def groups_to_word_id_pairs(
    groups: List[Tuple[str, List[str]]],
    char_to_id: Dict[str, int],
) -> List[dict]:
    """Map leaf groups to canonical (word_id, related_id) relation dicts."""
    from ingest.relation_canonical import canonical_word_ids

    out: List[dict] = []
    seen: Set[Tuple[int, int, str]] = set()
    for code, words in groups:
        ids = [char_to_id[w] for w in words if w in char_to_id]
        if len(ids) < 2:
            continue
        for id_a, id_b in itertools.combinations(ids, 2):
            w, r = canonical_word_ids(id_a, id_b)
            key = (w, r, "syn")
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "word_id": w,
                "related_id": r,
                "relation_type": "syn",
                "score": 0.85,
                "source": "cilin",
            })
    return out
