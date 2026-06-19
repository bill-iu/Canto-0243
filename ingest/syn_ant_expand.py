"""近義橋反義 expand strategies — ingest only（CONTEXT § 近義橋反義）。"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.domain.relations.canonical import canonical_word_ids
from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.store import (
    fetch_existing_relation_keys as _fetch_existing_keys,
    insert_relation_candidates as _insert_bridge_candidates,
    insert_relations as _insert_relations,
)
from app.models.word import Word, WordRelation

INSERT_BATCH = 300
SQL_IN_BATCH = 300

def _build_cilin_syn_adjacency(db: Session, *, cilin_syn_source: str = "cilin") -> Dict[int, Set[int]]:
    """Bidirectional Cilin synonym neighbors keyed by word id."""
    syn_neighbors: Dict[int, Set[int]] = {}
    rows = (
        db.query(WordRelation.word_id, WordRelation.related_id)
        .filter(
            WordRelation.relation_type == "syn",
            WordRelation.source == cilin_syn_source,
        )
        .all()
    )
    for w, r in rows:
        syn_neighbors.setdefault(int(w), set()).add(int(r))
        syn_neighbors.setdefault(int(r), set()).add(int(w))
    return syn_neighbors


def expand_antonyms_via_cilin_synonyms(
    db: Session,
    *,
    source: str = "ant_cilin_exanded",
    cilin_syn_source: str = "cilin",
    confidence: float = 0.75,
    dedupe_existing: bool = True,
    batch_size: int = INSERT_BATCH,
) -> dict:
    """Expand ant relations using Cilin synonym neighbors of each antonym endpoint.

    Example: if 快樂 ant 悲傷 and 悲傷 syn 傷心/難過 (cilin), insert 快樂 ant 傷心/難過.
    Processes all existing ant seeds; dedupes by canonical (word_id, related_id, ant).
    """
    source = (source or "ant_cilin_exanded")[:32]
    stats = {
        "ant_seeds": 0,
        "candidate_pairs": 0,
        "inserted": 0,
        "skipped_existing": 0,
        "skipped_self": 0,
        "skipped_no_syn": 0,
    }

    syn_neighbors = _build_cilin_syn_adjacency(db, cilin_syn_source=cilin_syn_source)
    if not syn_neighbors:
        return stats

    ant_rows = (
        db.query(WordRelation.word_id, WordRelation.related_id)
        .filter(WordRelation.relation_type == "ant")
        .all()
    )
    stats["ant_seeds"] = len(ant_rows)
    if not ant_rows:
        return stats

    candidates: Dict[Tuple[int, int, str], dict] = {}
    for word_id, related_id in ant_rows:
        a, b = int(word_id), int(related_id)
        syns_b = syn_neighbors.get(b)
        syns_a = syn_neighbors.get(a)
        if not syns_b and not syns_a:
            stats["skipped_no_syn"] += 1
            continue
        if syns_b:
            for syn_id in syns_b:
                if syn_id == a:
                    stats["skipped_self"] += 1
                    continue
                w, r = canonical_word_ids(a, syn_id)
                if w == r:
                    stats["skipped_self"] += 1
                    continue
                key = (w, r, "ant")
                candidates[key] = {
                    "word_id": w,
                    "related_id": r,
                    "relation_type": "ant",
                    "score": confidence,
                    "source": source,
                }
        if syns_a:
            for syn_id in syns_a:
                if syn_id == b:
                    stats["skipped_self"] += 1
                    continue
                w, r = canonical_word_ids(syn_id, b)
                if w == r:
                    stats["skipped_self"] += 1
                    continue
                key = (w, r, "ant")
                candidates[key] = {
                    "word_id": w,
                    "related_id": r,
                    "relation_type": "ant",
                    "score": confidence,
                    "source": source,
                }

    stats["candidate_pairs"] = len(candidates)
    if not candidates:
        return stats

    pending = list(candidates.values())
    if dedupe_existing:
        keys = [(c["word_id"], c["related_id"], c["relation_type"]) for c in pending]
        existing: Set[Tuple] = set()
        for i in range(0, len(keys), SQL_IN_BATCH):
            existing.update(_fetch_existing_keys(db, keys[i:i + SQL_IN_BATCH]))
        before = len(pending)
        pending = [
            c for c in pending
            if (c["word_id"], c["related_id"], c["relation_type"]) not in existing
        ]
        stats["skipped_existing"] = before - len(pending)

    if pending:
        for i in range(0, len(pending), batch_size):
            chunk = pending[i:i + batch_size]
            stats["inserted"] += _insert_relations(db, [WordRelation(**c) for c in chunk])

    return stats


ANT_SYN_MIRROR_SOURCE = "ant_syn_mirror"


def collect_ant_mirror_char_pairs(
    db: Session,
    *,
    include_static: bool = True,
    exclude_sources: Optional[Set[str]] = None,
) -> Set[Tuple[str, str]]:
    """Char pairs (head, tail) matching runtime ``!head`` expansion: ant endpoints + their syns."""
    from app.domain.relations.graph import CharRelationGraph
    from app.domain.thesaurus.port import default_thesaurus_port

    graph = CharRelationGraph(db, default_thesaurus_port())
    return graph.collect_mirror_ant_pairs(
        include_static=include_static,
        exclude_sources=exclude_sources,
    )


def expand_antonyms_via_syn_endpoints(
    db: Session,
    *,
    source: str = ANT_SYN_MIRROR_SOURCE,
    confidence: float = 0.72,
    dedupe_existing: bool = True,
    include_static: bool = True,
    batch_size: int = INSERT_BATCH,
) -> dict:
    """Persist ``!query`` results as ant word_relations via ant-endpoint synonym expansion.

    Uses direct ant seeds (excluding prior mirror rows), then adds one hop through
    synonym neighbors of each ant endpoint — same logic as runtime ``!`` search.
    """
    source = (source or ANT_SYN_MIRROR_SOURCE)[:32]
    stats = {
        "ant_seed_orientations": 0,
        "mirror_char_pairs": 0,
        "candidate_pairs": 0,
        "inserted": 0,
        "skipped_existing": 0,
        "skipped_no_char_id": 0,
        "skipped_self": 0,
    }

    char_to_id = get_char_to_primary_id(db)
    from app.domain.relations.graph import CharRelationGraph
    from app.domain.thesaurus.port import default_thesaurus_port

    graph = CharRelationGraph(db, default_thesaurus_port())
    seeds = graph.direct_ant_oriented_pairs(exclude_sources={source})
    stats["ant_seed_orientations"] = len(seeds)
    if not seeds:
        return stats

    mirror_pairs = collect_ant_mirror_char_pairs(
        db,
        include_static=include_static,
        exclude_sources={source},
    )
    stats["mirror_char_pairs"] = len(mirror_pairs)

    candidates: Dict[Tuple[int, int, str], dict] = {}
    for head_char, tail_char in mirror_pairs:
        if head_char == tail_char:
            stats["skipped_self"] += 1
            continue
        head_id = char_to_id.get(head_char)
        tail_id = char_to_id.get(tail_char)
        if not head_id or not tail_id:
            stats["skipped_no_char_id"] += 1
            continue
        w, r = canonical_word_ids(head_id, tail_id)
        if w == r:
            stats["skipped_self"] += 1
            continue
        key = (w, r, "ant")
        candidates[key] = {
            "word_id": w,
            "related_id": r,
            "relation_type": "ant",
            "score": confidence,
            "source": source,
        }

    stats["candidate_pairs"] = len(candidates)
    if not candidates:
        return stats

    pending = list(candidates.values())
    if dedupe_existing:
        keys = [(c["word_id"], c["related_id"], c["relation_type"]) for c in pending]
        existing: Set[Tuple] = set()
        for i in range(0, len(keys), SQL_IN_BATCH):
            existing.update(_fetch_existing_keys(db, keys[i:i + SQL_IN_BATCH]))
        before = len(pending)
        pending = [
            c for c in pending
            if (c["word_id"], c["related_id"], c["relation_type"]) not in existing
        ]
        stats["skipped_existing"] = before - len(pending)

    if pending:
        for i in range(0, len(pending), batch_size):
            chunk = pending[i:i + batch_size]
            stats["inserted"] += _insert_relations(db, [WordRelation(**c) for c in chunk])

    return stats


ANT_SYN_BRIDGE_SOURCE = "ant_syn_bridge"
DEFAULT_MIN_BRIDGE_COSINE = 0.80
DEFAULT_MAX_BRIDGED_ANTS_PER_HEAD = 30


def _merge_bridge_ants_by_score(
    qualified_bridges: List[Tuple[str, List[str], float]],
    *,
    max_ants: int,
) -> List[Tuple[str, float]]:
    """Dedupe ants across bridges; keep highest 橋分 per ant; rank and cap."""
    best_score: Dict[str, float] = {}
    for _syn_char, direct_ants, score in qualified_bridges:
        rounded = round(float(score), 4)
        for ant_char in direct_ants:
            if not ant_char:
                continue
            prev = best_score.get(ant_char)
            if prev is None or rounded > prev:
                best_score[ant_char] = rounded
    ranked = sorted(best_score.items(), key=lambda item: (-item[1], item[0]))
    return ranked[: max(0, int(max_ants))]


def _empty_bridge_stats() -> dict:
    return {
        "total_targets": 0,
        "offset": 0,
        "targets": 0,
        "batches": 0,
        "bridged": 0,
        "skipped_no_bridge": 0,
        "skipped_no_model": 0,
        "skipped_self": 0,
        "skipped_no_char_id": 0,
        "candidate_pairs": 0,
        "inserted": 0,
        "skipped_existing": 0,
    }


def _merge_bridge_stats(into: dict, chunk: dict) -> None:
    for key, value in chunk.items():
        if key in ("total_targets", "offset", "batches", "targets"):
            continue
        if isinstance(value, (int, float)):
            into[key] = into.get(key, 0) + value


def _process_bridge_targets(
    db: Session,
    targets: List[str],
    *,
    source: str,
    include_static: bool,
    embed_batch_size: int,
    model,
    char_to_id: Dict[str, int],
    pool_ctx,
    global_ant_chars: Set[str],
    embedding_cache: Dict[str, List[float]],
    min_bridge_cosine: float = DEFAULT_MIN_BRIDGE_COSINE,
    max_bridged_ants_per_head: int = DEFAULT_MAX_BRIDGED_ANTS_PER_HEAD,
    progress_interval: int = 50,
    on_progress=None,
    progress_base: int = 0,
) -> Tuple[dict, Dict[Tuple[int, int, str], dict]]:
    from app.utils.embedding import cosine_similarity

    stats = _empty_bridge_stats()
    stats["targets"] = len(targets)
    candidates: Dict[Tuple[int, int, str], dict] = {}

    def _cached_embeddings(chars: Iterable[str]) -> None:
        missing = [c for c in dict.fromkeys(chars) if c and c not in embedding_cache]
        for i in range(0, len(missing), embed_batch_size):
            chunk = missing[i : i + embed_batch_size]
            embedding_cache.update(_encode_char_batch(chunk, model))

    def _syn_might_have_ants(syn_char: str) -> bool:
        if syn_char in global_ant_chars:
            return True
        if include_static and pool_ctx.thesaurus.get_antonyms(syn_char):
            return True
        return False

    for idx, head_char in enumerate(targets):
        if progress_interval > 0 and on_progress is not None and idx > 0 and idx % progress_interval == 0:
            on_progress(progress_base + idx, stats)

        head_id = char_to_id.get(head_char)
        if not head_id:
            stats["skipped_no_char_id"] += 1
            continue

        syn_pool = pool_ctx.relation_chars(head_char, "syn")
        bridge_options: List[Tuple[str, List[str]]] = []
        chars_to_embed = [head_char, *syn_pool]
        for syn_char in syn_pool:
            if not syn_char or syn_char == head_char:
                continue
            if not _syn_might_have_ants(syn_char):
                continue
            direct_ants = pool_ctx.relation_chars(syn_char, "ant")
            if not direct_ants:
                continue
            chars_to_embed.extend(direct_ants)
            bridge_options.append((syn_char, direct_ants))

        if not bridge_options:
            stats["skipped_no_bridge"] += 1
            continue

        _cached_embeddings(chars_to_embed)
        head_vec = embedding_cache.get(head_char)
        if not head_vec:
            stats["skipped_no_bridge"] += 1
            continue

        qualified_bridges: List[Tuple[str, List[str], float]] = []
        for syn_char, direct_ants in bridge_options:
            syn_vec = embedding_cache.get(syn_char)
            if not syn_vec:
                continue
            score = cosine_similarity(head_vec, syn_vec)
            if score < min_bridge_cosine:
                continue
            qualified_bridges.append((syn_char, direct_ants, score))

        if not qualified_bridges:
            stats["skipped_no_bridge"] += 1
            continue

        stats["bridged"] += 1
        merged_ants = _merge_bridge_ants_by_score(
            qualified_bridges,
            max_ants=max_bridged_ants_per_head,
        )

        for ant_char, bridge_score in merged_ants:
            if not ant_char or ant_char == head_char:
                stats["skipped_self"] += 1
                continue
            tail_id = char_to_id.get(ant_char)
            if not tail_id:
                stats["skipped_no_char_id"] += 1
                continue
            w, r = canonical_word_ids(head_id, tail_id)
            if w == r:
                stats["skipped_self"] += 1
                continue
            key = (w, r, "ant")
            candidates[key] = {
                "word_id": w,
                "related_id": r,
                "relation_type": "ant",
                "score": bridge_score,
                "source": source,
            }

    stats["candidate_pairs"] = len(candidates)
    return stats, candidates


def _chars_with_relations_of_type(db: Session, relation_type: str) -> Set[str]:
    from sqlalchemy.orm import aliased

    chars: Set[str] = set()
    w_head = aliased(Word)
    w_tail = aliased(Word)
    for ch, in (
        db.query(w_head.char)
        .join(WordRelation, WordRelation.word_id == w_head.id)
        .filter(WordRelation.relation_type == relation_type)
        .distinct()
        .all()
    ):
        if ch:
            chars.add(ch)
    for ch, in (
        db.query(w_tail.char)
        .join(WordRelation, WordRelation.related_id == w_tail.id)
        .filter(WordRelation.relation_type == relation_type)
        .distinct()
        .all()
    ):
        if ch:
            chars.add(ch)
    return chars


def _encode_char_batch(chars: List[str], model) -> Dict[str, List[float]]:
    if not chars or model is None:
        return {}
    unique = list(dict.fromkeys(c for c in chars if c))
    embs = model.encode(unique, normalize_embeddings=True)
    return {ch: embs[i].tolist() for i, ch in enumerate(unique)}


def _load_embedding_model():
    from app.utils.embedding import enable_embedding_model_for_ingest

    enable_embedding_model_for_ingest()
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def expand_antonyms_via_embedding_syn_bridge(
    db: Session,
    *,
    source: str = ANT_SYN_BRIDGE_SOURCE,
    dedupe_existing: bool = True,
    include_static: bool = True,
    batch_size: int = INSERT_BATCH,
    embed_batch_size: int = 256,
    offset: int = 0,
    limit: Optional[int] = None,
    chunk_size: Optional[int] = None,
    min_bridge_cosine: float = DEFAULT_MIN_BRIDGE_COSINE,
    max_bridged_ants_per_head: int = DEFAULT_MAX_BRIDGED_ANTS_PER_HEAD,
    on_batch=None,
    on_progress=None,
    progress_interval: int = 50,
) -> dict:
    """近義橋反義：有 syn、無 ant 的字面 → 多橋合併、橋分排序 → 借 direct ant。

    See CONTEXT § 近義橋反義.

    When ``chunk_size`` is set, processes targets in chunks and inserts after each chunk
    (checkpoint-friendly). ``offset`` / ``limit`` slice the sorted target list.
    """
    from ingest.bridge_pool_context import IngestBridgePoolContext

    source = (source or ANT_SYN_BRIDGE_SOURCE)[:32]
    stats = _empty_bridge_stats()
    stats["offset"] = max(0, int(offset or 0))

    syn_chars = _chars_with_relations_of_type(db, "syn")
    ant_chars = _chars_with_relations_of_type(db, "ant")
    all_targets = sorted(syn_chars - ant_chars)
    stats["total_targets"] = len(all_targets)

    start = stats["offset"]
    end = len(all_targets) if limit is None else min(len(all_targets), start + max(0, int(limit)))
    targets = all_targets[start:end]
    stats["targets"] = len(targets)
    if not targets:
        return stats

    model = _load_embedding_model()
    if model is None:
        stats["skipped_no_model"] = len(targets)
        return stats

    char_to_id = get_char_to_primary_id(db)
    pool_ctx = IngestBridgePoolContext(db, include_static=include_static)
    global_ant_chars = ant_chars
    embedding_cache: Dict[str, List[float]] = {}

    chunk = max(0, int(chunk_size)) if chunk_size else 0
    if chunk > 0:
        total_batches = (len(targets) + chunk - 1) // chunk
        for batch_idx in range(total_batches):
            batch_start = batch_idx * chunk
            batch_targets = targets[batch_start : batch_start + chunk]
            chunk_stats, candidates = _process_bridge_targets(
                db,
                batch_targets,
                source=source,
                include_static=include_static,
                embed_batch_size=embed_batch_size,
                model=model,
                char_to_id=char_to_id,
                pool_ctx=pool_ctx,
                global_ant_chars=global_ant_chars,
                embedding_cache=embedding_cache,
                min_bridge_cosine=min_bridge_cosine,
                max_bridged_ants_per_head=max_bridged_ants_per_head,
                progress_interval=progress_interval,
                on_progress=on_progress,
                progress_base=start + batch_start,
            )
            inserted, skipped_existing = _insert_bridge_candidates(
                db,
                candidates,
                dedupe_existing=dedupe_existing,
                batch_size=batch_size,
            )
            chunk_stats["inserted"] = inserted
            chunk_stats["skipped_existing"] = skipped_existing
            embedding_cache.clear()
            stats["batches"] += 1
            _merge_bridge_stats(stats, chunk_stats)
            if on_batch is not None:
                chunk_stats["total_targets"] = stats["total_targets"]
                on_batch(
                    batch_idx + 1,
                    total_batches,
                    chunk_stats,
                    start + batch_start + len(batch_targets),
                )
        return stats

    chunk_stats, candidates = _process_bridge_targets(
        db,
        targets,
        source=source,
        include_static=include_static,
        embed_batch_size=embed_batch_size,
        model=model,
        char_to_id=char_to_id,
        pool_ctx=pool_ctx,
        global_ant_chars=global_ant_chars,
        embedding_cache=embedding_cache,
        min_bridge_cosine=min_bridge_cosine,
        max_bridged_ants_per_head=max_bridged_ants_per_head,
        progress_interval=progress_interval,
        on_progress=on_progress,
        progress_base=start,
    )
    inserted, skipped_existing = _insert_bridge_candidates(
        db,
        candidates,
        dedupe_existing=dedupe_existing,
        batch_size=batch_size,
    )
    chunk_stats["inserted"] = inserted
    chunk_stats["skipped_existing"] = skipped_existing
    stats["batches"] = 1
    _merge_bridge_stats(stats, chunk_stats)
    return stats

__all__ = [
    "ANT_SYN_BRIDGE_SOURCE",
    "ANT_SYN_MIRROR_SOURCE",
    "DEFAULT_MAX_BRIDGED_ANTS_PER_HEAD",
    "DEFAULT_MIN_BRIDGE_COSINE",
    "collect_ant_mirror_char_pairs",
    "expand_antonyms_via_cilin_synonyms",
    "expand_antonyms_via_embedding_syn_bridge",
    "expand_antonyms_via_syn_endpoints",
]
