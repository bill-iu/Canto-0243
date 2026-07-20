"""P3 長尾：Essay 詞頻 rank (K0,K1] 終局覆蓋（CONTEXT § 詞性覆蓋母體 P3）。"""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from ingest.project_pos import (
    DEFAULT_META,
    DEFAULT_TSV,
    PosRow,
    load_meta,
    parse_project_pos_tsv,
    write_carrier,
)
from tools.campaigns.project_pos_cleanup import _rewrite_table
from tools.campaigns.project_pos_p0 import build_proposals, merge_proposals_into_ssot, write_proposals
from tools.campaigns.project_pos_p1 import load_essay_ranked

POS_DIR = ROOT / "data" / "pos"
P3_BODY = POS_DIR / "p3_mother_body.txt"
P3_PROPOSALS = POS_DIR / "proposals" / "p3_proposals.tsv"
AUDIT_DIR = POS_DIR / "audit"

# Essay ranks after P1 Top-5000 through Top-20000 (inclusive end rank)
DEFAULT_FROM_RANK = 5001
DEFAULT_TO_RANK = 20000


def collect_p3_slice(
    *,
    from_rank: int = DEFAULT_FROM_RANK,
    to_rank: int = DEFAULT_TO_RANK,
) -> List[Tuple[int, str, int]]:
    """Return (rank, literal, freq) for essay ranks [from_rank, to_rank]."""
    ranked = load_essay_ranked()
    out: List[Tuple[int, str, int]] = []
    for i, (lit, freq) in enumerate(ranked, start=1):
        if i < from_rank:
            continue
        if i > to_rank:
            break
        out.append((i, lit, freq))
    return out


def freeze_p3(
    path: Path = P3_BODY,
    *,
    from_rank: int = DEFAULT_FROM_RANK,
    to_rank: int = DEFAULT_TO_RANK,
) -> Path:
    rows = collect_p3_slice(from_rank=from_rank, to_rank=to_rank)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["rank\tliteral\tfreq"]
    for rank, lit, freq in rows:
        lines.append(f"{rank}\t{lit}\t{freq}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_p3_body(path: Path = P3_BODY) -> List[Tuple[int, str]]:
    if not path.is_file():
        freeze_p3(path)
    out: List[Tuple[int, str]] = []
    with path.open(encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh, delimiter="\t")
        for row in r:
            lit = (row.get("literal") or "").strip()
            try:
                rank = int(row.get("rank") or 0)
            except ValueError:
                rank = 0
            if lit:
                out.append((rank, lit))
    return out


def p3_status(*, body_path: Path = P3_BODY, tsv: Path = DEFAULT_TSV) -> dict:
    from tools.campaigns.project_pos_lexicon_prune import load_lexicon_literals

    body = load_p3_body(body_path)
    lits = [lit for _, lit in body]
    try:
        lex = load_lexicon_literals()
        in_lex = [lit for lit in lits if lit in lex]
        out_of_lex = len(lits) - len(in_lex)
    except FileNotFoundError:
        in_lex = lits
        out_of_lex = 0
    table = parse_project_pos_tsv(tsv)
    from tools.campaigns.project_pos_alias import covered_literals

    covered = covered_literals(table)
    tagged = [lit for lit in in_lex if lit in covered]
    in_table = [lit for lit in in_lex if lit in table]
    missing = [lit for lit in in_lex if lit not in covered]
    gate = sum(1 for lit in in_table if table[lit].gate_pos())
    undet = sum(1 for lit in in_table if table[lit].pos <= frozenset({"u"}))
    low = sum(
        1
        for lit in in_table
        if table[lit].trust() == "low" and bool(table[lit].formal_pos())
    )
    return {
        "phase": "p3",
        "from_rank": body[0][0] if body else None,
        "to_rank": body[-1][0] if body else None,
        "mother_body": len(lits),
        "mother_in_lexicon": len(in_lex),
        "mother_out_of_lexicon": out_of_lex,
        "tagged": len(tagged),
        "missing": len(missing),
        "gate_formal": gate,
        "undetermined_only": undet,
        "low_draft_formal": low,
        "coverage": round(len(tagged) / len(in_lex), 4) if in_lex else 0.0,
        "gate_coverage": round(gate / len(in_lex), 4) if in_lex else 0.0,
        "p3_complete": len(missing) == 0 and len(in_lex) > 0,
    }


def run_coverage(
    *,
    from_rank: int = DEFAULT_FROM_RANK,
    to_rank: int = DEFAULT_TO_RANK,
) -> dict:
    """Freeze → propose missing → merge safe slices → fill u for missing."""
    freeze_p3(from_rank=from_rank, to_rank=to_rank)
    body = load_p3_body()
    lits = [lit for _, lit in body]
    table = parse_project_pos_tsv()
    missing = [lit for lit in lits if lit not in table]

    # Proposals only for not-yet-in-SSOT (build_proposals also skips existing)
    rows = build_proposals(missing, existing=set(table.keys()))
    write_proposals(rows, P3_PROPOSALS)
    by_conf = Counter(r["confidence"] for r in rows)

    def _stamp(rs: List[dict]) -> List[dict]:
        out = []
        for r in rs:
            note = (r.get("note") or "").strip()
            if "p3" not in note.split(";"):
                note = f"{note};p3" if note else "p3"
            out.append({**r, "note": note})
        return out

    merges = {}
    all_rows = rows
    merges["high-heuristic"] = merge_proposals_into_ssot(
        _stamp([r for r in all_rows if r.get("confidence") == "high" and r.get("source") == "heuristic"]),
        skip_undetermined=True,
    )
    for pref in ("len4-noun-heuristic", "cow-multi", "verb-suffix", "prefix-passive"):
        merges[pref] = merge_proposals_into_ssot(
            _stamp([r for r in all_rows if (r.get("note") or "").startswith(pref)]),
            skip_undetermined=True,
        )
    merges["cow-single"] = merge_proposals_into_ssot(
        _stamp([r for r in all_rows if (r.get("note") or "").startswith("cow-single")]),
        skip_undetermined=True,
    )
    merges["fallback-u"] = merge_proposals_into_ssot(
        _stamp([r for r in all_rows if r.get("confidence") == "low"]),
        skip_undetermined=False,
    )
    write_carrier()
    st = p3_status()
    meta = load_meta()
    meta["version"] = "0.3.0"
    meta["p3"] = {
        **st,
        "proposed": len(rows),
        "by_confidence": dict(by_conf),
        "merges": merges,
    }
    DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"proposed": len(rows), "by_confidence": dict(by_conf), "merges": merges, "status": st}


def sample_size_for(n: int) -> int:
    if n <= 0:
        return 0
    return min(n, max(50, math.ceil(n * 0.05)))


def write_gate_sample(*, seed: int, round_id: int) -> dict:
    """Sample newly relevant: P3 body ∩ gate_pos for quality (if any)."""
    body = {lit for _, lit in load_p3_body()}
    table = parse_project_pos_tsv()
    universe = sorted(lit for lit in body if lit in table and table[lit].gate_pos())
    n = sample_size_for(len(universe))
    if n == 0:
        return {"round": round_id, "universe": 0, "sample_n": 0, "skipped": True}
    rng = random.Random(seed)
    sample = sorted(rng.sample(universe, n)) if n < len(universe) else universe
    rank = {lit: r for r, lit in load_p3_body()}
    out = AUDIT_DIR / f"p3_gate_quality_r{round_id}.tsv"
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    header = [
        "literal",
        "pos",
        "family",
        "voice",
        "note",
        "trust",
        "stratum",
        "rank",
        "verdict",
        "fix_pos",
        "fix_family",
        "fix_voice",
        "audit_note",
    ]
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=header, delimiter="\t", lineterminator="\n")
        w.writeheader()
        for lit in sample:
            r = table[lit]
            w.writerow(
                {
                    "literal": lit,
                    "pos": ",".join(sorted(r.pos)),
                    "family": r.family,
                    "voice": r.voice,
                    "note": r.note,
                    "trust": r.trust(),
                    "stratum": "p3|gate",
                    "rank": rank.get(lit, ""),
                    "verdict": "",
                    "fix_pos": "",
                    "fix_family": "",
                    "fix_voice": "",
                    "audit_note": "",
                }
            )
    meta = {
        "round": round_id,
        "seed": seed,
        "universe": len(universe),
        "sample_n": n,
        "out": str(out),
        "threshold": 0.90,
    }
    out.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return meta


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_p3")
    sub = p.add_subparsers(dest="cmd", required=True)
    fr = sub.add_parser("freeze")
    fr.add_argument("--from-rank", type=int, default=DEFAULT_FROM_RANK)
    fr.add_argument("--to-rank", type=int, default=DEFAULT_TO_RANK)
    sub.add_parser("status")
    rn = sub.add_parser("run", help="freeze + fill missing SSOT rows for long tail")
    rn.add_argument("--from-rank", type=int, default=DEFAULT_FROM_RANK)
    rn.add_argument("--to-rank", type=int, default=DEFAULT_TO_RANK)
    sm = sub.add_parser("sample-gate", help="sample P3∩gate for quality audit")
    sm.add_argument("--seed", type=int, default=20260719)
    sm.add_argument("--round", type=int, default=1)
    args = p.parse_args(argv)
    if args.cmd == "freeze":
        path = freeze_p3(from_rank=args.from_rank, to_rank=args.to_rank)
        print(json.dumps({"out": str(path), "n": len(load_p3_body())}, ensure_ascii=False))
        return 0
    if args.cmd == "status":
        print(json.dumps(p3_status(), ensure_ascii=False))
        return 0
    if args.cmd == "run":
        print(json.dumps(run_coverage(from_rank=args.from_rank, to_rank=args.to_rank), ensure_ascii=False))
        return 0
    if args.cmd == "sample-gate":
        print(json.dumps(write_gate_sample(seed=args.seed, round_id=args.round), ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
