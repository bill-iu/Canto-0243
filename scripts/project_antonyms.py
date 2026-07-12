#!/usr/bin/env python3
"""Maintainer CLI for 專案自建反義 batch: seed / filter / sample / validate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.domain.relations.word_relation_queries import load_db_char_set
from app.lexicon.essay_index import get_essay_frequency, load_essay_corpus
from ingest.project_antonyms import (
    DEFAULT_META,
    DEFAULT_SEED_K,
    DEFAULT_TSV,
    ProjectAntonymsError,
    export_seed_literals,
    filter_proposals,
    load_meta,
    parse_project_antonyms_tsv,
    passes_quality_gate,
    sample_pairs,
    sample_size_for,
    static_ant_heads_from_port,
    syn_pairs_from_db,
    write_proposals_tsv,
    write_seed_export,
)


def _session(db_path: Path):
    if not db_path.is_file():
        raise SystemExit(f"missing db: {db_path}")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)()


def cmd_seed_export(args: argparse.Namespace) -> int:
    load_essay_corpus()
    db = _session(Path(args.db))
    try:
        membership = load_db_char_set(db)
        static_heads = static_ant_heads_from_port()
        seeds = export_seed_literals(
            db,
            k=args.k,
            essay_freq=get_essay_frequency,
            membership=membership,
            static_ant_heads=static_heads,
        )
    finally:
        db.close()
    out = Path(args.out)
    write_seed_export(out, seeds)
    print(
        json.dumps(
            {
                "k": args.k,
                "exported": len(seeds),
                "static_ant_heads": len(static_heads),
                "out": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _read_pair_lines(path: Path) -> list[tuple[str, str]]:
    """Fail-closed: exactly two tab-separated columns per data row."""
    pairs: list[tuple[str, str]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if lineno == 1 and line.startswith("head\t"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            raise ProjectAntonymsError(
                f"{path}:{lineno}: expected exactly 2 columns, got {len(parts)}"
            )
        head, tail = parts[0].strip(), parts[1].strip()
        if not head or not tail:
            raise ProjectAntonymsError(f"{path}:{lineno}: empty head/tail")
        pairs.append((head, tail))
    return pairs


def cmd_filter(args: argparse.Namespace) -> int:
    db = _session(Path(args.db))
    try:
        membership = load_db_char_set(db)
        syn_pairs = syn_pairs_from_db(db)
    finally:
        db.close()
    try:
        proposals = _read_pair_lines(Path(args.proposals))
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    stats = filter_proposals(
        proposals,
        membership=membership,
        syn_pairs=syn_pairs,
    )
    out = Path(args.out)
    write_proposals_tsv(out, stats.accepted, batch_id=args.batch_id)
    report = {
        "accepted": len(stats.accepted),
        "rejected": len(stats.rejected),
        "guotong_overlap_note": stats.guotong_overlap,
        "reject_reasons": {},
        "out": str(out),
    }
    for row in stats.rejected:
        reason = row["reason"]
        report["reject_reasons"][reason] = report["reject_reasons"].get(reason, 0) + 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    db = _session(Path(args.db)) if args.db else None
    try:
        membership = load_db_char_set(db) if db is not None else None
        syn_pairs = syn_pairs_from_db(db) if db is not None else None
        pairs = [
            (p.head, p.tail)
            for p in parse_project_antonyms_tsv(
                args.tsv,
                meta=load_meta(args.meta),
                membership=membership,
                syn_pairs=syn_pairs,
                require_file=True,
            )
        ]
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        if db is not None:
            db.close()
    sampled = sample_pairs(pairs, seed=args.seed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["head\ttail"] + [f"{h}\t{t}" for h, t in sampled]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "n": len(pairs),
                "sample_size": sample_size_for(len(pairs)),
                "sampled": len(sampled),
                "seed": args.seed,
                "out": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    db = _session(Path(args.db))
    try:
        membership = load_db_char_set(db)
        syn_pairs = syn_pairs_from_db(db)
        meta = load_meta(args.meta)
        pairs = parse_project_antonyms_tsv(
            args.tsv,
            meta=meta,
            membership=membership,
            syn_pairs=syn_pairs,
            require_file=True,
        )
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        db.close()
    print(json.dumps({"ok": True, "pairs": len(pairs)}, ensure_ascii=False))
    return 0


def cmd_quality_check(args: argparse.Namespace) -> int:
    if args.sample_n <= 0 or args.ok < 0 or args.ok > args.sample_n:
        print(
            json.dumps(
                {
                    "ok_count": args.ok,
                    "sample_n": args.sample_n,
                    "passes": False,
                    "error": "impossible counts",
                    "threshold": 0.85,
                },
                ensure_ascii=False,
            )
        )
        return 1
    ok = passes_quality_gate(args.ok, args.sample_n)
    print(
        json.dumps(
            {
                "ok_count": args.ok,
                "sample_n": args.sample_n,
                "passes": ok,
                "threshold": 0.85,
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


def cmd_report(args: argparse.Namespace) -> int:
    """Print accepted TSV vs DB ant source stats (WP-06)."""
    from collections import Counter

    from sqlalchemy import text

    from app.domain.relations.ranking import DERIVED_ANT_SOURCES, SOURCE_BASE_RANK
    from app.domain.thesaurus.port import StaticThesaurusPort
    from ingest.project_antonyms import (
        PROJECT_ANT_SOURCE,
        collect_project_ant_tuples,
    )
    from ingest.word_relations_build import _SOURCE_RANK

    db = _session(Path(args.db))
    try:
        membership = load_db_char_set(db)
        syn_pairs = syn_pairs_from_db(db)
        meta = load_meta(args.meta)
        pairs = parse_project_antonyms_tsv(
            args.tsv,
            meta=meta,
            membership=membership,
            syn_pairs=syn_pairs,
            require_file=True,
        )
        covered_heads = {p.head for p in pairs}
        port = StaticThesaurusPort(auto_load=True)
        static_heads = static_ant_heads_from_port(port)
        overlap = sum(
            1 for p in pairs if p.tail in set(port.get_antonyms(p.head) or [])
        )
        project_rows = db.execute(
            text(
                "SELECT COUNT(*) FROM word_relations "
                "WHERE source=:s AND relation_type='ant'"
            ),
            {"s": PROJECT_ANT_SOURCE},
        ).scalar()
        by_src = Counter(
            r[0]
            for r in db.execute(
                text("SELECT source FROM word_relations WHERE relation_type='ant'")
            )
        )
        seeds = set(
            export_seed_literals(
                db,
                k=500,
                essay_freq=get_essay_frequency,
                membership=membership,
                static_ant_heads=static_heads,
            )
        )
        seed_hits = sorted(h for h in covered_heads if h in seeds)
        t1 = collect_project_ant_tuples(db, tsv_path=args.tsv, meta_path=args.meta)
        t2 = collect_project_ant_tuples(db, tsv_path=args.tsv, meta_path=args.meta)
        batch = next(iter((meta.get("batches") or {}).values()), {})
        sample_verdicts = batch.get("sample_verdicts") or []
        sample_ok = int(batch.get("sample_ok") or 0)
        sample_n = int(batch.get("sample_n") or 0)
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    finally:
        db.close()

    build_idempotent = None
    if args.dual_build:
        from ingest.word_relations_build import build_word_relations

        def _project_fp(session) -> list[tuple]:
            return sorted(
                (int(a), int(b), float(s) if s is not None else None)
                for a, b, s in session.execute(
                    text(
                        "SELECT word_id, related_id, score FROM word_relations "
                        "WHERE source=:src AND relation_type='ant' "
                        "ORDER BY word_id, related_id"
                    ),
                    {"src": PROJECT_ANT_SOURCE},
                )
            )

        db2 = _session(Path(args.db))
        try:
            build_word_relations(db2)
            fp1 = _project_fp(db2)
            build_word_relations(db2)
            fp2 = _project_fp(db2)
            build_idempotent = fp1 == fp2 and len(fp1) == len(pairs)
        finally:
            db2.close()

    report = {
        "accepted_pairs_tsv": len(pairs),
        "unique_db_project_ant_rows": int(project_rows or 0),
        "guotong_static_overlap_with_tsv": overlap,
        "covered_heads": len(covered_heads),
        "static_ant_heads": len(static_heads),
        "bridge_ant_rows": int(by_src.get("ant_syn_bridge", 0)),
        "ant_source_counts": dict(sorted(by_src.items())),
        "covered_heads_still_in_top500_seeds": len(seed_hits),
        "rank_project": SOURCE_BASE_RANK.get("project_ant"),
        "rank_guotong": SOURCE_BASE_RANK.get("guotong"),
        "merge_rank_project": _SOURCE_RANK.get("project_ant"),
        "project_not_derived": PROJECT_ANT_SOURCE not in DERIVED_ANT_SOURCES,
        "collect_idempotent": t1 == t2,
        "sample_n": sample_n,
        "sample_ok": sample_ok,
        "sample_verdicts": len(sample_verdicts),
        "build_idempotent": build_idempotent,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    ok = (
        report["rank_project"] == 12
        and report["merge_rank_project"] == 12
        and report["project_not_derived"]
        and report["collect_idempotent"]
        and report["covered_heads_still_in_top500_seeds"] == 0
        and report["accepted_pairs_tsv"] == report["unique_db_project_ant_rows"]
        and report["sample_n"] > 0
        and report["sample_verdicts"] == report["sample_n"]
        and report["sample_ok"] <= report["sample_n"]
        and (build_idempotent is True if args.dual_build else True)
    )
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="專案自建反義 batch tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_seed = sub.add_parser("seed-export", help="Export Top-K 有近無直連反 seeds")
    p_seed.add_argument("--db", default=str(ROOT / "lyrics.db"))
    p_seed.add_argument("--k", type=int, default=DEFAULT_SEED_K)
    p_seed.add_argument("--out", required=True)
    p_seed.set_defaults(func=cmd_seed_export)

    p_filter = sub.add_parser("filter", help="Hard-filter proposal pairs")
    p_filter.add_argument("--db", default=str(ROOT / "lyrics.db"))
    p_filter.add_argument("--proposals", required=True, help="TSV or head\\ttail lines")
    p_filter.add_argument("--batch-id", required=True)
    p_filter.add_argument("--out", required=True)
    p_filter.set_defaults(func=cmd_filter)

    p_sample = sub.add_parser("sample", help="Reproducible quality-gate sample")
    p_sample.add_argument("--db", default=str(ROOT / "lyrics.db"))
    p_sample.add_argument("--tsv", default=str(DEFAULT_TSV))
    p_sample.add_argument("--meta", default=str(DEFAULT_META))
    p_sample.add_argument("--seed", type=int, required=True)
    p_sample.add_argument("--out", required=True)
    p_sample.set_defaults(func=cmd_sample)

    p_val = sub.add_parser("validate", help="Fail-closed validate authoritative TSV+meta")
    p_val.add_argument("--db", default=str(ROOT / "lyrics.db"))
    p_val.add_argument("--tsv", default=str(DEFAULT_TSV))
    p_val.add_argument("--meta", default=str(DEFAULT_META))
    p_val.set_defaults(func=cmd_validate)

    p_q = sub.add_parser("quality-check", help="Check OK-rate gate")
    p_q.add_argument("--ok", type=int, required=True)
    p_q.add_argument("--sample-n", type=int, required=True)
    p_q.set_defaults(func=cmd_quality_check)

    p_rep = sub.add_parser("report", help="WP-06 stats: TSV vs DB ant sources")
    p_rep.add_argument("--db", default=str(ROOT / "lyrics.db"))
    p_rep.add_argument("--tsv", default=str(DEFAULT_TSV))
    p_rep.add_argument("--meta", default=str(DEFAULT_META))
    p_rep.add_argument(
        "--dual-build",
        action="store_true",
        help="Re-run build-word-relations twice and compare project_ant fingerprint",
    )
    p_rep.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
