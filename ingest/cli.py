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
from ingest.lexicon_corrections import (
    DEFAULT_BATCH_N,
    DEFAULT_TSV,
    apply_pending,
    check_status,
    load_corrections,
    post_apply_exports,
    save_corrections,
)
from ingest.compound_antonyms import ingest_compound_ant_char_pairs, load_compound_antonyms


def cmd_report(_: argparse.Namespace) -> int:
    print(manifest_report())
    print()
    ensure_syn_ant_edges_table()
    ensure_word_relations_table()
    with SessionLocal() as db:
        print(staging_report(db))
        rel_count = db.query(WordRelation).count()
        syn_count = db.query(WordRelation).filter(WordRelation.relation_type == "syn").count()
        bridge_ant = (
            db.query(WordRelation)
            .filter(
                WordRelation.source == "ant_syn_bridge",
                WordRelation.relation_type == "ant",
            )
            .count()
        )
        print(f"\nword_relations rows: {rel_count} (syn: {syn_count})")
        print(f"ant_syn_bridge ant rows: {bridge_ant}")
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
            min_bridge_cosine=args.min_bridge_cosine,
            max_bridged_ants_per_head=args.max_bridged_ants_per_head,
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


def cmd_bake_syn_bridge(args: argparse.Namespace) -> int:
    from ingest.bridge_snapshot import DEFAULT_SNAPSHOT, write_bridge_snapshot

    if not args.export_only:
        expand_args = argparse.Namespace(
            source=args.source,
            batch_size=args.batch_size,
            embed_batch_size=args.embed_batch_size,
            offset=0,
            limit=args.limit,
            chunk_size=args.chunk_size,
            progress_interval=args.progress_interval,
            min_bridge_cosine=args.min_bridge_cosine,
            max_bridged_ants_per_head=args.max_bridged_ants_per_head,
            fresh=True,
            no_auto_resume=True,
            dedupe_existing=args.dedupe_existing,
            no_static=args.no_static,
            replace_relations=True,
        )
        rc = cmd_expand_antonyms_syn_bridge(expand_args)
        if rc:
            return rc

    out = Path(args.output or DEFAULT_SNAPSHOT)
    ensure_word_relations_table()
    with SessionLocal() as db:
        n = write_bridge_snapshot(db, out, source=(args.source or "ant_syn_bridge")[:32])
    print(f"bake-syn-bridge: wrote {n} pair(s) -> {out}")
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


def cmd_build_db(args: argparse.Namespace) -> int:
    from app.database import Base, engine
    from ingest.lexicon_build import DEFAULT_LEXICON_MANIFEST, build_lexicon_words
    from ingest.lexicon_truncate import truncate_lexicon_core
    from ingest.bridge_snapshot import ingest_bridge_snapshot
    from ingest.manual_relations_apply import apply_manual_relations

    manifest = args.lexicon_manifest or str(DEFAULT_LEXICON_MANIFEST)
    print(f"==> build-db manifest: {manifest}")

    Base.metadata.create_all(bind=engine)
    ensure_syn_ant_edges_table()
    ensure_word_relations_table()

    with SessionLocal() as db:
        print("==> truncate words / relations / staging")
        truncate_lexicon_core(db)
        print("==> lexicon SSOT ingest + overlay")
        n_words = build_lexicon_words(db, manifest_path=manifest)
        db.commit()
        print(f"    persisted {n_words} word(s)")

    if args.skip_relations:
        print("skip-relations: done")
        return _build_db_exports(args)

    steps = [
        ("normalize", lambda: cmd_normalize(
            argparse.Namespace(manifest=None, source=None, allow_external=False, append=False)
        )),
        ("build-relations", lambda: cmd_build_relations(
            argparse.Namespace(allow_external=False, source=None, batch_size=300, batched=False)
        )),
        ("ingest-cilin", lambda: cmd_ingest_cilin(
            argparse.Namespace(
                manifest=None,
                source_path=None,
                staging=False,
                chunk_size=300,
                dedupe_existing=True,
                allow_external=False,
                replace_relations=True,
            )
        )),
        ("expand-antonyms-cilin", lambda: cmd_expand_antonyms_cilin(
            argparse.Namespace(
                source=None,
                cilin_syn_source="cilin",
                confidence=0.75,
                dedupe_existing=True,
                batch_size=300,
                replace_relations=True,
            )
        )),
        ("expand-antonyms-mirror", lambda: cmd_expand_antonyms_mirror(
            argparse.Namespace(
                source=None,
                no_static=False,
                confidence=0.72,
                dedupe_existing=True,
                batch_size=300,
                replace_relations=True,
            )
        )),
        ("ingest-compound-ant", lambda: cmd_ingest_compound_ant(
            argparse.Namespace(
                list_path=None,
                source=None,
                confidence=0.9,
                dedupe_existing=True,
                replace_relations=True,
            )
        )),
    ]
    for label, fn in steps:
        print(f"==> {label}")
        rc = fn()
        if rc != 0:
            print(f"{label} failed with exit {rc}", file=sys.stderr)
            return rc

    with SessionLocal() as db:
        print("==> bridge snapshot")
        bstats = ingest_bridge_snapshot(db)
        db.commit()
        print(f"    bridge: {bstats}")
        print("==> manual relations")
        mcount = apply_manual_relations(db)
        db.commit()
        print(f"    manual rows: {mcount}")

    return _build_db_exports(args)


def _build_db_exports(args: argparse.Namespace) -> int:
    if args.no_exports:
        return 0
    print("==> export words-lexicon.json + README word count")
    try:
        post_apply_exports()
    except Exception as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 1
    if args.copy_public:
        import shutil
        src = REPO_ROOT / "lyrics.db"
        dest = REPO_ROOT / "client" / "public" / "lyrics.db"
        if src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"    copied -> {dest}")
    return 0


def cmd_apply_lexicon_corrections(args: argparse.Namespace) -> int:
    path = Path(args.file)
    rows = load_corrections(path)
    if args.check or not args.apply:
        return check_status(rows, batch_n=args.batch_n)

    if not rows:
        print("No corrections.")
        return 0

    with SessionLocal() as db:
        try:
            apply_pending(db, rows, dry_run=False)
            db.commit()
        except Exception as exc:
            db.rollback()
            print(f"apply failed (rolled back): {exc}", file=sys.stderr)
            return 1

    if not args.no_exports:
        print("==> Export words-lexicon.json + README word count...")
        post_apply_exports()

    print("Done. Prefer: python -m ingest build-db for full lexicon rebuild.")
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
        description="近義橋反義 ingest。全量重跑與驗收見 docs/ingest-bridge-ant.md",
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
        "--min-bridge-cosine",
        type=float,
        default=0.80,
        help="Min head–bridge synonym cosine to borrow ants (default 0.80)",
    )
    p_bridge.add_argument(
        "--max-bridged-ants-per-head",
        type=int,
        default=30,
        help="Max ant relations per head after multi-bridge merge (default 30)",
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
        help="Clear checkpoint and restart from offset 0 (see docs/ingest-bridge-ant.md)",
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

    p_bake = sub.add_parser(
        "bake-syn-bridge",
        help="Bake ant_syn_bridge snapshot TSV (embedding run + export)",
        description="Maintainer: expand-antonyms-syn-bridge --fresh, then export git-tracked TSV. See docs/ingest-bridge-ant.md",
    )
    p_bake.add_argument(
        "--output",
        default="data/syn_ant/ant_syn_bridge_pairs.tsv",
        help="Snapshot TSV path (default: data/syn_ant/ant_syn_bridge_pairs.tsv)",
    )
    p_bake.add_argument(
        "--export-only",
        action="store_true",
        help="Skip embedding; export current ant_syn_bridge rows from lyrics.db",
    )
    p_bake.add_argument("--source", default="ant_syn_bridge", help="Source tag for bridged ant relations")
    p_bake.add_argument("--batch-size", type=int, default=300, help="Insert batch size")
    p_bake.add_argument("--embed-batch-size", type=int, default=256, help="Embedding encode batch size")
    p_bake.add_argument("--limit", type=int, default=None, help="Max target chars (debug/smoke)")
    p_bake.add_argument("--chunk-size", type=int, default=0, help="Chunked insert with checkpoint (0 = single pass)")
    p_bake.add_argument("--progress-interval", type=int, default=50, help="Progress print interval")
    p_bake.add_argument("--min-bridge-cosine", type=float, default=0.80, help="Min head–bridge synonym cosine")
    p_bake.add_argument("--max-bridged-ants-per-head", type=int, default=30, help="Max ant relations per head")
    p_bake.add_argument("--dedupe-existing", action="store_true", default=True, help="Skip existing ant keys")
    p_bake.add_argument("--no-dedupe-existing", dest="dedupe_existing", action="store_false")
    p_bake.add_argument("--no-static", dest="no_static", action="store_true", help="Only use DB syn, not static thesaurus")

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

    p_lxc = sub.add_parser(
        "apply-lexicon-corrections",
        help="Apply pending 詞庫勘誤 rows (see docs/lexicon-corrections.md)",
    )
    p_lxc.add_argument("--file", default=str(DEFAULT_TSV), help="Corrections TSV path")
    p_lxc.add_argument("--check", action="store_true", help="Show pending/applied counts only")
    p_lxc.add_argument("--apply", action="store_true", help="Apply pending rows to lyrics.db")
    p_lxc.add_argument(
        "--batch-n",
        type=int,
        default=DEFAULT_BATCH_N,
        help=f"Pending count hint threshold (default {DEFAULT_BATCH_N})",
    )
    p_lxc.add_argument(
        "--no-exports",
        action="store_true",
        help="Skip words-lexicon export and README word-count sync",
    )

    p_build_db = sub.add_parser("build-db", help="Wipe and rebuild lyrics.db from SSOT manifest")
    p_build_db.add_argument(
        "--lexicon-manifest",
        default=None,
        help="Path to data/lexicon/sources.yaml (default: repo manifest)",
    )
    p_build_db.add_argument("--skip-relations", action="store_true", help="Only rebuild words tables")
    p_build_db.add_argument("--no-exports", action="store_true", help="Skip export + README sync")
    p_build_db.add_argument(
        "--copy-public",
        action="store_true",
        help="Copy lyrics.db to client/public/ after build",
    )

    p_migrate = sub.add_parser(
        "migrate-legacy-snapshots",
        help="Export bridge + manual relations from legacy lyrics.db into TSV sidecars",
    )
    p_migrate.add_argument("--db", default="lyrics.db", help="Legacy lyrics.db path")
    p_migrate.add_argument(
        "--bridge-out",
        default="data/syn_ant/ant_syn_bridge_pairs.tsv",
        help="Bridge snapshot TSV output",
    )
    p_migrate.add_argument(
        "--manual-out",
        default="data/relations/manual_relations.tsv",
        help="Manual relations TSV output",
    )

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
    if args.command == "bake-syn-bridge":
        return cmd_bake_syn_bridge(args)
    if args.command == "ingest-compound-ant":
        return cmd_ingest_compound_ant(args)
    if args.command == "apply-lexicon-corrections":
        return cmd_apply_lexicon_corrections(args)
    if args.command == "build-db":
        return cmd_build_db(args)
    if args.command == "migrate-legacy-snapshots":
        return cmd_migrate_legacy_snapshots(args)
    return 1


def cmd_migrate_legacy_snapshots(args: argparse.Namespace) -> int:
    from ingest.migrate_legacy import export_bridge_snapshot, export_manual_relations

    db = Path(args.db)
    if not db.is_file():
        print(f"db not found: {db}", file=sys.stderr)
        return 1
    bridge_out = Path(args.bridge_out)
    manual_out = Path(args.manual_out)
    nb = export_bridge_snapshot(db, bridge_out)
    nm = export_manual_relations(db, manual_out)
    print(f"exported bridge pairs: {nb} -> {bridge_out}")
    print(f"exported manual relations: {nm} -> {manual_out}")
    return 0


__all__ = ["main"]
