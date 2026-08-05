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


def char_id_fingerprint(char_to_primary_id: Mapping[str, int]) -> str:
    """Stable sha256 over sorted 'char\\tprimary_id' lines (UTF-8).

    Bin CSR stores word ids; reuse is safe only when this fingerprint matches
    the lexicon at bake time.
    """
    lines = [f"{ch}\t{int(pid)}" for ch, pid in sorted(char_to_primary_id.items(), key=lambda x: x[0])]
    payload = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def char_id_fingerprint_from_db(db) -> str:
    from app.domain.relations.char_index import get_char_to_primary_id

    return char_id_fingerprint(get_char_to_primary_id(db))


def char_id_fingerprint_from_sqlite(db_path: Path | str) -> str:
    import sqlite3

    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute(
            "SELECT char, MIN(id) AS pid FROM words "
            "WHERE char IS NOT NULL AND char != '' GROUP BY char"
        ).fetchall()
    finally:
        con.close()
    return char_id_fingerprint({str(ch): int(pid) for ch, pid in rows if ch is not None})


def load_nbr_meta(meta_path: Path | str) -> dict:
    p = Path(meta_path)
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def verify_embedding_nbr_fingerprint(
    *,
    db_path: Path | str,
    meta_path: Path | str,
    bin_path: Path | str | None = None,
    require_present: bool = False,
) -> dict:
    """Compare live lyrics.db char→id fingerprint to meta.

    Returns dict: ok, status (match|mismatch|missing_meta|missing_fp|missing_bin), ...
    """
    meta_p = Path(meta_path)
    bin_p = Path(bin_path) if bin_path else meta_p.with_suffix(".bin")
    # default: embedding-nbr.meta.json → embedding-nbr.bin
    if bin_path is None and meta_p.name.endswith(".meta.json"):
        bin_p = meta_p.with_name(meta_p.name.replace(".meta.json", ".bin"))

    out: dict = {
        "ok": True,
        "status": "match",
        "meta_path": str(meta_p),
        "bin_path": str(bin_p),
        "db_path": str(db_path),
    }
    if not meta_p.is_file():
        out["status"] = "missing_meta"
        out["ok"] = not require_present
        out["hint"] = "no embedding-nbr.meta.json — skip or bake first"
        return out
    if not bin_p.is_file():
        out["status"] = "missing_bin"
        out["ok"] = not require_present
        out["hint"] = "meta without bin"
        return out

    meta = load_nbr_meta(meta_p)
    baked_fp = meta.get("char_id_fingerprint")
    live_fp = char_id_fingerprint_from_sqlite(db_path)
    out["live_fingerprint"] = live_fp
    out["baked_fingerprint"] = baked_fp
    out["n_heads_meta"] = meta.get("n_heads")
    out["sha256_meta"] = meta.get("sha256")

    if not baked_fp:
        out["status"] = "missing_fp"
        out["ok"] = False
        out["hint"] = (
            "meta lacks char_id_fingerprint — re-export/bake or "
            "python -m ingest stamp-embedding-nbr-fp"
        )
        return out
    if baked_fp != live_fp:
        out["status"] = "mismatch"
        out["ok"] = False
        out["hint"] = (
            "words id map changed — do NOT reuse bin; "
            "re-run bake-embedding-topk (vectors sidecar ok if chars set unchanged)"
        )
        return out
    out["status"] = "match"
    out["ok"] = True
    out["hint"] = "bin safe to reuse (char→primary_id unchanged)"
    return out


def stamp_fingerprint_on_meta(
    *,
    db_path: Path | str,
    meta_path: Path | str,
    also: Sequence[Path | str] | None = None,
) -> dict:
    """Write/overwrite char_id_fingerprint on existing meta (bin unchanged)."""
    fp = char_id_fingerprint_from_sqlite(db_path)
    paths = [Path(meta_path)]
    if also:
        paths.extend(Path(p) for p in also)
    written = []
    for p in paths:
        if not p.is_file():
            continue
        meta = load_nbr_meta(p)
        meta["char_id_fingerprint"] = fp
        p.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(str(p))
    return {"char_id_fingerprint": fp, "written": written}


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
    "char_id_fingerprint",
    "char_id_fingerprint_from_db",
    "char_id_fingerprint_from_sqlite",
    "decode_csr_blob",
    "edges_from_word_relations_db",
    "encode_csr_blob",
    "load_nbr_meta",
    "score_to_u16",
    "stamp_fingerprint_on_meta",
    "u16_to_score",
    "verify_embedding_nbr_fingerprint",
    "write_nbr_bundle",
]
