from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from ingest.cilin_leaf import (
    groups_to_syn_edges,
    iter_cilin_leaf_line_chunks,
    parse_leaf_group_line,
    parse_leaf_groups,
)
from ingest.syn_ant_manifest import ROOT, resolve_source_path

CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def _edge(
    head: str,
    tail: str,
    relation_type: str,
    source: str,
    *,
    confidence: float = 0.7,
    source_rank: int = 50,
    evidence: Optional[dict] = None,
    license_tag: Optional[str] = None,
) -> dict:
    return {
        "head": head,
        "tail": tail,
        "relation_type": relation_type,
        "source": source,
        "confidence": float(confidence),
        "source_rank": int(source_rank),
        "evidence": evidence or {},
        "license_tag": license_tag or source,
    }


def _read_lines(path: Path) -> List[str]:
    for enc in ("utf-8", "gbk", "gb18030"):
        try:
            return path.read_text(encoding=enc).splitlines()
        except UnicodeDecodeError:
            continue
    return []


def parse_cilin_lines(lines: Iterable[str], source: str, source_rank: int = 55) -> List[dict]:
    """Parse leaf Cilin synonym groups into undirected char-pair edges (n choose 2)."""
    groups = parse_leaf_groups(list(lines))
    return groups_to_syn_edges(groups, source, source_rank=source_rank)


def iter_cilin_line_chunks(path: Path, chunk_size: int = 300) -> Iterator[List[str]]:
    """Yield leaf synonym lines only, in fixed-size chunks."""
    yield from iter_cilin_leaf_line_chunks(path, chunk_size=chunk_size)


def parse_cilin_like(path: Path, source: str, source_rank: int = 55) -> List[dict]:
    """Cilin leaf groups: CODE= word1 word2 ..."""
    leaf_lines = []
    for line in _read_lines(path):
        parsed = parse_leaf_group_line(line)
        if parsed:
            code, words = parsed
            leaf_lines.append(f"{code} {' '.join(words)}")
    return parse_cilin_lines(leaf_lines, source, source_rank=source_rank)


def parse_antonym_pairs(path: Path, source: str, source_rank: int = 55) -> List[dict]:
    edges: List[dict] = []
    for line in _read_lines(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            left, right = line.split(":", 1)
            ants = [x.strip() for x in right.replace("；", ";").split(";") if x.strip()]
        else:
            parts = [x.strip() for x in line.replace("——", " ").replace("—", " ").split() if x.strip()]
            if len(parts) < 2:
                continue
            left, ants = parts[0], parts[1:]
        if not left or not ants:
            continue
        for ant in ants:
            if ant and ant != left:
                edges.append(_edge(left, ant, "ant", source, source_rank=source_rank))
                edges.append(_edge(ant, left, "ant", source, source_rank=source_rank))
    return edges


def parse_wordnet_synsets(path: Path, source: str, source_rank: int = 50) -> List[dict]:
    """Tab/space synset-lemma pairs: synset_id<TAB>lemma"""
    groups: Dict[str, List[str]] = {}
    for line in _read_lines(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            sid, lemma = line.split("\t", 1)
        else:
            parts = line.split(None, 1)
            if len(parts) != 2:
                continue
            sid, lemma = parts
        lemma = lemma.strip()
        if not CJK_RE.search(lemma):
            continue
        groups.setdefault(sid.strip(), [])
        if lemma not in groups[sid.strip()]:
            groups[sid.strip()].append(lemma)

    edges: List[dict] = []
    for sid, words in groups.items():
        for w in words:
            for other in words:
                if other != w:
                    edges.append(
                        _edge(w, other, "syn", source, source_rank=source_rank, confidence=0.75, evidence={"synset": sid})
                    )
    return edges


def parse_relation_pairs(path: Path, source: str, source_rank: int = 60) -> List[dict]:
    """TSV/CSV: head<TAB>tail<TAB>relation_type"""
    edges: List[dict] = []
    for line in _read_lines(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = re.split(r"[\t,]", line)
        if len(parts) < 3:
            continue
        head, tail, rtype = parts[0].strip(), parts[1].strip(), parts[2].strip().lower()
        if rtype not in ("syn", "ant", "semantic_related"):
            continue
        if head and tail and head != tail:
            edges.append(_edge(head, tail, rtype, source, source_rank=source_rank))
    return edges


def parse_current_static(src: Dict[str, Any]) -> List[dict]:
    """Emit edges from bundled static thesaurus via 靜態詞林埠."""
    from app.domain.thesaurus.port import StaticThesaurusPort

    paths = src.get("paths") or {}
    rank = int(src.get("source_rank") or 70)
    port = StaticThesaurusPort(
        cilin_path=str(ROOT / paths["cilin"]) if paths.get("cilin") else None,
        antisem_path=str(ROOT / paths["antisem"]) if paths.get("antisem") else None,
        thesaurus_syn_path=str(ROOT / paths["thesaurus_syn"]) if paths.get("thesaurus_syn") else None,
        thesaurus_ant_path=str(ROOT / paths["thesaurus_ant"]) if paths.get("thesaurus_ant") else None,
        auto_load=True,
    )

    edges: List[dict] = []
    for w in port.iter_literal_heads():
        for s in port.get_cilin_synonyms(w):
            edges.append(_edge(w, s, "syn", "cilin", source_rank=rank, confidence=0.85))
        for s in port.get_guotong_synonyms(w):
            edges.append(_edge(w, s, "syn", "guotong", source_rank=rank, confidence=0.8))
        for a in port.get_antonyms(w):
            edges.append(_edge(w, a, "ant", "antisem", source_rank=rank, confidence=0.85))
    return edges


PARSERS = {
    "cilin_like": lambda src: parse_cilin_like(
        resolve_source_path(src) or Path(""),
        src["id"],
        int(src.get("source_rank") or 55),
    ),
    "antonym_pairs": lambda src: parse_antonym_pairs(
        resolve_source_path(src) or Path(""),
        src["id"],
        int(src.get("source_rank") or 55),
    ),
    "wordnet_synsets": lambda src: parse_wordnet_synsets(
        resolve_source_path(src) or Path(""),
        src["id"],
        int(src.get("source_rank") or 50),
    ),
    "relation_pairs": lambda src: parse_relation_pairs(
        resolve_source_path(src) or Path(""),
        src["id"],
        int(src.get("source_rank") or 60),
    ),
    "current_static": parse_current_static,
}


def parse_source(src: Dict[str, Any]) -> List[dict]:
    parser_name = src.get("parser") or ""
    parser = PARSERS.get(parser_name)
    if not parser:
        raise ValueError(f"Unknown parser: {parser_name}")
    if parser_name != "current_static":
        raw = resolve_source_path(src)
        if raw is None or not raw.exists():
            return []
    return parser(src)


def parse_sources(sources: Iterable[Dict[str, Any]]) -> List[dict]:
    all_edges: List[dict] = []
    for src in sources:
        try:
            edges = parse_source(src)
            all_edges.extend(edges)
        except Exception as exc:
            print(f"[ingest] source {src.get('id')} failed: {type(exc).__name__}: {exc}")
    return all_edges
