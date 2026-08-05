"""語意鄰居 CSR 緊湊載體 e1.v1（CONTEXT § 語意鄰居緊湊載體 / 真緊湊）.

Binary layout (little-endian), bidirectional CSR:
  magic[4]=ENBR | ver:u16=1 | n_heads:u32 | n_edges:u32
  | score_floor_milli:u16 | score_span_milli:u16
  | head_ids:u32[n_heads] (sorted)
  | indptr:u32[n_heads+1]
  | neighbor_ids:u32[n_edges]
  | score_u16:u16[n_edges]  # 0..65535 over [floor, floor+span] milli-cosine
"""
from __future__ import annotations

import hashlib
import json
import struct
from bisect import bisect_left
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

NBR_VERSION = "e1.v1"
MAGIC = b"ENBR"
FORMAT_VER = 1
# cosine 0.50–1.00 → u16
SCORE_FLOOR_MILLI = 500
SCORE_SPAN_MILLI = 500
SOURCE = "embedding_cosine"
RELATION_TYPE = "semantic_related"

Neighbor = Tuple[int, float]  # related_id, score


def score_to_u16(score: float) -> int:
    milli = float(score) * 1000.0
    t = (milli - SCORE_FLOOR_MILLI) / float(SCORE_SPAN_MILLI)
    return int(max(0, min(65535, round(t * 65535))))


def u16_to_score(q: int) -> float:
    t = max(0, min(65535, int(q))) / 65535.0
    milli = SCORE_FLOOR_MILLI + t * SCORE_SPAN_MILLI
    return milli / 1000.0


def build_bidirectional_adj(
    undirected_edges: Iterable[Tuple[int, int, float]],
) -> Dict[int, List[Neighbor]]:
    """edges: (id_a, id_b, score) undirected; expand both directions."""
    adj: Dict[int, List[Neighbor]] = defaultdict(list)
    seen: set[Tuple[int, int]] = set()
    for a, b, s in undirected_edges:
        a, b = int(a), int(b)
        if a == b:
            continue
        lo, hi = (a, b) if a < b else (b, a)
        key = (lo, hi)
        if key in seen:
            continue
        seen.add(key)
        sc = float(s)
        adj[a].append((b, sc))
        adj[b].append((a, sc))
    for hid in adj:
        adj[hid].sort(key=lambda x: (-x[1], x[0]))
    return adj


def encode_csr_blob(adj: Mapping[int, Sequence[Neighbor]]) -> bytes:
    heads = sorted(int(h) for h in adj.keys())
    indptr = [0]
    neighbors: List[int] = []
    scores: List[int] = []
    for h in heads:
        for nid, sc in adj[h]:
            neighbors.append(int(nid))
            scores.append(score_to_u16(sc))
        indptr.append(len(neighbors))
    n_heads = len(heads)
    n_edges = len(neighbors)
    buf = bytearray()
    buf += MAGIC
    buf += struct.pack(
        "<HIIHH",
        FORMAT_VER,
        n_heads,
        n_edges,
        SCORE_FLOOR_MILLI,
        SCORE_SPAN_MILLI,
    )
    if n_heads:
        buf += struct.pack(f"<{n_heads}I", *heads)
    buf += struct.pack(f"<{n_heads + 1}I", *indptr)
    if n_edges:
        buf += struct.pack(f"<{n_edges}I", *neighbors)
        buf += struct.pack(f"<{n_edges}H", *scores)
    return bytes(buf)


class EmbeddingNbrIndex:
    """Decoded CSR; lookup by primary word_id."""

    __slots__ = (
        "heads",
        "indptr",
        "neighbors",
        "scores_u16",
        "floor_milli",
        "span_milli",
    )

    def __init__(
        self,
        heads: List[int],
        indptr: List[int],
        neighbors: List[int],
        scores_u16: List[int],
        floor_milli: int = SCORE_FLOOR_MILLI,
        span_milli: int = SCORE_SPAN_MILLI,
    ):
        self.heads = heads
        self.indptr = indptr
        self.neighbors = neighbors
        self.scores_u16 = scores_u16
        self.floor_milli = floor_milli
        self.span_milli = span_milli

    def neighbors_of(self, head_id: int) -> List[Neighbor]:
        i = bisect_left(self.heads, int(head_id))
        if i >= len(self.heads) or self.heads[i] != head_id:
            return []
        lo, hi = self.indptr[i], self.indptr[i + 1]
        out: List[Neighbor] = []
        span = float(self.span_milli) or 1.0
        for j in range(lo, hi):
            q = self.scores_u16[j]
            milli = self.floor_milli + (q / 65535.0) * span
            out.append((self.neighbors[j], milli / 1000.0))
        return out


def decode_csr_blob(data: bytes) -> EmbeddingNbrIndex:
    if len(data) < 4 + 2 + 4 + 4 + 2 + 2:
        raise ValueError("embedding nbr blob too short")
    if data[:4] != MAGIC:
        raise ValueError(f"bad magic {data[:4]!r}")
    ver, n_heads, n_edges, floor_m, span_m = struct.unpack_from("<HIIHH", data, 4)
    if ver != FORMAT_VER:
        raise ValueError(f"unsupported nbr format ver {ver}")
    off = 4 + 2 + 4 + 4 + 2 + 2
    heads: List[int] = []
    if n_heads:
        heads = list(struct.unpack_from(f"<{n_heads}I", data, off))
        off += 4 * n_heads
    indptr = list(struct.unpack_from(f"<{n_heads + 1}I", data, off))
    off += 4 * (n_heads + 1)
    neighbors: List[int] = []
    scores: List[int] = []
    if n_edges:
        neighbors = list(struct.unpack_from(f"<{n_edges}I", data, off))
        off += 4 * n_edges
        scores = list(struct.unpack_from(f"<{n_edges}H", data, off))
    return EmbeddingNbrIndex(heads, indptr, neighbors, scores, floor_m, span_m)


def write_nbr_bundle(
    blob: bytes,
    *,
    bin_path: Path,
    meta_path: Path,
    model_version: str,
    extra: dict | None = None,
) -> dict:
    bin_path.parent.mkdir(parents=True, exist_ok=True)
    bin_path.write_bytes(blob)
    digest = hashlib.sha256(blob).hexdigest()
    idx = decode_csr_blob(blob)
    meta = {
        "embedding_nbr_version": NBR_VERSION,
        "format": FORMAT_VER,
        "model_version": model_version,
        "n_heads": len(idx.heads),
        "n_edges": len(idx.neighbors),
        "sha256": digest,
        "score_floor_milli": SCORE_FLOOR_MILLI,
        "score_span_milli": SCORE_SPAN_MILLI,
        "source": SOURCE,
        "relation_type": RELATION_TYPE,
    }
    if extra:
        meta.update(extra)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def edges_from_word_relations_db(db, source: str = SOURCE) -> List[Tuple[int, int, float]]:
    from sqlalchemy import text

    rows = db.execute(
        text(
            "SELECT word_id, related_id, score FROM word_relations "
            "WHERE source = :src AND relation_type = :rt"
        ),
        {"src": source, "rt": RELATION_TYPE},
    ).fetchall()
    out: List[Tuple[int, int, float]] = []
    for a, b, s in rows:
        out.append((int(a), int(b), float(s if s is not None else 0.5)))
    return out


__all__ = [
    "NBR_VERSION",
    "SOURCE",
    "RELATION_TYPE",
    "EmbeddingNbrIndex",
    "build_bidirectional_adj",
    "decode_csr_blob",
    "edges_from_word_relations_db",
    "encode_csr_blob",
    "score_to_u16",
    "u16_to_score",
    "write_nbr_bundle",
]
