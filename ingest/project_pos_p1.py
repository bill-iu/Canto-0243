"""P1 詞性覆蓋：Essay 詞頻 Top-K 母體（CONTEXT § 詞性覆蓋母體 P1）。"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from app.lexicon.essay_index import DEFAULT_ESSAY_PATH
from ingest.project_pos import DEFAULT_META, DEFAULT_TSV, load_meta, parse_project_pos_tsv, write_carrier
from ingest.project_pos_p0 import (
    P0_PROPOSALS,
    build_proposals,
    merge_proposals_into_ssot,
    read_proposals,
    write_proposals,
)

ROOT = Path(__file__).resolve().parents[1]
POS_DIR = ROOT / "data" / "pos"
P1_BODY = POS_DIR / "p1_mother_body.txt"
P1_PROPOSALS = POS_DIR / "proposals" / "p1_proposals.tsv"
DEFAULT_K = 5000


def load_essay_ranked(path: Path = DEFAULT_ESSAY_PATH) -> List[Tuple[str, int]]:
    """Return (literal, freq) sorted by freq desc, then literal."""
    rows: List[Tuple[str, int]] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            lit = parts[0].strip()
            try:
                freq = int(parts[1].strip())
            except ValueError:
                continue
            if lit and freq >= 0:
                rows.append((lit, freq))
    rows.sort(key=lambda x: (-x[1], x[0]))
    return rows


def collect_p1_mother_body(k: int = DEFAULT_K, essay_path: Path = DEFAULT_ESSAY_PATH) -> List[Tuple[str, int]]:
    ranked = load_essay_ranked(essay_path)
    return ranked[: max(0, k)]


def freeze_p1_mother_body(
    path: Path = P1_BODY,
    *,
    k: int = DEFAULT_K,
    essay_path: Path = DEFAULT_ESSAY_PATH,
) -> Path:
    body = collect_p1_mother_body(k, essay_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # rank\tliteral\tfreq
    lines = ["rank\tliteral\tfreq"]
    for i, (lit, freq) in enumerate(body, start=1):
        lines.append(f"{i}\t{lit}\t{freq}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_p1_mother_body(path: Path = P1_BODY) -> List[str]:
    if not path.is_file():
        freeze_p1_mother_body(path)
    out: List[str] = []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for row in reader:
            lit = (row.get("literal") or "").strip()
            if lit:
                out.append(lit)
    return out


def p1_status(*, body_path: Path = P1_BODY, tsv: Path = DEFAULT_TSV) -> dict:
    from ingest.project_pos_lexicon_prune import load_lexicon_literals

    body = load_p1_mother_body(body_path)
    # Coverage only over mother ∩ 詞庫 (POS SSOT is lexicon-only)
    try:
        lex = load_lexicon_literals()
        body_set = {lit for lit in body if lit in lex}
        out_of_lex = len(body) - len(body_set)
    except FileNotFoundError:
        body_set = set(body)
        out_of_lex = 0
    table = parse_project_pos_tsv(tsv)
    tagged = body_set & set(table.keys())
    gate_formal = {lit for lit in tagged if table[lit].gate_pos()}
    undetermined = {lit for lit in tagged if table[lit].pos <= frozenset({"u"})}
    low_draft = {
        lit
        for lit in tagged
        if table[lit].trust() == "low" and table[lit].formal_pos() and lit not in undetermined
    }
    missing = body_set - set(table.keys())
    complete = len(missing) == 0 and len(body_set) > 0
    return {
        "phase": "p1",
        "k": len(body),
        "mother_body": len(body),
        "mother_in_lexicon": len(body_set),
        "mother_out_of_lexicon": out_of_lex,
        "tagged": len(tagged),
        "gate_formal": len(gate_formal),
        "low_draft_formal": len(low_draft),
        "undetermined_only": len(undetermined),
        "missing": len(missing),
        "coverage": round(len(tagged) / len(body_set), 4) if body_set else 0.0,
        "gate_coverage": round(len(gate_formal) / len(body_set), 4) if body_set else 0.0,
        "p1_complete": complete,
    }


def update_meta_p1(status: dict, *, meta_path: Path = DEFAULT_META, k: int = DEFAULT_K) -> None:
    meta = load_meta(meta_path)
    meta["p1"] = {
        "k": k,
        "mother_body": status["mother_body"],
        "tagged": status["tagged"],
        "gate_formal": status["gate_formal"],
        "missing": status["missing"],
        "coverage": status["coverage"],
        "gate_coverage": status["gate_coverage"],
        "complete": status["p1_complete"],
    }
    if "version" in meta:
        # bump patch when p1 lands
        pass
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_freeze(args: argparse.Namespace) -> int:
    k = int(args.k or DEFAULT_K)
    path = freeze_p1_mother_body(k=k)
    body = load_p1_mother_body(path)
    print(json.dumps({"out": str(path), "k": k, "literals": len(body)}, ensure_ascii=False))
    return 0


def cmd_propose(args: argparse.Namespace) -> int:
    body = load_p1_mother_body()
    rows = build_proposals(body)  # skips already in SSOT
    if args.min_confidence == "high":
        rows = [r for r in rows if r["confidence"] == "high"]
    elif args.min_confidence == "medium":
        rows = [r for r in rows if r["confidence"] in ("high", "medium")]
    out = write_proposals(rows, Path(args.out) if args.out else P1_PROPOSALS)
    by: Dict[str, int] = {}
    for r in rows:
        by[r["confidence"]] = by.get(r["confidence"], 0) + 1
    print(json.dumps({"out": str(out), "proposals": len(rows), "by_confidence": by}, ensure_ascii=False))
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    path = Path(args.proposals) if args.proposals else P1_PROPOSALS
    rows = read_proposals(path)
    conf: Optional[Set[str]] = None
    if args.only_confidence:
        conf = {c.strip() for c in args.only_confidence.split(",") if c.strip()}
    if args.only_source:
        allow = {s.strip() for s in args.only_source.split(",") if s.strip()}
        rows = [r for r in rows if (r.get("source") or "").strip() in allow]
    if args.only_note_prefix:
        pref = args.only_note_prefix
        rows = [r for r in rows if (r.get("note") or "").startswith(pref)]
    # stamp note with p1 so provenance is clear
    stamped = []
    for r in rows:
        note = (r.get("note") or "").strip()
        if "p1" not in note:
            note = f"{note};p1" if note else "p1"
        stamped.append({**r, "note": note})
    stats = merge_proposals_into_ssot(
        stamped,
        only_confidence=conf,
        skip_undetermined=bool(args.skip_u),
        dry_run=bool(args.dry_run),
    )
    if not args.dry_run and stats["added"]:
        write_carrier()
    st = p1_status()
    update_meta_p1(st, k=st["k"])
    print(json.dumps({"merge": stats, "status": st}, ensure_ascii=False))
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    if not P1_BODY.is_file():
        freeze_p1_mother_body()
    st = p1_status()
    update_meta_p1(st, k=st["k"])
    print(json.dumps(st, ensure_ascii=False))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """freeze → propose → merge safe slices → fill u → status."""
    k = int(args.k or DEFAULT_K)
    freeze_p1_mother_body(k=k)
    body = load_p1_mother_body()
    rows = build_proposals(body)
    write_proposals(rows, P1_PROPOSALS)
    by: Dict[str, int] = {}
    for r in rows:
        by[r["confidence"]] = by.get(r["confidence"], 0) + 1

    def _merge(filter_rows: List[dict], *, skip_u: bool = True) -> dict:
        stamped = []
        for r in filter_rows:
            note = (r.get("note") or "").strip()
            if "p1" not in note:
                note = f"{note};p1" if note else "p1"
            stamped.append({**r, "note": note})
        return merge_proposals_into_ssot(stamped, skip_undetermined=skip_u, dry_run=False)

    all_rows = read_proposals(P1_PROPOSALS)
    results = []
    # high heuristic
    results.append(
        (
            "high-heuristic",
            _merge([r for r in all_rows if r.get("confidence") == "high" and r.get("source") == "heuristic"]),
        )
    )
    for pref in ("len4-noun-heuristic", "cow-multi", "verb-suffix", "prefix-passive"):
        results.append(
            (
                pref,
                _merge([r for r in all_rows if (r.get("note") or "").startswith(pref)]),
            )
        )
    # cow-single as low-trust draft (keep in SSOT, not gate)
    results.append(
        (
            "cow-single",
            _merge([r for r in all_rows if (r.get("note") or "").startswith("cow-single")]),
        )
    )
    # remainder u
    results.append(
        (
            "fallback-u",
            _merge([r for r in all_rows if r.get("confidence") == "low"], skip_u=False),
        )
    )
    write_carrier()
    st = p1_status()
    update_meta_p1(st, k=k)
    # bump meta version
    meta = load_meta()
    meta["version"] = "0.1.2"
    meta["p1"] = meta.get("p1") or {}
    DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "k": k,
                "proposed": len(all_rows),
                "by_confidence": by,
                "merges": {name: stats for name, stats in results},
                "status": st,
            },
            ensure_ascii=False,
        )
    )
    return 0 if st["p1_complete"] else 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_p1")
    sub = p.add_subparsers(dest="cmd", required=True)
    fr = sub.add_parser("freeze", help="freeze Essay Top-K mother body")
    fr.add_argument("--k", type=int, default=DEFAULT_K)
    pr = sub.add_parser("propose", help="proposals for untagged P1 body")
    pr.add_argument("--out", default="")
    pr.add_argument("--min-confidence", choices=("low", "medium", "high"), default="low")
    mg = sub.add_parser("merge", help="merge P1 proposals into SSOT")
    mg.add_argument("--proposals", default="")
    mg.add_argument("--only-confidence", default="")
    mg.add_argument("--only-source", default="")
    mg.add_argument("--only-note-prefix", default="")
    mg.add_argument("--skip-u", action="store_true")
    mg.add_argument("--dry-run", action="store_true")
    sub.add_parser("status", help="P1 coverage report")
    rn = sub.add_parser("run", help="freeze+propose+merge all slices (one shot)")
    rn.add_argument("--k", type=int, default=DEFAULT_K)
    args = p.parse_args(argv)
    if args.cmd == "freeze":
        return cmd_freeze(args)
    if args.cmd == "propose":
        return cmd_propose(args)
    if args.cmd == "merge":
        return cmd_merge(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "run":
        return cmd_run(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
