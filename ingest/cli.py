"""Syn/Ant ingest v2 CLI (`python -m ingest <command>`)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.database import SessionLocal, ensure_syn_ant_edges_table, ensure_word_relations_table
from app.models.word import SynAntEdge, WordRelation
from ingest.ingest_lock import IngestLockError, ingest_lock
from ingest.syn_ant_manifest import load_manifest, manifest_report, resolve_source_path, select_sources
from ingest.syn_ant_build import (
    build_word_relations_from_staging,
    clear_word_relations_source,
    ingest_cilin_leaf_direct,
)
from ingest.syn_ant_staging import persist_staging_edges, staging_report
from ingest.syn_ant_expand import (
    expand_antonyms_via_cilin_synonyms,
    expand_antonyms_via_embedding_syn_bridge,
    expand_antonyms_via_syn_endpoints,
)
from app.repositories.word_relation_repo import load_db_char_set
from ingest.syn_ant_normalize import merge_staging_edges, normalize_edges
from ingest.syn_ant_sources import iter_cilin_line_chunks, parse_cilin_lines, parse_sources


def cmd_report(_: argparse.Namespace) -> int:
    print(manifest_report())
    print()
    ensure_syn_ant_edges_table()
    ensure_word_relations_table()
    with SessionLocal() as db:
        print(staging_report(db))
        rel_count = db.query(WordRelation).count()
        syn_count = db.query(WordRelation).filter(WordRelation.relation_type == "syn").count()
        print(f"\nword_relations rows: {rel_count} (syn: {syn_count})")
    return 0


def cmd_normalize(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    sources = select_sources(
        manifest,
        source_ids=args.source or None,
        defaults_only=not bool(args.source),
    )
    if not sources:
        print("No sources selected.")
        return 1

    print(f"Parsing {len(sources)} source(s)...")
    raw_edges = parse_sources(sources)
    print(f"Raw edges: {len(raw_edges)}")

    ensure_syn_ant_edges_table()
    with SessionLocal() as db:
        db_chars = load_db_char_set(db)
        normalized = normalize_edges(raw_edges, db_chars=db_chars, allow_external=args.allow_external)
        merged = merge_staging_edges(normalized)
        print(f"Normalized edges: {len(normalized)} -> merged unique: {len(merged)}")
        n = persist_staging_edges(db, merged, clear=not args.append)
        print(f"Persisted {n} rows to syn_ant_edges staging.")
    return 0


def cmd_build_relations(args: argparse.Namespace) -> int:
    ensure_syn_ant_edges_table()
    ensure_word_relations_table()
    with SessionLocal() as db:
        stats = build_word_relations_from_staging(
            db,
            allow_external=args.allow_external,
            batch_size=args.batch_size,
            source=args.source,
            use_batched_sql=args.batched,
        )
        print("build-relations stats:", stats)
    return 0


def _resolve_cilin_path(args: argparse.Namespace, src: dict) -> Path | None:
    if args.source_path:
        p = Path(args.source_path)
        return p if p.exists() else None
    p = resolve_source_path(src)
    return p if p and p.exists() else None


def cmd_ingest_cilin(args: argparse.Namespace) -> int:
    manifest = load_manifest(args.manifest)
    sources = select_sources(manifest, source_ids=["cilin"])
    if not sources:
        print("Cilin source not found in manifest.")
        return 1
    src = sources[0]
    path = _resolve_cilin_path(args, src)
    if path is None:
        print(f"Cilin file missing: {args.source_path or resolve_source_path(src)}")
        return 1

    chunk_size = args.chunk_size
    source_id = src["id"]
    source_rank = int(src.get("source_rank") or 55)

    ensure_word_relations_table()

    if not args.staging:
        print(f"Cilin direct ingest from {path} (chunk={chunk_size}, dedupe={args.dedupe_existing})")
        with SessionLocal() as db:
            if args.replace_relations:
                removed = clear_word_relations_source(db, source_id)
                print(f"Cleared {removed} existing word_relations with source={source_id!r}")
            stats = ingest_cilin_leaf_direct(
                db,
                path,
                source=source_id,
                chunk_size=chunk_size,
                dedupe_existing=args.dedupe_existing,
            )
            print("ingest-cilin stats:", stats)
        return 0

    ensure_syn_ant_edges_table()
    total_lines = 0
    total_persisted = 0
    batch_num = 0

    with SessionLocal() as db:
        db_chars = load_db_char_set(db)
        db.query(SynAntEdge).filter(SynAntEdge.source == source_id).delete()
        db.commit()
        if args.replace_relations:
            removed = clear_word_relations_source(db, source_id)
            print(f"Cleared {removed} existing word_relations with source={source_id!r}")

        for lines in iter_cilin_line_chunks(path, chunk_size=chunk_size):
            batch_num += 1
            total_lines += len(lines)
            raw = parse_cilin_lines(lines, source_id, source_rank=source_rank)
            normalized = normalize_edges(raw, db_chars=db_chars, allow_external=args.allow_external)
            merged = merge_staging_edges(normalized)
            n = persist_staging_edges(db, merged, clear=False, batch_size=chunk_size)
            total_persisted += n
            print(f"  chunk {batch_num}: {len(lines)} lines -> {len(merged)} edges ({n} rows)", flush=True)

    print(f"Cilin staging done: {total_lines} lines in {batch_num} chunks, {total_persisted} staging rows.")

    with SessionLocal() as db:
        stats = build_word_relations_from_staging(
            db,
            allow_external=args.allow_external,
            batch_size=chunk_size,
            source=source_id,
            use_batched_sql=True,
        )
        print("build-relations stats:", stats)
    return 0


def cmd_expand_antonyms_cilin(args: argparse.Namespace) -> int:
    ensure_word_relations_table()
    source_id = (args.source or "ant_cilin_exanded")[:32]
    with SessionLocal() as db:
        if args.replace_relations:
            removed = clear_word_relations_source(db, source_id)
            print(f"Cleared {removed} existing word_relations with source={source_id!r}")
        stats = expand_antonyms_via_cilin_synonyms(
            db,
            source=source_id,
            cilin_syn_source=args.cilin_syn_source,
            confidence=args.confidence,
            dedupe_existing=args.dedupe_existing,
            batch_size=args.batch_size,
        )
        print("expand-antonyms-cilin stats:", stats)
    return 0


def cmd_expand_antonyms_syn_bridge(args: argparse.Namespace) -> int:
    try:
        with ingest_lock("expand-antonyms-syn-bridge"):
            return _run_expand_antonyms_syn_bridge(args)
    except IngestLockError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def _run_expand_antonyms_syn_bridge(args: argparse.Namespace) -> int:
    from ingest.bridge_pool_context import (
        clear_bridge_checkpoint,
        read_bridge_checkpoint,
        write_bridge_checkpoint,
    )

    ensure_word_relations_table()
    source_id = (args.source or "ant_syn_bridge")[:32]
    offset = max(0, int(args.offset or 0))
    inserted_cumulative = 0

    if args.fresh:
        clear_bridge_checkpoint()
        print("Cleared checkpoint (--fresh)", flush=True)
    elif offset == 0 and not getattr(args, "no_auto_resume", False):
        cp = read_bridge_checkpoint()
        if cp and cp.get("offset", 0) > 0:
            offset = int(cp["offset"])
            inserted_cumulative = int(cp.get("inserted_cumulative") or 0)
            total = cp.get("total_targets", "?")
            print(
                f"Resuming from checkpoint offset={offset} "
                f"(inserted_cumulative={inserted_cumulative}, total_targets={total})",
                flush=True,
            )

    def on_progress(processed: int, chunk_stats: dict) -> None:
        print(
            f"progress offset={offset + processed} "
            f"bridged={chunk_stats.get('bridged', 0)} "
            f"skipped_no_bridge={chunk_stats.get('skipped_no_bridge', 0)}",
            flush=True,
        )

    def on_batch(
        batch_num: int,
        total_batches: int,
        chunk_stats: dict,
        next_offset: int,
    ) -> None:
        nonlocal inserted_cumulative
        batch_inserted = int(chunk_stats.get("inserted") or 0)
        inserted_cumulative += batch_inserted
        write_bridge_checkpoint(
            offset=next_offset,
            inserted_cumulative=inserted_cumulative,
            total_targets=chunk_stats.get("total_targets") or 0,
        )
        print(
            f"batch {batch_num}/{total_batches} "
            f"offset→{next_offset} "
            f"bridged={chunk_stats.get('bridged', 0)} "
            f"inserted={batch_inserted} "
            f"cumulative={inserted_cumulative}",
            flush=True,
        )

    with SessionLocal() as db:
        if args.fresh and args.replace_relations:
            removed = clear_word_relations_source(db, source_id)
            print(f"Cleared {removed} existing word_relations with source={source_id!r} (--fresh)")
        elif args.replace_relations and offset == 0:
            removed = clear_word_relations_source(db, source_id)
            print(f"Cleared {removed} existing word_relations with source={source_id!r}")
        elif offset > 0:
            print("Skipping clear: resuming from checkpoint", flush=True)

        stats = expand_antonyms_via_embedding_syn_bridge(
            db,
            source=source_id,
            dedupe_existing=args.dedupe_existing,
            include_static=not args.no_static,
            batch_size=args.batch_size,
            embed_batch_size=args.embed_batch_size,
            offset=offset,
            limit=args.limit,
            chunk_size=args.chunk_size,
            on_batch=on_batch if args.chunk_size else None,
            on_progress=on_progress if args.progress_interval else None,
            progress_interval=max(0, int(args.progress_interval or 0)),
        )
        if not args.chunk_size:
            inserted_cumulative += int(stats.get("inserted") or 0)
        final_offset = offset + int(stats.get("targets") or 0)
        total_targets = int(stats.get("total_targets") or 0)
        if total_targets > 0:
            write_bridge_checkpoint(
                offset=final_offset,
                inserted_cumulative=inserted_cumulative,
                total_targets=total_targets,
            )
        print("expand-antonyms-syn-bridge stats:", stats)
    return 0


def cmd_expand_antonyms_mirror(args: argparse.Namespace) -> int:
    ensure_word_relations_table()
    source_id = (args.source or "ant_syn_mirror")[:32]
    with SessionLocal() as db:
        if args.replace_relations:
            removed = clear_word_relations_source(db, source_id)
            print(f"Cleared {removed} existing word_relations with source={source_id!r}")
        stats = expand_antonyms_via_syn_endpoints(
            db,
            source=source_id,
            confidence=args.confidence,
            dedupe_existing=args.dedupe_existing,
            include_static=not args.no_static,
            batch_size=args.batch_size,
        )
        print("expand-antonyms-mirror stats:", stats)
    return 0


def cmd_ingest_compound_ant(args: argparse.Namespace) -> int:
    ensure_word_relations_table()
    path = Path(args.list_path) if args.list_path else None
    compounds = load_compound_antonyms(path)
    print(f"Loaded {len(compounds)} unique compound antonyms from {path or 'default list'}")
    source_id = (args.source or "compound_ant")[:32]
    with SessionLocal() as db:
        stats = ingest_compound_ant_char_pairs(
            db,
            compounds,
            source=source_id,
            confidence=args.confidence,
            dedupe_existing=args.dedupe_existing,
            replace_source=args.replace_relations,
        )
        matched = stats.get("matched_chars") or []
        print("ingest-compound-ant stats:", {k: v for k, v in stats.items() if k != "matched_chars"})
        if matched:
            preview = ", ".join(matched[:20])
            suffix = f" ... (+{len(matched) - 20})" if len(matched) > 20 else ""
            print(f"matched_in_db sample: {preview}{suffix}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Syn/Ant ingest v2")
    parser.add_argument("--manifest", default=None, help="Path to sources.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("report", help="Show manifest + DB stats")

    p_norm = sub.add_parser("normalize", help="Parse sources into syn_ant_edges staging")
    p_norm.add_argument("--source", action="append", help="Source id (repeatable)")
    p_norm.add_argument("--allow-external", action="store_true", help="Keep edges where tail/head not in words DB")
    p_norm.add_argument("--append", action="store_true", help="Append staging instead of replace")

    p_build = sub.add_parser("build-relations", help="Merge staging into word_relations")
    p_build.add_argument("--allow-external", action="store_true", help="Include external-only char pairs")
    p_build.add_argument("--batch-size", type=int, default=300, help="Staging rows per SQL batch (default 300)")
    p_build.add_argument("--source", help="Only merge staging rows from this source id")
    p_build.add_argument("--batched", action="store_true", help="Force batched SQL merge")

    p_cilin = sub.add_parser("ingest-cilin", help="Ingest Cilin leaf synonym groups")
    p_cilin.add_argument("--chunk-size", type=int, default=300, help="Leaf groups per chunk (default 300)")
    p_cilin.add_argument("--source-path", help="Override Cilin file path (e.g. Desktop/new_cilin.txt)")
    p_cilin.add_argument("--staging", action="store_true", help="Use syn_ant_edges staging path instead of direct")
    p_cilin.add_argument("--dedupe-existing", action="store_true", default=True, help="Skip existing canonical syn pairs")
    p_cilin.add_argument("--no-dedupe-existing", dest="dedupe_existing", action="store_false")
    p_cilin.add_argument("--allow-external", action="store_true", help="Keep edges where char not in words DB")
    p_cilin.add_argument(
        "--no-replace-relations",
        dest="replace_relations",
        action="store_false",
        help="Keep existing word_relations with source=cilin (default: clear cilin rows first)",
    )
    p_cilin.set_defaults(replace_relations=True)

    p_expand = sub.add_parser("expand-antonyms-cilin", help="Expand antonyms via Cilin synonym neighbors")
    p_expand.add_argument("--source", default="ant_cilin_exanded", help="Source tag for derived ant relations")
    p_expand.add_argument("--cilin-syn-source", default="cilin", help="Cilin synonym source to expand from")
    p_expand.add_argument("--confidence", type=float, default=0.75, help="Score for derived ant relations")
    p_expand.add_argument("--batch-size", type=int, default=300, help="Insert batch size")
    p_expand.add_argument("--dedupe-existing", action="store_true", default=True, help="Skip existing ant keys")
    p_expand.add_argument("--no-dedupe-existing", dest="dedupe_existing", action="store_false")
    p_expand.add_argument(
        "--no-replace-relations",
        dest="replace_relations",
        action="store_false",
        help="Keep existing derived ant rows (default: clear source first)",
    )
    p_expand.set_defaults(replace_relations=True)

    p_mirror = sub.add_parser(
        "expand-antonyms-mirror",
        help="Persist !query ant expansion (~endpoint syns) into word_relations",
    )
    p_mirror.add_argument("--source", default="ant_syn_mirror", help="Source tag for mirror ant relations")
    p_mirror.add_argument("--confidence", type=float, default=0.72, help="Score for mirror ant relations")
    p_mirror.add_argument("--batch-size", type=int, default=300, help="Insert batch size")
    p_mirror.add_argument("--dedupe-existing", action="store_true", default=True, help="Skip existing ant keys")
    p_mirror.add_argument("--no-dedupe-existing", dest="dedupe_existing", action="store_false")
    p_mirror.add_argument("--no-static", dest="no_static", action="store_true", help="Only use DB syn, not static thesaurus")
    p_mirror.add_argument(
        "--no-replace-relations",
        dest="replace_relations",
        action="store_false",
        help="Keep existing mirror ant rows (default: clear source first)",
    )
    p_mirror.set_defaults(replace_relations=True)

    p_bridge = sub.add_parser(
        "expand-antonyms-syn-bridge",
        help="Expand antonyms via embedding-selected synonym bridge",
    )
    p_bridge.add_argument("--source", default="ant_syn_bridge", help="Source tag for bridged ant relations")
    p_bridge.add_argument("--batch-size", type=int, default=300, help="Insert batch size")
    p_bridge.add_argument("--embed-batch-size", type=int, default=256, help="Embedding encode batch size")
    p_bridge.add_argument("--offset", type=int, default=0, help="Skip first N target chars (resume)")
    p_bridge.add_argument("--limit", type=int, default=None, help="Max target chars from offset (debug/smoke)")
    p_bridge.add_argument(
        "--chunk-size",
        type=int,
        default=200,
        help="Process N targets per batch with incremental insert (default 200; 0 = single pass)",
    )
    p_bridge.add_argument(
        "--progress-interval",
        type=int,
        default=50,
        help="Print progress every N targets within a chunk (default 50; 0 = off)",
    )
    p_bridge.add_argument(
        "--fresh",
        action="store_true",
        help="Clear checkpoint and restart from offset 0",
    )
    p_bridge.add_argument(
        "--no-auto-resume",
        action="store_true",
        help="Do not resume from checkpoint when --offset is 0",
    )
    p_bridge.add_argument("--dedupe-existing", action="store_true", default=True, help="Skip existing ant keys")
    p_bridge.add_argument("--no-dedupe-existing", dest="dedupe_existing", action="store_false")
    p_bridge.add_argument("--no-static", dest="no_static", action="store_true", help="Only use DB syn, not static thesaurus")
    p_bridge.add_argument(
        "--no-replace-relations",
        dest="replace_relations",
        action="store_false",
        help="Keep existing bridged ant rows (default: clear source first)",
    )
    p_bridge.set_defaults(replace_relations=True)

    p_compound = sub.add_parser(
        "ingest-compound-ant",
        help="Seed single-char ant pairs from 0243 compound antonym list",
    )
    p_compound.add_argument(
        "--list-path",
        help="Override compound antonyms list (default: data/syn_ant/compound_antonyms.txt)",
    )
    p_compound.add_argument("--source", default="compound_ant", help="Source tag for inserted ant relations")
    p_compound.add_argument("--confidence", type=float, default=0.9, help="Score for compound ant relations")
    p_compound.add_argument("--dedupe-existing", action="store_true", default=True, help="Skip existing ant keys")
    p_compound.add_argument("--no-dedupe-existing", dest="dedupe_existing", action="store_false")
    p_compound.add_argument(
        "--no-replace-relations",
        dest="replace_relations",
        action="store_false",
        help="Keep existing compound_ant rows (default: clear source first)",
    )
    p_compound.set_defaults(replace_relations=True)

    args = parser.parse_args(argv)
    if args.command == "report":
        return cmd_report(args)
    if args.command == "normalize":
        return cmd_normalize(args)
    if args.command == "build-relations":
        return cmd_build_relations(args)
    if args.command == "ingest-cilin":
        return cmd_ingest_cilin(args)
    if args.command == "expand-antonyms-cilin":
        return cmd_expand_antonyms_cilin(args)
    if args.command == "expand-antonyms-mirror":
        return cmd_expand_antonyms_mirror(args)
    if args.command == "expand-antonyms-syn-bridge":
        return cmd_expand_antonyms_syn_bridge(args)
    if args.command == "ingest-compound-ant":
        return cmd_ingest_compound_ant(args)
    return 1


__all__ = ["main"]
