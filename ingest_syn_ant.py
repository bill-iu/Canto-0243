#!/usr/bin/env python3
"""
ingest_syn_ant.py — Syn/Ant ingest v2 CLI

Commands:
  report                          Manifest + staging + word_relations summary
  normalize [--source ID ...]     Parse sources -> normalize -> syn_ant_edges staging
  build-relations                 Merge staging -> word_relations

Examples:
  python ingest_syn_ant.py report
  python ingest_syn_ant.py normalize --source current_static
  python ingest_syn_ant.py normalize --source cow --allow-external
  python ingest_syn_ant.py build-relations
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, ensure_syn_ant_edges_table, ensure_word_relations_table
from app.models.word import WordRelation
from ingest.syn_ant_manifest import load_manifest, manifest_report, select_sources
from ingest.syn_ant_merge import (
    build_word_relations_from_staging,
    get_db_char_set,
    persist_staging_edges,
    staging_report,
)
from ingest.syn_ant_normalize import merge_staging_edges, normalize_edges
from ingest.syn_ant_sources import parse_sources


def cmd_report(_: argparse.Namespace) -> int:
    print(manifest_report())
    print()
    ensure_syn_ant_edges_table()
    ensure_word_relations_table()
    with SessionLocal() as db:
        print(staging_report(db))
        rel_count = db.query(WordRelation).count()
        print(f"\nword_relations rows: {rel_count}")
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
        db_chars = get_db_char_set(db)
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
        stats = build_word_relations_from_staging(db, allow_external=args.allow_external)
        print("build-relations stats:", stats)
    return 0


def main() -> int:
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

    args = parser.parse_args()
    if args.command == "report":
        return cmd_report(args)
    if args.command == "normalize":
        return cmd_normalize(args)
    if args.command == "build-relations":
        return cmd_build_relations(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
