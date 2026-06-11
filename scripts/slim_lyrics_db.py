#!/usr/bin/env python3
"""
Slim lyrics.db for faster startup: export embeddings to sidecar, clear main DB, VACUUM.

Usage:
  python scripts/slim_lyrics_db.py --dry-run
  python scripts/slim_lyrics_db.py
  python scripts/slim_lyrics_db.py --skip-export   # if sidecar already exists
  python scripts/slim_lyrics_db.py --restore-sidecar backup/lyrics_embeddings_20260612.jsonl.gz
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "lyrics.db"
BACKUP_DIR = ROOT / "backup"


def _file_mb(path: Path) -> float:
    if not path.is_file():
        return 0.0
    return path.stat().st_size / 1024 / 1024


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def collect_stats(db_path: Path) -> Dict[str, Any]:
    stats: Dict[str, Any] = {"db_path": str(db_path), "file_mb": _file_mb(db_path)}
    if not db_path.is_file():
        stats["error"] = "database not found"
        return stats

    conn = _connect(db_path)
    try:
        stats["page_size"] = conn.execute("PRAGMA page_size").fetchone()[0]
        stats["page_count"] = conn.execute("PRAGMA page_count").fetchone()[0]
        stats["freelist_count"] = conn.execute("PRAGMA freelist_count").fetchone()[0]
        ps = stats["page_size"]
        stats["freelist_mb"] = round(stats["freelist_count"] * ps / 1024 / 1024, 2)

        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        stats["tables"] = sorted(tables)

        if "words" in tables:
            stats["words_count"] = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
            stats["embedding_nonempty"] = conn.execute(
                "SELECT COUNT(*) FROM words WHERE embedding IS NOT NULL AND LENGTH(embedding) > 10"
            ).fetchone()[0]
            stats["embedding_bytes"] = conn.execute(
                "SELECT COALESCE(SUM(LENGTH(COALESCE(embedding, ''))), 0) FROM words"
            ).fetchone()[0]

        if "word_relations" in tables:
            stats["word_relations_count"] = conn.execute(
                "SELECT COUNT(*) FROM word_relations"
            ).fetchone()[0]

        if "syn_ant_edges" in tables:
            stats["syn_ant_edges_count"] = conn.execute(
                "SELECT COUNT(*) FROM syn_ant_edges"
            ).fetchone()[0]
        else:
            stats["syn_ant_edges_count"] = 0
    finally:
        conn.close()
    return stats


def print_stats(label: str, stats: Dict[str, Any]) -> None:
    print(f"\n=== {label} ===")
    print(f"  file: {stats.get('db_path')}")
    print(f"  size: {stats.get('file_mb', 0):.2f} MB")
    if "error" in stats:
        print(f"  error: {stats['error']}")
        return
    print(f"  freelist: {stats.get('freelist_mb', 0):.2f} MB")
    print(f"  words: {stats.get('words_count', 'n/a')}")
    print(f"  embedding non-empty: {stats.get('embedding_nonempty', 'n/a')}")
    emb_bytes = stats.get("embedding_bytes")
    if emb_bytes is not None:
        print(f"  embedding bytes: {emb_bytes / 1024 / 1024:.2f} MB")
    print(f"  word_relations: {stats.get('word_relations_count', 'n/a')}")
    print(f"  syn_ant_edges: {stats.get('syn_ant_edges_count', 'n/a')}")


def export_embeddings(
    db_path: Path,
    sidecar_path: Path,
    *,
    batch_size: int = 2000,
) -> Tuple[int, str]:
    """Export words.id + embedding to gzip JSONL. Returns (row_count, sha256_hex)."""
    sidecar_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = sidecar_path.with_suffix(sidecar_path.suffix + ".tmp")

    conn = _connect(db_path)
    count = 0
    hasher = hashlib.sha256()

    try:
        with gzip.open(tmp_path, "wt", encoding="utf-8") as out:
            offset = 0
            while True:
                rows = conn.execute(
                    """
                    SELECT id, embedding FROM words
                    WHERE embedding IS NOT NULL AND LENGTH(embedding) > 10
                    ORDER BY id
                    LIMIT ? OFFSET ?
                    """,
                    (batch_size, offset),
                ).fetchall()
                if not rows:
                    break
                for row in rows:
                    line = json.dumps(
                        {"id": int(row["id"]), "embedding": row["embedding"]},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    out.write(line + "\n")
                    hasher.update(line.encode("utf-8"))
                    count += 1
                offset += len(rows)
                if count and count % 20000 == 0:
                    print(f"  exported {count} embeddings...")

        if tmp_path.exists():
            tmp_path.replace(sidecar_path)
    finally:
        conn.close()
        if tmp_path.exists() and not sidecar_path.exists():
            tmp_path.unlink(missing_ok=True)

    return count, hasher.hexdigest()


def verify_sidecar(sidecar_path: Path, expected_count: int, expected_hash: str) -> bool:
    if not sidecar_path.is_file():
        print(f"  sidecar missing: {sidecar_path}")
        return False

    count = 0
    hasher = hashlib.sha256()
    with gzip.open(sidecar_path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            hasher.update(line.encode("utf-8"))
            count += 1

    ok = count == expected_count and hasher.hexdigest() == expected_hash
    print(f"  sidecar rows: {count} (expected {expected_count})")
    print(f"  sidecar sha256: {hasher.hexdigest()[:16]}...")
    if not ok:
        print("  WARNING: sidecar verification mismatch")
    return ok


def slim_database(
    db_path: Path,
    *,
    drop_staging: bool = True,
    vacuum_suffix: str = ".vacuumed",
) -> Path:
    """Clear embeddings, optionally drop syn_ant_edges, VACUUM INTO new file."""
    vacuum_path = db_path.with_name(db_path.name + vacuum_suffix)
    if vacuum_path.exists():
        vacuum_path.unlink()

    conn = _connect(db_path)
    try:
        conn.execute("UPDATE words SET embedding = NULL WHERE embedding IS NOT NULL AND embedding != ''")
        if drop_staging:
            conn.execute("DROP TABLE IF EXISTS syn_ant_edges")
        conn.commit()

        conn.execute(f"VACUUM INTO '{vacuum_path.as_posix()}'")
        conn.commit()
    finally:
        conn.close()

    return vacuum_path


def verify_slimmed_db(
    vacuum_path: Path,
    *,
    expected_words: int,
    expected_relations: int,
) -> bool:
    stats = collect_stats(vacuum_path)
    ok = True
    if stats.get("words_count") != expected_words:
        print(f"  words mismatch: {stats.get('words_count')} != {expected_words}")
        ok = False
    if stats.get("word_relations_count") != expected_relations:
        print(
            f"  word_relations mismatch: {stats.get('word_relations_count')} != {expected_relations}"
        )
        ok = False
    if stats.get("embedding_nonempty", 1) != 0:
        print(f"  embedding still present: {stats.get('embedding_nonempty')}")
        ok = False
    if stats.get("freelist_count", 1) != 0:
        print(f"  freelist not zero: {stats.get('freelist_count')}")
        ok = False
    return ok


def atomic_replace(db_path: Path, vacuum_path: Path) -> None:
    bak_path = db_path.with_suffix(db_path.suffix + ".bak")
    if bak_path.exists():
        bak_path.unlink()
    if db_path.exists():
        db_path.rename(bak_path)
    vacuum_path.rename(db_path)
    print(f"  replaced {db_path.name}; backup at {bak_path.name}")


def restore_sidecar(db_path: Path, sidecar_path: Path, *, batch_size: int = 500) -> int:
    """Restore embeddings from sidecar into db (for verification / optional use)."""
    conn = _connect(db_path)
    updated = 0
    try:
        batch: list[tuple[str, int]] = []
        with gzip.open(sidecar_path, "rt", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                batch.append((obj["embedding"], int(obj["id"])))
                if len(batch) >= batch_size:
                    conn.executemany(
                        "UPDATE words SET embedding = ? WHERE id = ?",
                        batch,
                    )
                    conn.commit()
                    updated += len(batch)
                    batch.clear()
            if batch:
                conn.executemany(
                    "UPDATE words SET embedding = ? WHERE id = ?",
                    batch,
                )
                conn.commit()
                updated += len(batch)
    finally:
        conn.close()
    return updated


def cmd_dry_run(db_path: Path) -> int:
    print_stats("lyrics.db stats", collect_stats(db_path))
    return 0


def cmd_slim(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    if not db_path.is_file():
        print(f"Database not found: {db_path}")
        return 1

    before = collect_stats(db_path)
    print_stats("before", before)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = date.today().strftime("%Y%m%d")
    pre_backup = BACKUP_DIR / f"lyrics.db.pre-slim-{stamp}.db"
    if not pre_backup.exists():
        print(f"\nCopying backup -> {pre_backup}")
        shutil.copy2(db_path, pre_backup)
    else:
        print(f"\nBackup already exists: {pre_backup}")

    sidecar_path = Path(args.sidecar).resolve() if args.sidecar else (
        BACKUP_DIR / f"lyrics_embeddings_{stamp}.jsonl.gz"
    )

    export_count = 0
    export_hash = ""

    if not args.skip_export:
        if sidecar_path.is_file() and not args.force_export:
            print(f"\nSidecar exists, verifying: {sidecar_path}")
            with gzip.open(sidecar_path, "rt", encoding="utf-8") as f:
                export_count = sum(1 for line in f if line.strip())
            export_hash = "skip"
        else:
            print(f"\nExporting embeddings -> {sidecar_path}")
            export_count, export_hash = export_embeddings(db_path, sidecar_path)
            print(f"  exported {export_count} rows, sha256={export_hash[:16]}...")

        if export_hash != "skip":
            if not verify_sidecar(sidecar_path, export_count, export_hash):
                print("Export verification failed; aborting slim.")
                return 1
    else:
        print("\nSkipping export (--skip-export)")

    expected_words = before.get("words_count", 0)
    expected_relations = before.get("word_relations_count", 0)

    print("\nSlimming database (clear embedding, drop staging, VACUUM INTO)...")
    vacuum_path = slim_database(
        db_path,
        drop_staging=not args.keep_staging,
    )

    print(f"  vacuum file: {vacuum_path} ({_file_mb(vacuum_path):.2f} MB)")

    if not verify_slimmed_db(
        vacuum_path,
        expected_words=expected_words,
        expected_relations=expected_relations,
    ):
        print("Slimmed DB verification failed; not replacing original.")
        return 1

    if not args.no_replace:
        atomic_replace(db_path, vacuum_path)
    else:
        print(f"  --no-replace: leaving vacuum at {vacuum_path}")

    after = collect_stats(db_path if not args.no_replace else vacuum_path)
    print_stats("after", after)
    print(f"\nSidecar: {sidecar_path} ({_file_mb(sidecar_path):.2f} MB)")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    db_path = Path(args.db).resolve()
    sidecar_path = Path(args.restore_sidecar).resolve()
    if not sidecar_path.is_file():
        print(f"Sidecar not found: {sidecar_path}")
        return 1
    n = restore_sidecar(db_path, sidecar_path)
    print(f"Restored {n} embeddings into {db_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Slim lyrics.db (export embedding sidecar + VACUUM)")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Path to lyrics.db")
    parser.add_argument("--dry-run", action="store_true", help="Print stats only")
    parser.add_argument("--skip-export", action="store_true", help="Skip embedding export")
    parser.add_argument("--force-export", action="store_true", help="Re-export even if sidecar exists")
    parser.add_argument("--keep-staging", action="store_true", help="Do not DROP syn_ant_edges")
    parser.add_argument("--no-replace", action="store_true", help="VACUUM but do not swap files")
    parser.add_argument("--sidecar", help="Sidecar output path (default: backup/lyrics_embeddings_DATE.jsonl.gz)")
    parser.add_argument(
        "--restore-sidecar",
        metavar="PATH",
        help="Restore embeddings from sidecar into --db (verification)",
    )
    args = parser.parse_args()

    if args.dry_run:
        return cmd_dry_run(Path(args.db).resolve())
    if args.restore_sidecar:
        return cmd_restore(args)
    return cmd_slim(args)


if __name__ == "__main__":
    raise SystemExit(main())
