"""Runtime loader for e1 embedding-nbr CSR (Desktop pool)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from app.domain.lexicon.embedding_nbr_codec import (
    NBR_VERSION,
    RELATION_TYPE,
    SOURCE,
    EmbeddingNbrIndex,
    decode_csr_blob,
)
from app.domain.relation_pool.ranking import final_score
from app.models.word import Word

_ROOT = Path(__file__).resolve().parents[3]
_index: Optional[EmbeddingNbrIndex] = None
_loaded_path: Optional[str] = None


def default_nbr_bin_paths() -> list[Path]:
    env = os.environ.get("CANTO_EMBEDDING_NBR_BIN")
    paths: list[Path] = []
    if env:
        paths.append(Path(env))
    paths.append(_ROOT / "client" / "public" / "embedding-nbr.bin")
    paths.append(_ROOT / ".cache" / "embedding_topk" / "embedding-nbr.bin")
    return paths


def load_embedding_nbr_index(path: Path | None = None) -> Optional[EmbeddingNbrIndex]:
    global _index, _loaded_path
    if path is None and _index is not None:
        return _index
    candidates = [path] if path else default_nbr_bin_paths()
    for p in candidates:
        if p is None or not p.is_file():
            continue
        key = str(p.resolve())
        if _index is not None and _loaded_path == key:
            return _index
        data = p.read_bytes()
        _index = decode_csr_blob(data)
        _loaded_path = key
        return _index
    return _index


def clear_embedding_nbr_index() -> None:
    global _index, _loaded_path
    _index = None
    _loaded_path = None


def fetch_embedding_nbr_items(db: Session, query: str) -> List[dict]:
    idx = load_embedding_nbr_index()
    if idx is None:
        return []
    q = (query or "").strip()
    if not q:
        return []
    head = (
        db.query(Word.id)
        .filter(Word.char == q)
        .order_by(Word.id.asc())
        .limit(1)
        .first()
    )
    if not head:
        return []
    hits = idx.neighbors_of(int(head[0]))
    if not hits:
        return []
    id_list = [nid for nid, _ in hits]
    rows = db.query(Word.id, Word.char, Word.jyutping, Word.code).filter(Word.id.in_(id_list)).all()
    by_id = {int(r.id): r for r in rows}
    items: List[dict] = []
    for nid, score in hits:
        row = by_id.get(int(nid))
        if not row or not row.char or row.char == q:
            continue
        items.append(
            {
                "char": row.char,
                "relation": RELATION_TYPE,
                "source": SOURCE,
                "score": float(score),
                "in_db": True,
                "jyutping": row.jyutping or "",
                "code": row.code or "",
                "group_codes": [],
                "_sort": final_score(source=SOURCE, confidence=float(score), in_db=True),
            }
        )
    return items


__all__ = [
    "NBR_VERSION",
    "clear_embedding_nbr_index",
    "default_nbr_bin_paths",
    "fetch_embedding_nbr_items",
    "load_embedding_nbr_index",
]
