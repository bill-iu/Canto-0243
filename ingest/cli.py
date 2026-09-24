"""Syn/Ant ingest v2 CLI (`python -m ingest <command>`)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.database import SessionLocal, ensure_word_relations_table
from app.models.word import WordRelation
from ingest.ingest_lock import IngestLockError, ingest_lock
from ingest.syn_ant_manifest import load_manifest, manifest_report, resolve_source_path, select_sources
from ingest.syn_ant_build import clear_word_relations_source
from ingest.syn_ant_direct import ingest_static_relations
from ingest.word_relations_build import build_word_relations
from ingest.syn_ant_expand import (
    expand_antonyms_via_cilin_synonyms,
    expand_antonyms_via_embedding_syn_bridge,
    expand_antonyms_via_syn_endpoints,
)
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
from ingest.derived_ant_snapshot import (
    DEFAULT_CILIN_SNAPSHOT,
    DEFAULT_MIRROR_SNAPSHOT,
    bake_derived_ant_snapshots,
    ingest_cilin_derived_ant_snapshot,
    ingest_mirror_derived_ant_snapshot,
)


def cmd_report(_: argparse.Namespace) -> int:
    print(manifest_report())
    print()
    ensure_word_relations_table()
    with SessionLocal() as db:
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


def cmd_build_word_relations(args: argparse.Namespace) -> int:
    ensure_word_relations_table()
    with SessionLocal() as db:
        stats = build_word_relations(
            db,
            manifest_path=args.manifest,
            compound_path=args.compound_path,
            replace_static=not args.append,
        )
        print("build-word-relations stats:", stats)
    return 0


def cmd_ingest_static_relations(args: argparse.Namespace) -> int:
    ensure_word_relations_table()
    with SessionLocal() as db:
        stats = ingest_static_relations(
            db,
            manifest_path=args.manifest,
            chunk_size=args.chunk_size,
        )
        print("ingest-static-relations stats:", stats)
    return 0


def _resolve_cilin_path(args: argparse.Namespace, src: dict) -> Path | None:
    if args.source_path:
        p = Path(args.source_path)
        return p if p.exists() else None
    p = resolve_source_path(src)
    return p if p and p.exists() else None


def cmd_ingest_cilin(args: argparse.Namespace) -> int:
    """Legacy alias → 關係直寫 (`build_word_relations`); not a second write path."""
    # Validate cilin still present in manifest / on disk (compat with old flags).
    manifest = load_manifest(args.manifest)
    sources = select_sources(manifest, source_ids=["cilin"])
    if not sources:
        print("Cilin source not found in manifest.")
        return 1
    path = _resolve_cilin_path(args, sources[0])
    if path is None:
        print(f"Cilin file missing: {args.source_path or resolve_source_path(sources[0])}")
        return 1

    _ = (args.chunk_size, args.dedupe_existing)  # ponytail: legacy flags ignored after delegate
    print(
        "ingest-cilin: delegating to build-word-relations "
        f"(cilin={path}; full static 關係直寫, not leaf_direct)"
    )
    return cmd_build_word_relations(
        argparse.Namespace(
            manifest=args.manifest,
            compound_path=None,
            append=not args.replace_relations,
        )
    )


def cmd_expand_antonyms_cilin(args: argparse.Namespace) -> int:
    from ingest.derived_ant_snapshot import DEFAULT_CILIN_SNAPSHOT

    ensure_word_relations_table()
    source_id = (args.source or "ant_cilin_exanded")[:32]
    output = args.output or str(DEFAULT_CILIN_SNAPSHOT)
    with SessionLocal() as db:
        if args.insert and args.replace_relations:
            removed = clear_word_relations_source(db, source_id)
            print(f"Cleared {removed} existing word_relations with source={source_id!r}")
        stats = expand_antonyms_via_cilin_synonyms(
            db,
            source=source_id,
            cilin_syn_source=args.cilin_syn_source,
            confidence=args.confidence,
            dedupe_existing=args.dedupe_existing,
            batch_size=args.batch_size,
            insert=bool(args.insert),
            export_path=output,
            include_static=not args.no_static,
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
    from ingest.derived_ant_snapshot import DEFAULT_MIRROR_SNAPSHOT

    ensure_word_relations_table()
    source_id = (args.source or "ant_syn_mirror")[:32]
    output = args.output or str(DEFAULT_MIRROR_SNAPSHOT)
    with SessionLocal() as db:
        if args.insert and args.replace_relations:
            removed = clear_word_relations_source(db, source_id)
            print(f"Cleared {removed} existing word_relations with source={source_id!r}")
        stats = expand_antonyms_via_syn_endpoints(
            db,
            source=source_id,
            confidence=args.confidence,
            dedupe_existing=args.dedupe_existing,
            include_static=not args.no_static,
            batch_size=args.batch_size,
            insert=bool(args.insert),
            export_path=output,
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


def cmd_ingest_derived_ant_snapshots(args: argparse.Namespace) -> int:
    ensure_word_relations_table()
    cilin_path = Path(args.cilin_path) if args.cilin_path else DEFAULT_CILIN_SNAPSHOT
    mirror_path = Path(args.mirror_path) if args.mirror_path else DEFAULT_MIRROR_SNAPSHOT
    with SessionLocal() as db:
        cilin_stats = ingest_cilin_derived_ant_snapshot(db, cilin_path)
        mirror_stats = ingest_mirror_derived_ant_snapshot(db, mirror_path)
        print("ingest-derived-ant-snapshots:", {"cilin": cilin_stats, "mirror": mirror_stats})
    return 0


def cmd_bake_derived_ant_snapshots(args: argparse.Namespace) -> int:
    ensure_word_relations_table()
    cilin_out = Path(args.cilin_out or DEFAULT_CILIN_SNAPSHOT)
    mirror_out = Path(args.mirror_out or DEFAULT_MIRROR_SNAPSHOT)
    with SessionLocal() as db:
        stats = bake_derived_ant_snapshots(
            db,
            cilin_path=cilin_out,
            mirror_path=mirror_out,
            export_only=args.export_only,
            cilin_syn_source=args.cilin_syn_source,
            cilin_confidence=args.cilin_confidence,
            mirror_confidence=args.mirror_confidence,
            include_static=not args.no_static,
            batch_size=args.batch_size,
        )
    print(f"bake-derived-ant-snapshots: {stats}")
    return 0


BUILD_DB_PATH_HINT = """
建議路徑（CONTEXT § 詞條庫建置流程；唔係對現行庫打增量 patch）:
  全量從源重建:              python -m ingest build-db
  只改詞源／overlay:         python -m ingest build-db --stage words
  詞已齊、只重關係:          python -m ingest build-db --stage relations
  只 seal／閘／copy-db:      python -m ingest build-db --stage seal
  只改關係補錄清單:          python -m ingest apply-manual-relations
""".strip()


def resolve_build_db_stage(args: argparse.Namespace) -> str:
    """Return all|words|relations|seal. --skip-relations aliases --stage words."""
    stage = getattr(args, "stage", None) or "all"
    if getattr(args, "skip_relations", False):
        if stage not in ("all", "words"):
            raise ValueError(
                f"--skip-relations conflicts with --stage {stage}; "
                "use --stage words or omit --stage"
            )
        return "words"
    if stage not in ("all", "words", "relations", "seal"):
        raise ValueError(f"unknown --stage {stage!r}")
    return stage


def cmd_build_db(args: argparse.Namespace) -> int:
    try:
        with ingest_lock("build-db"):
            return _cmd_build_db_impl(args)
    except IngestLockError as exc:
        print(exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2


def _build_db_words(args: argparse.Namespace, *, manifest: str) -> int:
    from app.database import Base, engine
    from ingest.lexicon_build import build_lexicon_words
    from ingest.lexicon_stats import check_min_multi_char, lexicon_word_stats
    from ingest.lexicon_truncate import truncate_lexicon_core
    from ingest.manual_relations_apply import merge_orphan_manual_directs_into_tsv

    Base.metadata.create_all(bind=engine)
    ensure_word_relations_table()

    with SessionLocal() as db:
        # Wipe 前先把未入清單嘅 manual 直連合併入 TSV（cluster/mirror 唔寫入）。
        print("==> merge orphan manual directs → 關係補錄清單")
        ostats = merge_orphan_manual_directs_into_tsv(db)
        print(f"    orphan-merge: {ostats}")

        print("==> truncate words / relations")
        truncate_lexicon_core(db)
        print("==> lexicon SSOT ingest + overlay")
        n_words = build_lexicon_words(
            db,
            manifest_path=manifest,
            use_layer_cache=not getattr(args, "no_layer_cache", False),
        )
        db.commit()
        stats = lexicon_word_stats(db)
        print(f"    persisted {n_words} word(s)")
        print(
            f"    lexicon stats: total={stats['total']} multi_char={stats['multi_char']}"
        )
        if args.min_multi_char is not None:
            try:
                check_min_multi_char(db, args.min_multi_char)
            except ValueError as exc:
                print(f"build-db failed: {exc}", file=sys.stderr)
                return 1
    return 0


def _build_db_relations() -> int:
    from ingest.bridge_snapshot import ingest_bridge_snapshot
    from ingest.manual_relations_apply import hot_apply_manual_relations

    print("==> build-word-relations")
    rc = cmd_build_word_relations(
        argparse.Namespace(manifest=None, compound_path=None, append=False)
    )
    if rc != 0:
        print(f"build-word-relations failed with exit {rc}", file=sys.stderr)
        return rc

    with SessionLocal() as db:
        print("==> bridge snapshot")
        bstats = ingest_bridge_snapshot(db)
        db.commit()
        print(f"    bridge: {bstats}")
        print("==> manual relations (熱套用)")
        mstats = hot_apply_manual_relations(db)
        print(f"    manual: {mstats}")
    return 0


def _cmd_build_db_impl(args: argparse.Namespace) -> int:
    from ingest.lexicon_build import DEFAULT_LEXICON_MANIFEST

    stage = resolve_build_db_stage(args)
    print(BUILD_DB_PATH_HINT)
    print(f"==> build-db stage={stage}")

    if stage == "seal":
        return _build_db_exports(args)

    if stage == "relations":
        from app.database import Base, engine

        Base.metadata.create_all(bind=engine)
        ensure_word_relations_table()
        rc = _build_db_relations()
        if rc != 0:
            return rc
        return _build_db_exports(args)

    # words | all — words stage still full wipe+ingest (唔係 patch)
    manifest = args.lexicon_manifest or str(DEFAULT_LEXICON_MANIFEST)
    print(f"==> build-db manifest: {manifest}")
    rc = _build_db_words(args, manifest=manifest)
    if rc != 0:
        return rc

    if stage == "words":
        print("stage=words: skip relations")
        return _build_db_exports(args)

    rc = _build_db_relations()
    if rc != 0:
        return rc
    return _build_db_exports(args)


def _seal_lexicon_vacuum(db_path: Path) -> None:
    """ADR-0027: one page_size + VACUUM after meta/index work (C1 — no second VACUUM)."""
    import os
    import sqlite3

    from app.database import engine as _engine

    _engine.dispose()
    size_before = os.path.getsize(db_path)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("PRAGMA page_size = 16384")
        conn.execute("VACUUM")
    size_after = os.path.getsize(db_path)
    print(
        f"    {size_before / 1024 / 1024:.1f} MB -> {size_after / 1024 / 1024:.1f} MB"
        f" (saved {(size_before - size_after) / 1024 / 1024:.1f} MB)"
    )


def _build_db_exports(args: argparse.Namespace) -> int:
    if args.no_exports:
        return 0
    print("==> export words-lexicon.json + README word count")
    try:
        post_apply_exports()
    except Exception as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 1
    print("==> phoneme vocab meta (J2 / ADR-0037)")
    try:
        from ingest.lexicon_meta import write_phoneme_vocab_meta

        write_phoneme_vocab_meta(REPO_ROOT / "lyrics.db")
        print("    lexicon_meta phoneme fingerprint written")
    except Exception as exc:
        print(f"phoneme meta failed (non-fatal): {exc}", file=sys.stderr)
    print("==> finalize lexicon indexes (I2 allowlist)")
    try:
        import os
        import sqlite3

        from ingest.lexicon_indexes import finalize_lexicon_indexes

        db_path = REPO_ROOT / "lyrics.db"
        dropped = finalize_lexicon_indexes(db_path)
        if dropped:
            print(f"    dropped: {', '.join(dropped)}")
        else:
            print("    no forbidden indexes")

        size_mb = os.path.getsize(db_path) / 1024 / 1024
        idx_mb: float | None
        with sqlite3.connect(db_path) as conn:
            try:
                idx_mb = (
                    conn.execute(
                        "SELECT SUM(pgsize) FROM dbstat WHERE name IN "
                        "(SELECT name FROM sqlite_master WHERE type='index' "
                        "AND name NOT LIKE 'sqlite_%')"
                    ).fetchone()[0]
                    or 0
                ) / 1024 / 1024
            except Exception:
                idx_mb = None
        if idx_mb is None:
            print(f"    post-finalize: db={size_mb:.1f} MB indexes=n/a (no dbstat)")
        else:
            print(f"    post-finalize: db={size_mb:.1f} MB indexes={idx_mb:.1f} MB")
    except Exception as exc:
        print(f"index finalize failed (non-fatal): {exc}", file=sys.stderr)
    # Single seal VACUUM after exports/meta/index drops (was two VACUUMs).
    print("==> VACUUM (page_size=16384, defragment)")
    try:
        _seal_lexicon_vacuum(REPO_ROOT / "lyrics.db")
    except Exception as exc:
        print(f"VACUUM failed (non-fatal): {exc}", file=sys.stderr)
    print("==> lexicon release gate (I2)")
    try:
        from ingest.lexicon_release_gate import check_lexicon_release_gate

        gate = check_lexicon_release_gate(REPO_ROOT / "lyrics.db")
        for line in gate.messages:
            print(f"    {line}")
        if not gate.ok:
            print("lexicon release gate FAILED", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"release gate failed: {exc}", file=sys.stderr)
        return 1
    # E1c: embedding-nbr.bin char→id fingerprint (reuse safety)
    print("==> embedding-nbr fingerprint (E1c reuse gate)")
    try:
        from app.domain.lexicon.embedding_nbr_codec import verify_embedding_nbr_fingerprint

        public_meta = REPO_ROOT / "client" / "public" / "embedding-nbr.meta.json"
        nbr_check = verify_embedding_nbr_fingerprint(
            db_path=REPO_ROOT / "lyrics.db",
            meta_path=public_meta,
            require_present=False,
        )
        print(f"    status={nbr_check.get('status')} ok={nbr_check.get('ok')}")
        if nbr_check.get("hint"):
            print(f"    {nbr_check['hint']}")
        # Fail seal only when bin is shipped but fingerprint missing/mismatch
        if nbr_check.get("status") in ("mismatch", "missing_fp", "missing_bin") and (
            public_meta.is_file()
            or (REPO_ROOT / "client" / "public" / "embedding-nbr.bin").is_file()
        ):
            print("embedding-nbr fingerprint gate FAILED", file=sys.stderr)
            return 1
    except Exception as exc:
        print(f"embedding-nbr fingerprint check failed: {exc}", file=sys.stderr)
        return 1
    # 詞庫渠道同步（ADR-0036）：閘綠後預設 copy → public + manifest
    if not getattr(args, "no_copy_public", False):
        import os
        import subprocess

        print("==> copy-db (詞庫渠道同步 → public manifest + gzip)")
        copy_db = REPO_ROOT / "client" / "copy-db.js"
        if not copy_db.is_file():
            print(f"copy-db missing: {copy_db}", file=sys.stderr)
            return 1
        env = {**os.environ, "LEXICON_VERSION": os.environ.get("LEXICON_VERSION", "v1.0.7")}
        proc = subprocess.run(
            ["node", str(copy_db)],
            cwd=REPO_ROOT / "client",
            check=False,
            env=env,
        )
        if proc.returncode != 0:
            print(f"copy-db failed with exit {proc.returncode}", file=sys.stderr)
            return proc.returncode
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

    p_static = sub.add_parser(
        "ingest-static-relations",
        help="Alias for build-word-relations (static cilin/guotong/compound)",
    )
    p_static.add_argument("--chunk-size", type=int, default=300, help="Ignored (compat)")

    p_build_rel = sub.add_parser(
        "build-word-relations",
        help="Precompute static syn/ant into word_relations (canonical ids + bulk insert)",
    )
    p_build_rel.add_argument("--manifest", help="Override data/syn_ant/sources.yaml")
    p_build_rel.add_argument(
        "--compound-path",
        help="Override compound antonyms list (default: data/syn_ant/compound_antonyms.txt)",
    )
    p_build_rel.add_argument(
        "--append",
        action="store_true",
        help="Do not clear static sources before insert (default: replace cilin/guotong/compound_ant)",
    )

    p_cilin = sub.add_parser(
        "ingest-cilin",
        help="Deprecated alias: full static 關係直寫 via build-word-relations",
    )
    p_cilin.add_argument("--chunk-size", type=int, default=300, help="Leaf groups per chunk (default 300)")
    p_cilin.add_argument("--source-path", help="Override Cilin file path (e.g. Desktop/new_cilin.txt)")
    p_cilin.add_argument("--dedupe-existing", action="store_true", default=True, help="Skip existing canonical syn pairs")
    p_cilin.add_argument("--no-dedupe-existing", dest="dedupe_existing", action="store_false")
    p_cilin.add_argument(
        "--no-replace-relations",
        dest="replace_relations",
        action="store_false",
        help="Keep existing word_relations with source=cilin (default: clear cilin rows first)",
    )
    p_cilin.set_defaults(replace_relations=True)

    p_expand = sub.add_parser("expand-antonyms-cilin", help="Export cilin-derived ant pairs TSV (default)")
    p_expand.add_argument("--source", default="ant_cilin_exanded", help="Source tag for derived ant relations")
    p_expand.add_argument(
        "--output",
        default=None,
        help="TSV output path (default: data/syn_ant/ant_cilin_exanded_pairs.tsv)",
    )
    p_expand.add_argument(
        "--insert",
        action="store_true",
        help="Also persist pairs to word_relations (maintainer debug; default export-only)",
    )
    p_expand.add_argument("--cilin-syn-source", default="cilin", help="Deprecated; core uses 靜態詞林埠")
    p_expand.add_argument("--confidence", type=float, default=0.75, help="Score for derived ant relations")
    p_expand.add_argument("--batch-size", type=int, default=2000, help="Insert batch size")
    p_expand.add_argument("--dedupe-existing", action="store_true", default=True, help="Skip existing ant keys")
    p_expand.add_argument("--no-dedupe-existing", dest="dedupe_existing", action="store_false")
    p_expand.add_argument("--no-static", dest="no_static", action="store_true", help="Seeds: DB ants only, no static thesaurus")
    p_expand.add_argument(
        "--no-replace-relations",
        dest="replace_relations",
        action="store_false",
        help="With --insert: keep existing derived ant rows (default: clear source first)",
    )
    p_expand.set_defaults(replace_relations=True)

    p_mirror = sub.add_parser(
        "expand-antonyms-mirror",
        help="Export mirror ant pairs TSV (default)",
    )
    p_mirror.add_argument("--source", default="ant_syn_mirror", help="Source tag for mirror ant relations")
    p_mirror.add_argument(
        "--output",
        default=None,
        help="TSV output path (default: data/syn_ant/ant_syn_mirror_pairs.tsv)",
    )
    p_mirror.add_argument(
        "--insert",
        action="store_true",
        help="Also persist pairs to word_relations (maintainer debug; default export-only)",
    )
    p_mirror.add_argument("--confidence", type=float, default=0.72, help="Score for mirror ant relations")
    p_mirror.add_argument("--batch-size", type=int, default=2000, help="Insert batch size")
    p_mirror.add_argument("--dedupe-existing", action="store_true", default=True, help="Skip existing ant keys")
    p_mirror.add_argument("--no-dedupe-existing", dest="dedupe_existing", action="store_false")
    p_mirror.add_argument("--no-static", dest="no_static", action="store_true", help="Seeds: DB ants only, no static thesaurus")
    p_mirror.add_argument(
        "--no-replace-relations",
        dest="replace_relations",
        action="store_false",
        help="With --insert: keep existing mirror ant rows (default: clear source first)",
    )
    p_mirror.set_defaults(replace_relations=True)

    p_derived = sub.add_parser(
        "ingest-derived-ant-snapshots",
        help="Inject baked cilin-derived and mirror ant snapshots into word_relations",
    )
    p_derived.add_argument("--cilin-path", help=f"Override cilin snapshot (default: {DEFAULT_CILIN_SNAPSHOT.name})")
    p_derived.add_argument("--mirror-path", help=f"Override mirror snapshot (default: {DEFAULT_MIRROR_SNAPSHOT.name})")

    p_bake_derived = sub.add_parser(
        "bake-derived-ant-snapshots",
        help="Bake cilin-derived + mirror ant snapshots (live expand or export-only)",
    )
    p_bake_derived.add_argument(
        "--cilin-out",
        default=str(DEFAULT_CILIN_SNAPSHOT),
        help="Cilin-derived ant snapshot TSV output",
    )
    p_bake_derived.add_argument(
        "--mirror-out",
        default=str(DEFAULT_MIRROR_SNAPSHOT),
        help="Mirror ant snapshot TSV output",
    )
    p_bake_derived.add_argument("--export-only", action="store_true", help="Only export existing DB rows to TSV")
    p_bake_derived.add_argument("--cilin-syn-source", default="cilin", help="Cilin synonym source for live expand")
    p_bake_derived.add_argument("--cilin-confidence", type=float, default=0.75, help="Score for cilin-derived ant")
    p_bake_derived.add_argument("--mirror-confidence", type=float, default=0.72, help="Score for mirror ant")
    p_bake_derived.add_argument("--batch-size", type=int, default=2000, help="Insert batch size for live expand")
    p_bake_derived.add_argument("--no-static", dest="no_static", action="store_true", help="Mirror expand: DB syn only")

    p_bridge = sub.add_parser(
        "expand-antonyms-syn-bridge",
        help="Expand antonyms via embedding-selected synonym bridge",
        description="近義橋反義 ingest。全量重跑與驗收見 docs/ingest-bridge-ant.md",
    )
    p_bridge.add_argument("--source", default="ant_syn_bridge", help="Source tag for bridged ant relations")
    p_bridge.add_argument("--batch-size", type=int, default=2000, help="Insert batch size")
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
    p_bake.add_argument("--batch-size", type=int, default=2000, help="Insert batch size")
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

    p_build_db = sub.add_parser(
        "build-db",
        help="Wipe and rebuild lyrics.db from SSOT manifest",
        epilog=BUILD_DB_PATH_HINT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_build_db.add_argument(
        "--lexicon-manifest",
        default=None,
        help="Path to data/lexicon/sources.yaml (default: repo manifest)",
    )
    p_build_db.add_argument(
        "--stage",
        choices=("all", "words", "relations", "seal"),
        default="all",
        help="Pipeline slice: all (default) | words | relations | seal",
    )
    p_build_db.add_argument(
        "--skip-relations",
        action="store_true",
        help="Alias for --stage words (rebuild words + seal only)",
    )
    p_build_db.add_argument(
        "--no-layer-cache",
        action="store_true",
        help="Force re-parse all lexicon sources (skip .cache/lexicon-layers)",
    )
    p_build_db.add_argument("--no-exports", action="store_true", help="Skip export + README sync")
    p_build_db.add_argument(
        "--copy-public",
        action="store_true",
        help="Deprecated no-op: 詞庫渠道同步 is the default after a green release gate",
    )
    p_build_db.add_argument(
        "--no-copy-public",
        action="store_true",
        help="Skip 詞庫渠道同步 (copy-db to client/public after green gate)",
    )
    p_build_db.add_argument(
        "--min-multi-char",
        type=int,
        default=None,
        metavar="N",
        help="Fail if fewer than N length>=2 words (release gate)",
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

    p_manual = sub.add_parser(
        "apply-manual-relations",
        help=(
            "關係補錄熱套用：clear manual* then apply data/relations/manual_relations.tsv "
            "(fast path when only the 補錄清單 changed — not a full build-db)"
        ),
    )
    p_manual.add_argument(
        "--tsv",
        default="data/relations/manual_relations.tsv",
        help="關係補錄清單 path",
    )
    p_manual.add_argument(
        "--no-clear",
        action="store_true",
        help="Only append from TSV (skip clear manual*)",
    )

    p_emb = sub.add_parser(
        "bake-embedding-topk",
        help="GPU bge-m3 top-K → semantic_related (A) + proposal TSV (C)",
        description=(
            "語意向量鄰居烘焙（強制 CUDA）。A: degree<T 寫 embedding_cosine/"
            "semantic_related；C: 全庫提案 TSV。見 docs/working-plans/"
            "2026-08-05-embedding-topk-semantic-bake.md"
        ),
    )
    p_emb.add_argument(
        "--model-dir",
        default=r"F:\localAI\data\models\bge-m3-onnx",
        help="bge-m3 ONNX directory",
    )
    p_emb.add_argument(
        "--cache-dir",
        default=str(REPO_ROOT / ".cache" / "embedding_topk"),
        help="vectors + default proposal TSV dir",
    )
    p_emb.add_argument("--proposal-tsv", default=None, help="C proposal TSV path")
    p_emb.add_argument("--vectors", default=None, help="npz npz path")
    p_emb.add_argument("--syn-degree-lt", type=int, default=5, help="A: write if direct syn degree < T")
    p_emb.add_argument("--a-topk", type=int, default=10, help="A: neighbors per eligible head")
    p_emb.add_argument("--a-min-cosine", type=float, default=0.50, help="A: min cosine")
    p_emb.add_argument("--c-topk", type=int, default=20, help="C: proposal neighbors per head")
    p_emb.add_argument("--encode-batch", type=int, default=64, help="GPU encode batch size")
    p_emb.add_argument("--limit", type=int, default=None, help="Debug: first N distinct chars")
    p_emb.add_argument("--skip-encode", action="store_true", help="Reuse vectors npz")
    p_emb.add_argument("--no-write-db", action="store_true", help="Skip clearing/writing relations")
    p_emb.add_argument(
        "--write-edges",
        action="store_true",
        help="Also insert embedding_cosine rows (default: E1c bin only)",
    )
    p_emb.add_argument(
        "--keep-edges",
        action="store_true",
        help="Do not strip embedding_cosine after bin write",
    )
    p_emb.add_argument(
        "--no-replace",
        action="store_true",
        help="Do not clear existing embedding_cosine rows first",
    )

    p_nbr = sub.add_parser(
        "export-embedding-nbr",
        help="E1c: build embedding-nbr.bin from existing embedding_cosine edges",
    )
    p_nbr.add_argument(
        "--cache-dir",
        default=str(REPO_ROOT / ".cache" / "embedding_topk"),
    )
    p_nbr.add_argument(
        "--keep-edges",
        action="store_true",
        help="Keep word_relations embedding_cosine rows after export",
    )

    p_stamp = sub.add_parser(
        "stamp-embedding-nbr-fp",
        help="Write char_id_fingerprint onto existing embedding-nbr.meta.json (bin unchanged)",
    )
    p_check = sub.add_parser(
        "check-embedding-nbr-fp",
        help="Verify embedding-nbr.bin is reusable vs current lyrics.db char→id map",
    )
    p_check.add_argument(
        "--require",
        action="store_true",
        help="Fail if meta/bin missing (default: missing is ok)",
    )

    args = parser.parse_args(argv)
    if args.command == "report":
        return cmd_report(args)
    if args.command == "build-word-relations":
        return cmd_build_word_relations(args)
    if args.command == "ingest-static-relations":
        return cmd_ingest_static_relations(args)
    if args.command == "ingest-cilin":
        return cmd_ingest_cilin(args)
    if args.command == "expand-antonyms-cilin":
        return cmd_expand_antonyms_cilin(args)
    if args.command == "expand-antonyms-mirror":
        return cmd_expand_antonyms_mirror(args)
    if args.command == "ingest-derived-ant-snapshots":
        return cmd_ingest_derived_ant_snapshots(args)
    if args.command == "bake-derived-ant-snapshots":
        return cmd_bake_derived_ant_snapshots(args)
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
    if args.command == "apply-manual-relations":
        return cmd_apply_manual_relations(args)
    if args.command == "bake-embedding-topk":
        return cmd_bake_embedding_topk(args)
    if args.command == "export-embedding-nbr":
        return cmd_export_embedding_nbr(args)
    if args.command == "stamp-embedding-nbr-fp":
        return cmd_stamp_embedding_nbr_fp(args)
    if args.command == "check-embedding-nbr-fp":
        return cmd_check_embedding_nbr_fp(args)
    return 1


def cmd_bake_embedding_topk(args: argparse.Namespace) -> int:
    from ingest.bake_embedding_topk import bake_embedding_topk

    ensure_word_relations_table()
    with SessionLocal() as db:
        try:
            stats = bake_embedding_topk(
                db,
                model_dir=Path(args.model_dir),
                cache_dir=Path(args.cache_dir),
                proposal_tsv=Path(args.proposal_tsv) if args.proposal_tsv else None,
                vectors_path=Path(args.vectors) if args.vectors else None,
                syn_degree_lt=args.syn_degree_lt,
                a_topk=args.a_topk,
                a_min_cosine=args.a_min_cosine,
                c_topk=args.c_topk,
                encode_batch=args.encode_batch,
                replace=not args.no_replace,
                skip_encode=args.skip_encode,
                write_db=not args.no_write_db,
                write_edges=bool(args.write_edges),
                strip_edges=not args.keep_edges,
                limit_chars=args.limit,
            )
        except Exception as e:
            print(f"bake-embedding-topk FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            return 1
    print("bake-embedding-topk stats:", stats)
    return 0


def cmd_export_embedding_nbr(args: argparse.Namespace) -> int:
    from ingest.bake_embedding_topk import export_nbr_from_existing_edges

    ensure_word_relations_table()
    with SessionLocal() as db:
        try:
            stats = export_nbr_from_existing_edges(
                db,
                cache_dir=Path(args.cache_dir),
                strip_edges=not args.keep_edges,
            )
        except Exception as e:
            print(f"export-embedding-nbr FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            return 1
    print("export-embedding-nbr stats:", stats)
    return 0


def cmd_stamp_embedding_nbr_fp(args: argparse.Namespace) -> int:
    from app.domain.lexicon.embedding_nbr_codec import stamp_fingerprint_on_meta

    public_meta = REPO_ROOT / "client" / "public" / "embedding-nbr.meta.json"
    cache_meta = REPO_ROOT / ".cache" / "embedding_topk" / "embedding-nbr.meta.json"
    stats = stamp_fingerprint_on_meta(
        db_path=REPO_ROOT / "lyrics.db",
        meta_path=public_meta,
        also=[cache_meta],
    )
    print("stamp-embedding-nbr-fp:", stats)
    return 0 if stats.get("written") else 1


def cmd_check_embedding_nbr_fp(args: argparse.Namespace) -> int:
    from app.domain.lexicon.embedding_nbr_codec import verify_embedding_nbr_fingerprint

    public_meta = REPO_ROOT / "client" / "public" / "embedding-nbr.meta.json"
    r = verify_embedding_nbr_fingerprint(
        db_path=REPO_ROOT / "lyrics.db",
        meta_path=public_meta,
        require_present=bool(args.require),
    )
    print("check-embedding-nbr-fp:", r)
    return 0 if r.get("ok") else 1


def cmd_apply_manual_relations(args: argparse.Namespace) -> int:
    from ingest.manual_relations_apply import (
        apply_manual_relations,
        hot_apply_manual_relations,
    )

    ensure_word_relations_table()
    tsv = Path(args.tsv)
    if not tsv.is_file():
        print(f"tsv not found: {tsv}", file=sys.stderr)
        return 1
    with SessionLocal() as db:
        if args.no_clear:
            stats = apply_manual_relations(db, tsv)
        else:
            stats = hot_apply_manual_relations(db, tsv)
    print(f"apply-manual-relations: {stats}")
    return 0 if stats.get("errors", 0) == 0 else 1


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
