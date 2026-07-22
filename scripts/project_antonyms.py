#!/usr/bin/env python3
"""Maintainer CLI for 專案自建反義 batch: seed / filter / sample / validate.

ponytail: 300-line limit exemption — maintainer CLI subcommands share one entrypoint.
"""
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
    """Fail-closed: exactly two tab-separated columns per data row (raw split)."""
    pairs: list[tuple[str, str]] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if raw == "" or raw.startswith("#"):
            continue
        if lineno == 1 and raw == "head\ttail":
            continue
        parts = raw.split("\t")
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
    from ingest.project_antonyms import OK_RATE_THRESHOLD, parse_ok_rate_threshold

    threshold = (
        float(args.threshold)
        if args.threshold is not None
        else OK_RATE_THRESHOLD
    )
    try:
        threshold = parse_ok_rate_threshold(
            threshold,
            field="threshold",
            path=Path("<cli>"),
            batch_id="quality-check",
        )
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.sample_n <= 0 or args.ok < 0 or args.ok > args.sample_n:
        print(
            json.dumps(
                {
                    "ok_count": args.ok,
                    "sample_n": args.sample_n,
                    "passes": False,
                    "error": "impossible counts",
                    "threshold": threshold,
                },
                ensure_ascii=False,
            )
        )
        return 1
    ok = passes_quality_gate(args.ok, args.sample_n, threshold=threshold)
    print(
        json.dumps(
            {
                "ok_count": args.ok,
                "sample_n": args.sample_n,
                "passes": ok,
                "threshold": threshold,
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


def cmd_report(args: argparse.Namespace) -> int:
    """Print accepted TSV vs DB ant source stats (WP-06)."""
    from collections import Counter

    from sqlalchemy import text

    from app.domain.relation_pool.ranking import DERIVED_ANT_SOURCES, SOURCE_BASE_RANK
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
        from ingest.word_relations_build import (
            LEGACY_SOURCES,
            STATIC_SOURCES,
            build_word_relations,
        )

        static_src = tuple(dict.fromkeys((*STATIC_SOURCES, *LEGACY_SOURCES)))

        def _static_fp(session) -> list[tuple]:
            placeholders = ",".join(f":s{i}" for i in range(len(static_src)))
            params = {f"s{i}": s for i, s in enumerate(static_src)}
            return sorted(
                (
                    int(a),
                    int(b),
                    str(rtype),
                    str(src or ""),
                    float(score) if score is not None else None,
                    str(group_codes or ""),
                )
                for a, b, rtype, src, score, group_codes in session.execute(
                    text(
                        "SELECT word_id, related_id, relation_type, source, score, group_codes "
                        f"FROM word_relations WHERE source IN ({placeholders}) "
                        "ORDER BY word_id, related_id, relation_type, source"
                    ),
                    params,
                )
            )

        db2 = _session(Path(args.db))
        try:
            build_word_relations(db2)
            fp1 = _static_fp(db2)
            build_word_relations(db2)
            fp2 = _static_fp(db2)
            build_idempotent = fp1 == fp2 and len(fp1) > 0
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
        "quality_gate": passes_quality_gate(sample_ok, sample_n),
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
        and report["quality_gate"] is True
        and (build_idempotent is True if args.dual_build else True)
    )
    return 0 if ok else 1


def _campaign_spec(args: argparse.Namespace):
    from ingest.project_antonyms_campaign import get_campaign_spec

    return get_campaign_spec(getattr(args, "campaign", "top5000") or "top5000")


def _remap_if_top5000_default(
    args: argparse.Namespace,
    *,
    attr: str,
    top_default: str,
    new_value: str,
) -> None:
    """When --campaign switches, replace still-top5000 argparse defaults."""
    if not hasattr(args, attr):
        return
    cur = getattr(args, attr)
    if cur is None or cur == "" or cur == top_default:
        setattr(args, attr, new_value)


def _apply_campaign_path_defaults(
    args: argparse.Namespace,
    *,
    mode: str = "manifest",
) -> None:
    """Bind path args to CampaignSpec when still on top5000 defaults.

    mode:
      - manifest: --tsv/--meta are campaign manifest
      - no_natural: --tsv/--meta are no-natural ledger
      - freeze: --out-tsv/--out-meta manifest; --no-natural ledger
    """
    from ingest.project_antonyms_campaign import TOP5000_SPEC

    spec = _campaign_spec(args)
    top = TOP5000_SPEC
    if mode == "manifest":
        _remap_if_top5000_default(
            args, attr="tsv", top_default=str(top.manifest_tsv),
            new_value=str(spec.manifest_tsv),
        )
        _remap_if_top5000_default(
            args, attr="meta", top_default=str(top.manifest_meta),
            new_value=str(spec.manifest_meta),
        )
        _remap_if_top5000_default(
            args, attr="no_natural", top_default=str(top.no_natural_tsv),
            new_value=str(spec.no_natural_tsv),
        )
        _remap_if_top5000_default(
            args, attr="audit_meta", top_default=str(top.final_audit_meta),
            new_value=str(spec.final_audit_meta),
        )
    elif mode == "no_natural":
        _remap_if_top5000_default(
            args, attr="tsv", top_default=str(top.no_natural_tsv),
            new_value=str(spec.no_natural_tsv),
        )
        _remap_if_top5000_default(
            args, attr="meta", top_default=str(top.no_natural_meta),
            new_value=str(spec.no_natural_meta),
        )
        _remap_if_top5000_default(
            args, attr="manifest", top_default=str(top.manifest_tsv),
            new_value=str(spec.manifest_tsv),
        )
        _remap_if_top5000_default(
            args, attr="manifest_meta", top_default=str(top.manifest_meta),
            new_value=str(spec.manifest_meta),
        )
    elif mode == "freeze":
        _remap_if_top5000_default(
            args, attr="out_tsv", top_default=str(top.manifest_tsv),
            new_value=str(spec.manifest_tsv),
        )
        _remap_if_top5000_default(
            args, attr="out_meta", top_default=str(top.manifest_meta),
            new_value=str(spec.manifest_meta),
        )
        _remap_if_top5000_default(
            args, attr="no_natural", top_default=str(top.no_natural_tsv),
            new_value=str(spec.no_natural_tsv),
        )
    else:
        raise ValueError(f"unknown path default mode {mode!r}")


def cmd_campaign_freeze(args: argparse.Namespace) -> int:
    """Freeze campaign manifest (exclude project_ant from ranking)."""
    from ingest.project_antonyms_campaign import (
        assert_first_batch_matches_seeds,
        build_campaign_meta,
        ensure_no_natural_tsv,
        inherit_no_natural_rows,
        rank_campaign_heads,
        write_campaign_manifest,
        write_empty_no_natural_meta,
    )

    _apply_campaign_path_defaults(args, mode="freeze")
    spec = _campaign_spec(args)

    load_essay_corpus()
    db = _session(Path(args.db))
    try:
        membership = load_db_char_set(db)
        static_heads = static_ant_heads_from_port()
        heads = rank_campaign_heads(
            db,
            essay_freq=get_essay_frequency,
            membership=membership,
            static_ant_heads=static_heads,
            spec=spec,
        )
    finally:
        db.close()

    if not heads:
        print(
            json.dumps(
                {"ok": False, "error": f"no heads for campaign {spec.campaign_id}"},
                ensure_ascii=False,
            )
        )
        return 1

    if args.reference_seeds:
        seeds = [
            ln.strip()
            for ln in Path(args.reference_seeds).read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        try:
            assert_first_batch_matches_seeds(
                heads, seeds, batch_size=spec.batch_size
            )
        except ProjectAntonymsError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1

    inherited_n = 0
    inherited_src: str | None = None
    no_natural_created = False
    force = bool(getattr(args, "force_reseed_no_natural", False))
    if spec.inherit_no_natural_from is not None:
        try:
            inherited_n, _ = inherit_no_natural_rows(
                source_path=spec.inherit_no_natural_from,
                campaign_heads={h.head for h in heads},
                dest_path=args.no_natural,
                overwrite=force,
            )
            # Prefer repo-relative path in meta (portable across machines).
            try:
                inherited_src = str(
                    Path(spec.inherit_no_natural_from).resolve().relative_to(ROOT)
                ).replace("\\", "/")
            except ValueError:
                inherited_src = str(spec.inherit_no_natural_from).replace("\\", "/")
        except ProjectAntonymsError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
            return 1
    elif args.init_no_natural:
        # ponytail: create-if-missing only — never wipe reviewed no-natural rows
        no_natural_created = ensure_no_natural_tsv(args.no_natural)

    baseline = (args.baseline_commit or "").strip() or None
    if baseline is None and spec.baseline_commit:
        baseline = spec.baseline_commit

    meta = build_campaign_meta(
        heads=heads,
        db_path=args.db,
        baseline_commit=baseline,
        spec=spec,
        inherited_no_natural_count=inherited_n,
        inherited_no_natural_source=inherited_src,
    )
    write_campaign_manifest(
        heads,
        meta,
        tsv_path=args.out_tsv,
        meta_path=args.out_meta,
    )
    nn_meta = Path(str(args.no_natural).replace(".tsv", ".meta.json"))
    if spec.campaign_id == "len4":
        nn_meta = Path(str(spec.no_natural_meta))
    if args.init_no_natural and not nn_meta.is_file():
        write_empty_no_natural_meta(nn_meta)

    print(
        json.dumps(
            {
                "ok": True,
                "campaign_id": spec.campaign_id,
                "k": len(heads),
                "batch_count": meta.get("batch_count"),
                "first_head": heads[0].head if heads else None,
                "last_head": heads[-1].head if heads else None,
                "manifest_sha256": load_campaign_meta_sha(args.out_meta),
                "out_tsv": str(args.out_tsv),
                "out_meta": str(args.out_meta),
                "no_natural": str(args.no_natural),
                "no_natural_created": no_natural_created,
                "inherited_no_natural_count": inherited_n,
            },
            ensure_ascii=False,
        )
    )
    return 0


def load_campaign_meta_sha(meta_path: str) -> str:
    from ingest.project_antonyms_campaign import load_campaign_meta

    return str(load_campaign_meta(meta_path).get("manifest_sha256") or "")


def cmd_campaign_validate(args: argparse.Namespace) -> int:
    from ingest.project_antonyms_campaign import (
        accepted_coverage_heads,
        assert_campaign_complete,
        compute_campaign_progress,
        parse_campaign_manifest,
        parse_no_natural_tsv,
    )

    _apply_campaign_path_defaults(args, mode="manifest")
    spec = _campaign_spec(args)
    try:
        heads = parse_campaign_manifest(
            args.tsv, meta_path=args.meta, spec=spec
        )
        campaign = {h.head for h in heads}
        no_nat = parse_no_natural_tsv(
            args.no_natural,
            campaign_heads=campaign,
            require_file=True,
        )
        covered = accepted_coverage_heads(args.accepted_tsv)
        progress = compute_campaign_progress(
            heads,
            accepted_heads=covered,
            no_natural_heads={h for h, _, _ in no_nat},
            unresolved_sample_n=args.unresolved_sample,
        )
        if args.require_complete:
            assert_campaign_complete(progress)
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    batch1_last = min(spec.batch_size, len(heads)) - 1
    print(
        json.dumps(
            {
                "ok": True,
                "campaign_id": spec.campaign_id,
                "require_complete": bool(args.require_complete),
                "manifest_heads": len(heads),
                "no_natural_rows": len(no_nat),
                "batch_1_first": heads[0].head,
                "batch_1_last": heads[batch1_last].head,
                **progress,
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_campaign_unresolved(args: argparse.Namespace) -> int:
    from ingest.project_antonyms_campaign import (
        accepted_coverage_heads,
        parse_campaign_manifest,
        parse_no_natural_tsv,
        unresolved_heads_for_batch,
    )

    _apply_campaign_path_defaults(args, mode="manifest")
    spec = _campaign_spec(args)
    try:
        heads = parse_campaign_manifest(
            args.tsv, meta_path=args.meta, spec=spec
        )
        campaign = {h.head for h in heads}
        no_nat = parse_no_natural_tsv(
            args.no_natural, campaign_heads=campaign, require_file=True
        )
        covered = accepted_coverage_heads(args.accepted_tsv)
        unresolved = unresolved_heads_for_batch(
            heads,
            batch_index=args.batch_index,
            accepted_heads=covered,
            no_natural_heads={h for h, _, _ in no_nat},
        )
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(unresolved) + ("\n" if unresolved else ""), encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "batch_index": args.batch_index,
                "unresolved": len(unresolved),
                "heads": unresolved if args.list_heads else unresolved[: args.preview],
                "preview": args.preview if not args.list_heads else None,
                "out": str(args.out) if args.out else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_no_natural_sample(args: argparse.Namespace) -> int:
    from ingest.project_antonyms import sample_size_for
    from ingest.project_antonyms_campaign import (
        parse_campaign_manifest,
        parse_no_natural_tsv,
        sample_no_natural_rows,
    )

    _apply_campaign_path_defaults(args, mode="no_natural")
    spec = _campaign_spec(args)

    try:
        heads = parse_campaign_manifest(
            args.manifest, meta_path=args.manifest_meta, spec=spec
        )
        campaign = {h.head for h in heads}
        rows = parse_no_natural_tsv(
            args.tsv, campaign_heads=campaign, require_file=True
        )
        if args.batch_id:
            rows = [r for r in rows if r[2] == args.batch_id]
        sampled = sample_no_natural_rows(rows, seed=args.seed)
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["head\treason\tbatch_id"] + [f"{h}\t{r}\t{b}" for h, r, b in sampled]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "campaign_id": spec.campaign_id,
                "n": len(rows),
                "sample_size": sample_size_for(len(rows)),
                "sampled": len(sampled),
                "seed": args.seed,
                "batch_id": args.batch_id or None,
                "out": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_no_natural_validate(args: argparse.Namespace) -> int:
    from ingest.project_antonyms_campaign import (
        parse_campaign_manifest,
        validate_no_natural_ledger,
    )

    _apply_campaign_path_defaults(args, mode="no_natural")
    spec = _campaign_spec(args)

    try:
        heads = parse_campaign_manifest(
            args.manifest, meta_path=args.manifest_meta, spec=spec
        )
        rows = validate_no_natural_ledger(
            tsv_path=args.tsv,
            meta_path=args.meta,
            campaign_heads={h.head for h in heads},
        )
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "campaign_id": spec.campaign_id,
                "rows": len(rows),
                "batch_ids": sorted({b for _, _, b in rows}),
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_campaign_final_sample(args: argparse.Namespace) -> int:
    from ingest.project_antonyms_campaign import (
        accepted_coverage_heads,
        accepted_pairs_light,
        assert_campaign_complete,
        compute_campaign_progress,
        file_sha256,
        head_to_batch_index,
        load_campaign_meta,
        parse_campaign_manifest,
        parse_no_natural_tsv,
        stratified_sample_accepted,
        stratified_sample_no_natural,
    )

    _apply_campaign_path_defaults(args, mode="manifest")
    spec = _campaign_spec(args)
    try:
        heads = parse_campaign_manifest(
            args.tsv, meta_path=args.meta, spec=spec
        )
        campaign = {h.head for h in heads}
        no_nat = parse_no_natural_tsv(
            args.no_natural, campaign_heads=campaign, require_file=True
        )
        pairs = accepted_pairs_light(args.accepted_tsv)
        if args.require_complete:
            progress = compute_campaign_progress(
                heads,
                accepted_heads=accepted_coverage_heads(args.accepted_tsv),
                no_natural_heads={h for h, _, _ in no_nat},
                unresolved_sample_n=0,
            )
            assert_campaign_complete(progress)
        head_batch = head_to_batch_index(heads)
        batch_count = max((h.batch_index for h in heads), default=0)
        accepted = stratified_sample_accepted(
            pairs, head_batch, seed=args.seed, batch_count=batch_count
        )
        no_natural = stratified_sample_no_natural(
            no_nat, head_batch, seed=args.seed, batch_count=batch_count
        )
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1

    if args.out_accepted:
        out = Path(args.out_accepted)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["head\ttail"] + [f"{h}\t{t}" for h, t in accepted["sampled"]]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if args.out_no_natural:
        out = Path(args.out_no_natural)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["head\treason\tbatch_id"] + [
            f"{h}\t{r}\t{b}" for h, r, b in no_natural["sampled"]
        ]
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _public(result: dict) -> dict:
        return {
            "status": result["status"],
            "sample_seed": result["sample_seed"],
            "sample_n": result["sample_n"],
            "sample_parent_n": result["sample_parent_n"],
            "strata": result["strata"],
            "sampled": result["sampled"] if args.list_sampled else None,
        }

    print(
        json.dumps(
            {
                "ok": True,
                "require_complete": bool(args.require_complete),
                "manifest_sha256": load_campaign_meta(args.meta).get("manifest_sha256")
                or file_sha256(args.tsv),
                "seed": args.seed,
                "accepted": _public(accepted),
                "no_natural": _public(no_natural),
                "out_accepted": str(args.out_accepted) if args.out_accepted else None,
                "out_no_natural": str(args.out_no_natural) if args.out_no_natural else None,
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_campaign_final_validate(args: argparse.Namespace) -> int:
    from ingest.project_antonyms_campaign import (
        accepted_coverage_heads,
        accepted_pairs_light,
        assert_campaign_complete,
        compute_campaign_progress,
        file_sha256,
        load_campaign_meta,
        load_final_audit_meta,
        parse_campaign_manifest,
        parse_no_natural_tsv,
        validate_final_audit_meta,
    )

    _apply_campaign_path_defaults(args, mode="manifest")
    spec = _campaign_spec(args)
    try:
        heads = parse_campaign_manifest(
            args.tsv, meta_path=args.meta, spec=spec
        )
        campaign = {h.head for h in heads}
        no_nat = parse_no_natural_tsv(
            args.no_natural, campaign_heads=campaign, require_file=True
        )
        if args.require_complete:
            progress = compute_campaign_progress(
                heads,
                accepted_heads=accepted_coverage_heads(args.accepted_tsv),
                no_natural_heads={h for h, _, _ in no_nat},
                unresolved_sample_n=0,
            )
            assert_campaign_complete(progress)
        meta = load_final_audit_meta(args.audit_meta)
        manifest_sha = str(
            load_campaign_meta(args.meta).get("manifest_sha256") or file_sha256(args.tsv) or ""
        )
        validate_final_audit_meta(
            meta,
            path=args.audit_meta,
            manifest_sha256=manifest_sha,
            accepted_pairs=accepted_pairs_light(args.accepted_tsv),
            no_natural_rows=no_nat,
            heads=heads,
        )
    except ProjectAntonymsError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "require_complete": bool(args.require_complete),
                "accepted_status": meta["accepted"]["status"],
                "no_natural_status": meta["no_natural"]["status"],
                "accepted_sample_n": meta["accepted"]["sample_n"],
                "no_natural_sample_n": meta["no_natural"]["sample_n"],
            },
            ensure_ascii=False,
        )
    )
    return 0


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
    p_q.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="ok_rate_threshold (0.85 or 0.90; default 0.85)",
    )
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

    from ingest.project_antonyms_campaign import (
        DEFAULT_FINAL_AUDIT_META,
        DEFAULT_MANIFEST_META,
        DEFAULT_MANIFEST_TSV,
        DEFAULT_NO_NATURAL_META,
        DEFAULT_NO_NATURAL_TSV,
        DEFAULT_UNRESOLVED_SAMPLE,
        CAMPAIGN_BASELINE_COMMIT,
    )

    def _add_campaign_flag(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--campaign",
            default="top5000",
            choices=("top5000", "len4"),
            help="Campaign id (default top5000; len4 = 四字缺直連)",
        )

    p_cf = sub.add_parser(
        "campaign-freeze",
        help="Freeze campaign manifest (top5000 or len4; exclude project_ant)",
    )
    _add_campaign_flag(p_cf)
    p_cf.add_argument("--db", default=str(ROOT / "lyrics.db"))
    p_cf.add_argument("--out-tsv", default=str(DEFAULT_MANIFEST_TSV))
    p_cf.add_argument("--out-meta", default=str(DEFAULT_MANIFEST_META))
    p_cf.add_argument("--no-natural", default=str(DEFAULT_NO_NATURAL_TSV))
    p_cf.add_argument(
        "--init-no-natural",
        action="store_true",
        default=True,
        help="Create empty no-natural TSV only if missing (default; never overwrite)",
    )
    p_cf.add_argument(
        "--no-init-no-natural",
        action="store_false",
        dest="init_no_natural",
        help="Do not create no-natural TSV even if missing",
    )
    p_cf.add_argument(
        "--force-reseed-no-natural",
        action="store_true",
        help="Overwrite existing no-natural ledger when inheriting (len4)",
    )
    p_cf.add_argument(
        "--baseline-commit",
        default="",
        help="Git sha1 baseline (top5000 defaults to fixed baseline; len4 defaults to HEAD)",
    )
    p_cf.add_argument(
        "--reference-seeds",
        default="",
        help="Optional seeds.txt; first batch must match exactly",
    )
    p_cf.set_defaults(func=cmd_campaign_freeze)

    p_cv = sub.add_parser("campaign-validate", help="Validate frozen campaign + no-natural")
    _add_campaign_flag(p_cv)
    p_cv.add_argument("--tsv", default=str(DEFAULT_MANIFEST_TSV))
    p_cv.add_argument("--meta", default=str(DEFAULT_MANIFEST_META))
    p_cv.add_argument("--no-natural", default=str(DEFAULT_NO_NATURAL_TSV))
    p_cv.add_argument("--accepted-tsv", default=str(DEFAULT_TSV))
    p_cv.add_argument(
        "--require-complete",
        action="store_true",
        help="Fail unless every campaign head is resolved (accepted or no-natural)",
    )
    p_cv.add_argument(
        "--unresolved-sample",
        type=int,
        default=DEFAULT_UNRESOLVED_SAMPLE,
        help=f"Max unresolved heads listed per batch (default {DEFAULT_UNRESOLVED_SAMPLE})",
    )
    p_cv.set_defaults(func=cmd_campaign_validate)

    p_cu = sub.add_parser(
        "campaign-unresolved",
        help="List unresolved campaign heads for one batch_index",
    )
    _add_campaign_flag(p_cu)
    p_cu.add_argument("--tsv", default=str(DEFAULT_MANIFEST_TSV))
    p_cu.add_argument("--meta", default=str(DEFAULT_MANIFEST_META))
    p_cu.add_argument("--no-natural", default=str(DEFAULT_NO_NATURAL_TSV))
    p_cu.add_argument("--accepted-tsv", default=str(DEFAULT_TSV))
    p_cu.add_argument("--batch-index", type=int, required=True)
    p_cu.add_argument("--out", default="", help="Optional plaintext heads file")
    p_cu.add_argument(
        "--list-heads",
        action="store_true",
        help="Include full unresolved head list in JSON (default: preview only)",
    )
    p_cu.add_argument("--preview", type=int, default=20)
    p_cu.set_defaults(func=cmd_campaign_unresolved)

    p_ns = sub.add_parser("no-natural-sample", help="Sample no-natural rows for quality gate")
    _add_campaign_flag(p_ns)
    p_ns.add_argument("--tsv", default=str(DEFAULT_NO_NATURAL_TSV))
    p_ns.add_argument("--manifest", default=str(DEFAULT_MANIFEST_TSV))
    p_ns.add_argument("--manifest-meta", default=str(DEFAULT_MANIFEST_META))
    p_ns.add_argument("--batch-id", default="", help="Optional filter to one batch_id")
    p_ns.add_argument("--seed", type=int, required=True)
    p_ns.add_argument("--out", required=True)
    p_ns.set_defaults(func=cmd_no_natural_sample)

    p_nv = sub.add_parser(
        "no-natural-validate",
        help="Fail-closed validate no-natural TSV + meta sample replay",
    )
    _add_campaign_flag(p_nv)
    p_nv.add_argument("--tsv", default=str(DEFAULT_NO_NATURAL_TSV))
    p_nv.add_argument("--meta", default=str(DEFAULT_NO_NATURAL_META))
    p_nv.add_argument("--manifest", default=str(DEFAULT_MANIFEST_TSV))
    p_nv.add_argument("--manifest-meta", default=str(DEFAULT_MANIFEST_META))
    p_nv.set_defaults(func=cmd_no_natural_validate)

    p_fs = sub.add_parser(
        "campaign-final-sample",
        help="Stratified final-audit sample (accepted + no-natural by batch_index)",
    )
    _add_campaign_flag(p_fs)
    p_fs.add_argument("--tsv", default=str(DEFAULT_MANIFEST_TSV))
    p_fs.add_argument("--meta", default=str(DEFAULT_MANIFEST_META))
    p_fs.add_argument("--no-natural", default=str(DEFAULT_NO_NATURAL_TSV))
    p_fs.add_argument("--accepted-tsv", default=str(DEFAULT_TSV))
    p_fs.add_argument("--seed", type=int, required=True)
    p_fs.add_argument("--out-accepted", default="", help="Optional accepted sample TSV")
    p_fs.add_argument(
        "--out-no-natural", default="", help="Optional no-natural sample TSV"
    )
    p_fs.add_argument(
        "--list-sampled",
        action="store_true",
        help="Include full sampled rows in JSON (default: strata stats only)",
    )
    p_fs.add_argument(
        "--require-complete",
        action="store_true",
        help="Fail unless campaign is structurally complete before sampling",
    )
    p_fs.set_defaults(func=cmd_campaign_final_sample)

    p_fv = sub.add_parser(
        "campaign-final-validate",
        help="Fail-closed validate campaign final audit meta + stratified replay",
    )
    _add_campaign_flag(p_fv)
    p_fv.add_argument("--tsv", default=str(DEFAULT_MANIFEST_TSV))
    p_fv.add_argument("--meta", default=str(DEFAULT_MANIFEST_META))
    p_fv.add_argument("--no-natural", default=str(DEFAULT_NO_NATURAL_TSV))
    p_fv.add_argument("--accepted-tsv", default=str(DEFAULT_TSV))
    p_fv.add_argument("--audit-meta", default=str(DEFAULT_FINAL_AUDIT_META))
    p_fv.add_argument(
        "--require-complete",
        action="store_true",
        help="Also require campaign-validate --require-complete",
    )
    p_fv.set_defaults(func=cmd_campaign_final_validate)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
