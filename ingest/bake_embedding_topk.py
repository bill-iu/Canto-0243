"""GPU bake: bge-m3 top-K → semantic_related (A) + proposal TSV (C).

CONTEXT: 語意向量鄰居烘焙 / 語意鄰居 GPU 烘焙.
Defaults (grill T2): A if direct_syn_degree < 5; K'=10; cosine>=0.50;
C every head top-K=20 (wider, no floor). Fail-closed on CUDA.
"""
from __future__ import annotations

import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = Path(r"F:\localAI\data\models\bge-m3-onnx")
DEFAULT_CACHE = ROOT / ".cache" / "embedding_topk"
SOURCE = "embedding_cosine"
MODEL_VERSION = "bge-m3-fp32-onnx-v1"
RELATION_TYPE = "semantic_related"

# grill T2 locked
DEFAULT_SYN_DEGREE_LT = 5
DEFAULT_A_TOPK = 10
DEFAULT_A_MIN_COSINE = 0.50
DEFAULT_C_TOPK = 20
DEFAULT_ENCODE_BATCH = 64


def _add_dll_dirs(model_python: Path | None = None) -> None:
    cuda = os.environ.get("CUDA_PATH", r"D:\NVIDIA GPU Computing Toolkit\CUDA\v13.3")
    for sub in ("bin", r"bin\x64"):
        p = Path(cuda) / sub
        if p.is_dir():
            os.add_dll_directory(str(p))
    base = Path(sys.prefix) / "Lib" / "site-packages" / "nvidia"
    if base.is_dir():
        for entry in base.iterdir():
            for cand in (entry / "bin", entry / "lib", entry / "lib" / "x64"):
                if cand.is_dir():
                    os.add_dll_directory(str(cand))


def require_cuda_session(model_dir: Path):
    """Load bge-m3 ONNX on CUDA only; raise if CUDA EP not used."""
    _add_dll_dirs()
    import onnxruntime as ort
    from tokenizers import Tokenizer

    try:
        ort.preload_dlls()
    except Exception:
        pass
    available = list(ort.get_available_providers())
    if "CUDAExecutionProvider" not in available:
        raise RuntimeError(
            f"CUDAExecutionProvider missing (available={available}). "
            "Install onnxruntime-gpu[cuda,cudnn] and CUDA 13.x + cuDNN."
        )
    onnx_path = model_dir / "model.onnx"
    tok_path = model_dir / "tokenizer.json"
    if not onnx_path.is_file() or not tok_path.is_file():
        raise FileNotFoundError(f"bge-m3 incomplete under {model_dir}")
    sess = ort.InferenceSession(str(onnx_path), providers=["CUDAExecutionProvider"])
    active = list(sess.get_providers())
    if not active or active[0] != "CUDAExecutionProvider":
        raise RuntimeError(f"session not on CUDA (providers={active})")
    tok = Tokenizer.from_file(str(tok_path))
    return sess, tok, available


def encode_chars(
    chars: list[str],
    sess,
    tok,
    *,
    batch_size: int = DEFAULT_ENCODE_BATCH,
) -> np.ndarray:
    """Return float32 L2-normalized matrix (N, 1024)."""
    n = len(chars)
    out = np.zeros((n, 1024), dtype=np.float32)
    t0 = time.perf_counter()
    for start in range(0, n, batch_size):
        batch = chars[start : start + batch_size]
        encs = [tok.encode(t) for t in batch]
        maxlen = max((len(e.ids) for e in encs), default=1)
        ids = np.zeros((len(batch), maxlen), dtype=np.int64)
        mask = np.zeros((len(batch), maxlen), dtype=np.int64)
        for i, e in enumerate(encs):
            ids[i, : len(e.ids)] = e.ids
            mask[i, : len(e.attention_mask)] = e.attention_mask
        outputs = sess.run(None, {"input_ids": ids, "attention_mask": mask})
        names = [o.name for o in sess.get_outputs()]
        idx = names.index("sentence_embedding") if "sentence_embedding" in names else 0
        vec = np.asarray(outputs[idx], dtype=np.float32)
        # safety L2
        norms = np.linalg.norm(vec, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-12)
        out[start : start + len(batch)] = vec / norms
        done = start + len(batch)
        if done == n or done % (batch_size * 40) < batch_size:
            thr = done / max(time.perf_counter() - t0, 1e-6)
            print(f"  encode {done}/{n} thr={thr:.0f}/s", flush=True)
    print(f"  encode done in {time.perf_counter() - t0:.1f}s", flush=True)
    return out


def topk_neighbors(
    matrix: np.ndarray,
    *,
    k: int,
    block: int = 1024,
) -> tuple[np.ndarray, np.ndarray]:
    """Per-row top-k indices/scores excluding self. matrix rows L2-normalized."""
    n = matrix.shape[0]
    d = matrix.shape[1]
    k = min(k, max(0, n - 1))
    if k <= 0:
        return np.zeros((n, 0), dtype=np.int32), np.zeros((n, 0), dtype=np.float32)

    x = np.ascontiguousarray(matrix, dtype=np.float32)
    t0 = time.perf_counter()
    try:
        import faiss  # type: ignore

        index = faiss.IndexFlatIP(d)
        index.add(x)
        # fetch k+1; drop self via score mask (handles near-duplicate score=1.0 rows)
        scores, idx = index.search(x, k + 1)
        self_mask = idx == np.arange(n, dtype=idx.dtype)[:, None]
        scores = scores.copy()
        scores[self_mask] = -np.inf
        order = np.argsort(-scores, axis=1)[:, :k]
        top_i = np.take_along_axis(idx, order, axis=1).astype(np.int32)
        top_s = np.take_along_axis(scores, order, axis=1).astype(np.float32)
        print(f"  topk faiss done in {time.perf_counter() - t0:.1f}s", flush=True)
        return top_i, top_s
    except Exception as e:
        print(f"  faiss unavailable ({type(e).__name__}: {e}); numpy blocked fallback", flush=True)

    top_i = np.full((n, k), -1, dtype=np.int32)
    top_s = np.full((n, k), -np.inf, dtype=np.float32)
    base = x
    for i0 in range(0, n, block):
        q = x[i0 : i0 + block]
        s = q @ base.T
        b = s.shape[0]
        for bi in range(b):
            s[bi, i0 + bi] = -np.inf
        part = np.argpartition(-s, kth=k - 1, axis=1)[:, :k]
        rows = np.arange(b)[:, None]
        vals = s[rows, part]
        order = np.argsort(-vals, axis=1)
        part = np.take_along_axis(part, order, axis=1)
        vals = np.take_along_axis(vals, order, axis=1)
        top_i[i0 : i0 + b] = part.astype(np.int32)
        top_s[i0 : i0 + b] = vals.astype(np.float32)
        if (i0 // block) % 20 == 0:
            print(f"  topk rows {min(i0 + block, n)}/{n}", flush=True)
    print(f"  topk done in {time.perf_counter() - t0:.1f}s", flush=True)
    return top_i, top_s


def direct_syn_degree_by_char(db) -> dict[str, int]:
    """Undirected syn degree per 字面 (excludes embedding_cosine)."""
    from sqlalchemy import text

    rows = db.execute(
        text(
            """
            SELECT w1.char, w2.char
            FROM word_relations wr
            JOIN words w1 ON w1.id = wr.word_id
            JOIN words w2 ON w2.id = wr.related_id
            WHERE wr.relation_type = 'syn'
              AND COALESCE(wr.source, '') != :src
            """
        ),
        {"src": SOURCE},
    ).fetchall()
    adj: dict[str, set[str]] = defaultdict(set)
    for a, b in rows:
        if not a or not b or a == b:
            continue
        adj[a].add(b)
        adj[b].add(a)
    return {c: len(s) for c, s in adj.items()}


def write_proposal_tsv(
    path: Path,
    chars: list[str],
    top_i: np.ndarray,
    top_s: np.ndarray,
    *,
    k: int,
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n_lines = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("head\ttail\tscore\trank\tmodel_version\n")
        for hi, head in enumerate(chars):
            for rank in range(min(k, top_i.shape[1])):
                j = int(top_i[hi, rank])
                if j < 0:
                    continue
                score = float(top_s[hi, rank])
                f.write(
                    f"{head}\t{chars[j]}\t{score:.6f}\t{rank + 1}\t{MODEL_VERSION}\n"
                )
                n_lines += 1
    return n_lines


def collect_a_tuples(
    chars: list[str],
    char_to_id: dict[str, int],
    top_i: np.ndarray,
    top_s: np.ndarray,
    degrees: dict[str, int],
    *,
    syn_degree_lt: int,
    a_topk: int,
    min_cosine: float,
) -> list:
    from app.domain.relations.bulk_insert import normalize_relation_tuple

    rows = []
    for hi, head in enumerate(chars):
        if degrees.get(head, 0) >= syn_degree_lt:
            continue
        hid = char_to_id.get(head)
        if hid is None:
            continue
        written = 0
        for rank in range(min(a_topk, top_i.shape[1])):
            j = int(top_i[hi, rank])
            if j < 0:
                continue
            score = float(top_s[hi, rank])
            if score < min_cosine:
                continue
            tail = chars[j]
            tid = char_to_id.get(tail)
            if tid is None:
                continue
            row = normalize_relation_tuple(
                hid, tid, RELATION_TYPE, score, SOURCE, None
            )
            if row is None:
                continue
            rows.append(row)
            written += 1
            if written >= a_topk:
                break
    return rows


def bake_embedding_topk(
    db,
    *,
    model_dir: Path = DEFAULT_MODEL_DIR,
    cache_dir: Path = DEFAULT_CACHE,
    proposal_tsv: Path | None = None,
    vectors_path: Path | None = None,
    syn_degree_lt: int = DEFAULT_SYN_DEGREE_LT,
    a_topk: int = DEFAULT_A_TOPK,
    a_min_cosine: float = DEFAULT_A_MIN_COSINE,
    c_topk: int = DEFAULT_C_TOPK,
    encode_batch: int = DEFAULT_ENCODE_BATCH,
    replace: bool = True,
    skip_encode: bool = False,
    write_db: bool = True,
    write_edges: bool = False,
    strip_edges: bool = True,
    nbr_bin_path: Path | str | None = None,
    nbr_meta_path: Path | str | None = None,
    limit_chars: int | None = None,
) -> dict:
    from app.domain.relations.char_index import get_char_to_primary_id
    from app.domain.relations.store import insert_relation_records
    from ingest.syn_ant_build import clear_word_relations_source

    cache_dir.mkdir(parents=True, exist_ok=True)
    vectors_path = vectors_path or (cache_dir / "vectors_bge-m3.npz")
    proposal_tsv = proposal_tsv or (cache_dir / "embedding_syn_topk_proposals.tsv")

    char_to_id = get_char_to_primary_id(db)
    chars = sorted(char_to_id.keys())
    if limit_chars is not None:
        chars = chars[: max(0, int(limit_chars))]
    stats: dict = {
        "chars": len(chars),
        "model_version": MODEL_VERSION,
        "syn_degree_lt": syn_degree_lt,
        "a_topk": a_topk,
        "a_min_cosine": a_min_cosine,
        "c_topk": c_topk,
    }

    if skip_encode and vectors_path.is_file():
        data = np.load(vectors_path, allow_pickle=True)
        saved = list(data["chars"])
        matrix = data["matrix"].astype(np.float32)
        if saved != chars:
            # allow subset if limit_chars
            idx = {c: i for i, c in enumerate(saved)}
            if not all(c in idx for c in chars):
                raise RuntimeError("vectors sidecar chars mismatch; re-encode")
            matrix = matrix[[idx[c] for c in chars]]
        stats["encode"] = "sidecar"
        print(f"loaded vectors {matrix.shape} from {vectors_path}", flush=True)
    else:
        print("loading CUDA bge-m3…", flush=True)
        sess, tok, available = require_cuda_session(model_dir)
        stats["ort_available"] = available
        stats["session_providers"] = list(sess.get_providers())
        print(f"CUDA ok providers={stats['session_providers']}", flush=True)
        matrix = encode_chars(chars, sess, tok, batch_size=encode_batch)
        np.savez_compressed(vectors_path, chars=np.array(chars, dtype=object), matrix=matrix)
        stats["vectors_path"] = str(vectors_path)
        stats["encode"] = "gpu"

    k_need = max(a_topk, c_topk)
    top_i, top_s = topk_neighbors(matrix, k=k_need)

    n_prop = write_proposal_tsv(proposal_tsv, chars, top_i, top_s, k=c_topk)
    stats["proposal_lines"] = n_prop
    stats["proposal_tsv"] = str(proposal_tsv)
    print(f"C proposals: {n_prop} lines -> {proposal_tsv}", flush=True)

    degrees = direct_syn_degree_by_char(db)
    eligible = sum(1 for c in chars if degrees.get(c, 0) < syn_degree_lt)
    stats["a_eligible_heads"] = eligible
    tuples = collect_a_tuples(
        chars,
        char_to_id,
        top_i,
        top_s,
        degrees,
        syn_degree_lt=syn_degree_lt,
        a_topk=a_topk,
        min_cosine=a_min_cosine,
    )
    # dedupe undirected
    from app.domain.relations.bulk_insert import collect_unique_relation_tuples

    tuples = collect_unique_relation_tuples(tuples)
    stats["a_candidate_edges"] = len(tuples)

    # E1c: CSR bin (關係包資產) — always when we have A edges
    from app.domain.lexicon.embedding_nbr_codec import (
        NBR_VERSION,
        build_bidirectional_adj,
        encode_csr_blob,
        write_nbr_bundle,
    )

    nbr_bin = Path(nbr_bin_path) if nbr_bin_path else (cache_dir / "embedding-nbr.bin")
    nbr_meta = Path(nbr_meta_path) if nbr_meta_path else (cache_dir / "embedding-nbr.meta.json")
    public_bin = ROOT / "client" / "public" / "embedding-nbr.bin"
    public_meta = ROOT / "client" / "public" / "embedding-nbr.meta.json"

    undirected = [(t[0], t[1], float(t[3] or 0.5)) for t in tuples]
    adj = build_bidirectional_adj(undirected)
    blob = encode_csr_blob(adj)
    from app.domain.lexicon.embedding_nbr_codec import char_id_fingerprint

    fp = char_id_fingerprint(char_to_id)
    meta = write_nbr_bundle(
        blob,
        bin_path=nbr_bin,
        meta_path=nbr_meta,
        model_version=MODEL_VERSION,
        extra={
            "syn_degree_lt": syn_degree_lt,
            "a_topk": a_topk,
            "a_min_cosine": a_min_cosine,
            "char_id_fingerprint": fp,
            "char_count": len(char_to_id),
        },
    )
    # ship beside static-*-index.json
    try:
        public_bin.parent.mkdir(parents=True, exist_ok=True)
        public_bin.write_bytes(blob)
        public_meta.write_text(nbr_meta.read_text(encoding="utf-8"), encoding="utf-8")
        stats["public_nbr_bin"] = str(public_bin)
    except OSError as e:
        stats["public_nbr_bin_error"] = str(e)
    stats["nbr_version"] = NBR_VERSION
    stats["nbr_bin"] = str(nbr_bin)
    stats["nbr_meta"] = meta
    print(
        f"E1c nbr bin: {meta.get('n_heads')} heads / {meta.get('n_edges')} dir-edges "
        f"-> {nbr_bin} ({len(blob)} bytes)",
        flush=True,
    )

    if write_db:
        if replace:
            cleared = clear_word_relations_source(db, SOURCE)
            stats["cleared"] = cleared
            print(f"cleared source={SOURCE!r}: {cleared}", flush=True)
        if write_edges:
            ins = insert_relation_records(db, tuples)
            stats["a_insert"] = ins
            print(f"A insert edges: {ins}", flush=True)
        else:
            stats["a_insert"] = {"skipped_edges": True, "attempted": len(tuples)}
            print("A edges skipped (E1c bin is authority for delivery)", flush=True)
    else:
        stats["a_insert"] = {"skipped": True, "attempted": len(tuples)}

    if strip_edges and not write_edges:
        cleared2 = clear_word_relations_source(db, SOURCE)
        stats["strip_edges"] = cleared2
        print(f"strip embedding_cosine edges: {cleared2}", flush=True)

    return stats


def export_nbr_from_existing_edges(
    db,
    *,
    cache_dir: Path = DEFAULT_CACHE,
    model_version: str = MODEL_VERSION,
    strip_edges: bool = True,
) -> dict:
    """Build e1 bin from current word_relations embedding_cosine rows (no re-encode)."""
    from app.domain.lexicon.embedding_nbr_codec import (
        NBR_VERSION,
        build_bidirectional_adj,
        char_id_fingerprint_from_db,
        edges_from_word_relations_db,
        encode_csr_blob,
        write_nbr_bundle,
    )
    from ingest.syn_ant_build import clear_word_relations_source

    cache_dir.mkdir(parents=True, exist_ok=True)
    edges = edges_from_word_relations_db(db, SOURCE)
    adj = build_bidirectional_adj(edges)
    blob = encode_csr_blob(adj)
    nbr_bin = cache_dir / "embedding-nbr.bin"
    nbr_meta = cache_dir / "embedding-nbr.meta.json"
    fp = char_id_fingerprint_from_db(db)
    meta = write_nbr_bundle(
        blob,
        bin_path=nbr_bin,
        meta_path=nbr_meta,
        model_version=model_version,
        extra={"char_id_fingerprint": fp},
    )
    public_bin = ROOT / "client" / "public" / "embedding-nbr.bin"
    public_meta = ROOT / "client" / "public" / "embedding-nbr.meta.json"
    public_bin.write_bytes(blob)
    public_meta.write_text(nbr_meta.read_text(encoding="utf-8"), encoding="utf-8")
    stats = {
        "nbr_version": NBR_VERSION,
        "from_edges": len(edges),
        "meta": meta,
        "nbr_bin": str(nbr_bin),
        "public_bin": str(public_bin),
        "char_id_fingerprint": fp,
    }
    if strip_edges:
        stats["stripped"] = clear_word_relations_source(db, SOURCE)
    return stats


__all__ = [
    "DEFAULT_A_MIN_COSINE",
    "DEFAULT_A_TOPK",
    "DEFAULT_C_TOPK",
    "DEFAULT_MODEL_DIR",
    "DEFAULT_SYN_DEGREE_LT",
    "MODEL_VERSION",
    "SOURCE",
    "bake_embedding_topk",
    "export_nbr_from_existing_edges",
    "require_cuda_session",
]
