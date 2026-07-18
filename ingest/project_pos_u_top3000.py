"""Essay-frequency top-N still-u repair campaign (default N=3000)."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from ingest.project_pos import (
    DEFAULT_META,
    PosRow,
    load_meta,
    parse_project_pos_tsv,
    write_carrier,
)
from ingest.project_pos_audit import sample_size_for, upsert_ssot_rows
from ingest.project_pos_cleanup import _rewrite_table
from ingest.project_pos_p0 import load_cow_pos_map, propose_for_literal
from ingest.project_pos_p1 import load_essay_ranked
from ingest.project_pos_u_repair import propose_u_fix

ROOT = Path(__file__).resolve().parents[1]
POS_DIR = ROOT / "data" / "pos"
BODY = POS_DIR / "u_top3000_mother_body.txt"
PROPOSALS = POS_DIR / "proposals" / "u_top3000_proposals.tsv"
AUDIT_DIR = POS_DIR / "audit"
DEFAULT_N = 3000


def collect_essay_top_u(n: int = DEFAULT_N) -> List[Tuple[int, str, int]]:
    """(essay_rank_among_u, literal, freq) for first n essay-ordered still-u."""
    table = parse_project_pos_tsv()
    u_set = {lit for lit, r in table.items() if r.pos <= frozenset({"u"})}
    out: List[Tuple[int, str, int]] = []
    for lit, freq in load_essay_ranked():
        if lit not in u_set:
            continue
        out.append((len(out) + 1, lit, freq))
        if len(out) >= n:
            break
    return out


def freeze_body(path: Path = BODY, *, n: int = DEFAULT_N) -> Path:
    rows = collect_essay_top_u(n)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["rank_u\tliteral\tfreq"]
    for rank, lit, freq in rows:
        lines.append(f"{rank}\t{lit}\t{freq}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_body(path: Path = BODY) -> List[str]:
    if not path.is_file():
        freeze_body(path)
    out: List[str] = []
    with path.open(encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh, delimiter="\t")
        for row in r:
            lit = (row.get("literal") or "").strip()
            if lit:
                out.append(lit)
    return out


def build_top_u_proposals(lits: Sequence[str]) -> List[dict]:
    cow = load_cow_pos_map()
    rows: List[dict] = []
    for lit in lits:
        # 1) dedicated u-repair map / patterns
        prop = propose_u_fix(lit)
        if prop:
            pos, tag = prop
            rows.append(
                {
                    "literal": lit,
                    "pos": pos,
                    "family": "",
                    "voice": "",
                    "note": f"u-top3000;{tag}",
                    "source": "u-repair",
                    "confidence": "high" if tag == "canto-u-map" else "medium",
                }
            )
            continue
        # 2) general propose_for_literal (COW / heuristics)
        p = propose_for_literal(lit, cow=cow)
        if p and p[0] != "u":
            pos, fam, voice, note, src, conf = p
            rows.append(
                {
                    "literal": lit,
                    "pos": pos,
                    "family": fam,
                    "voice": voice,
                    "note": f"u-top3000;{note}",
                    "source": src,
                    "confidence": conf if conf != "high" or src != "cow" else "medium",
                }
            )
            continue
        # 3) leave for later — write explicit u keep? skip
    return rows


def apply_proposals(
    proposals: Sequence[dict],
    *,
    only_confidence: Optional[set[str]] = None,
    promote_review: bool = True,
) -> dict:
    """Upsert over existing u rows (overwrite pos)."""
    table = parse_project_pos_tsv()
    fixes: List[dict] = []
    skipped = 0
    for r in proposals:
        lit = (r.get("literal") or "").strip()
        if not lit or lit not in table:
            skipped += 1
            continue
        conf = (r.get("confidence") or "").strip().lower()
        if only_confidence and conf not in only_confidence:
            skipped += 1
            continue
        if table[lit].pos > frozenset({"u"}):
            skipped += 1
            continue
        pos = (r.get("pos") or "").strip()
        if not pos or pos == "u":
            skipped += 1
            continue
        note = (r.get("note") or "").strip()
        if promote_review and "review" not in note.split(";"):
            # medium auto: no review unless high confidence map
            if conf == "high":
                note = f"{note};review" if note else "review"
        fixes.append(
            {
                "literal": lit,
                "fix_pos": pos,
                "fix_family": (r.get("family") or table[lit].family or "").strip(),
                "fix_voice": (r.get("voice") or table[lit].voice or "").strip(),
                "note": note,
                "audit_note": "u-top3000",
            }
        )
    # high with review → gate; medium without review may stay medium if cow-multi
    # Force high for canto map via review; for medium cow use trust from note
    up = upsert_ssot_rows(fixes, note_suffix="u-top3000")
    write_carrier()
    return {"upsert": up, "fixes": len(fixes), "skipped": skipped}


def status(*, n: int = DEFAULT_N) -> dict:
    body = load_body()
    table = parse_project_pos_tsv()
    still_u = [lit for lit in body if lit in table and table[lit].pos <= frozenset({"u"})]
    gated = [lit for lit in body if lit in table and table[lit].gate_pos()]
    formal = [
        lit
        for lit in body
        if lit in table and table[lit].formal_pos() and table[lit].pos > frozenset({"u"})
    ]
    return {
        "n": len(body),
        "still_u": len(still_u),
        "formal_any": len(formal),
        "gate_formal": len(gated),
        "u_rate": round(len(still_u) / len(body), 4) if body else 0.0,
        "gate_rate": round(len(gated) / len(body), 4) if body else 0.0,
        "complete_formal": len(still_u) == 0,
    }


def write_proposals(rows: Sequence[dict], path: Path = PROPOSALS) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = ("literal", "pos", "family", "voice", "note", "source", "confidence")
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(header), delimiter="\t", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})
    return path


def sample_gate_new(*, seed: int = 20260728, round_id: int = 1) -> dict:
    """Sample body∩gate that have u-top3000 note for quality."""
    body = set(load_body())
    table = parse_project_pos_tsv()
    universe = sorted(
        lit
        for lit in body
        if lit in table
        and table[lit].gate_pos()
        and "u-top3000" in table[lit].note
    )
    n = sample_size_for(len(universe))
    if n == 0:
        # fall back to any gate in body newly formal
        universe = sorted(lit for lit in body if lit in table and table[lit].gate_pos())
        n = sample_size_for(len(universe))
    rng = random.Random(seed)
    sample = sorted(rng.sample(universe, n)) if n < len(universe) else sorted(universe)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    out = AUDIT_DIR / f"u_top3000_gate_r{round_id}.tsv"
    header = [
        "literal",
        "pos",
        "family",
        "voice",
        "note",
        "trust",
        "stratum",
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
                    "stratum": "u-top3000|gate",
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


def run(*, n: int = DEFAULT_N) -> dict:
    freeze_body(n=n)
    body = load_body()
    props = build_top_u_proposals(body)
    write_proposals(props)
    by = Counter(r["confidence"] for r in props)
    # apply high first (with review), then medium (cow/heuristic patterns)
    # For medium: add review only for non-cow to avoid 13% cow-single pollution
    high = [r for r in props if r["confidence"] == "high"]
    med_safe = [
        r
        for r in props
        if r["confidence"] == "medium" and r.get("source") != "cow"
    ]
    med_cow = [
        r
        for r in props
        if r["confidence"] == "medium" and r.get("source") == "cow"
    ]
    # high + medium safe → review
    for r in high + med_safe:
        if "review" not in (r.get("note") or ""):
            r["note"] = f"{r.get('note')};review"
    # cow-single → low trust (no review); cow-multi keep medium without forcing review
    a1 = apply_proposals(high + med_safe, promote_review=False)
    a2 = apply_proposals(med_cow, promote_review=False)
    st = status(n=n)
    sample = sample_gate_new(seed=20260728, round_id=1)
    meta = load_meta()
    meta["version"] = "0.3.4"
    meta["u_top3000"] = {
        "n": n,
        "proposed": len(props),
        "by_confidence": dict(by),
        "apply_high_safe": a1,
        "apply_cow": a2,
        "status": st,
        "sample_r1": sample,
    }
    DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"proposed": len(props), "by_confidence": dict(by), "status": st, "sample": sample}


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_u_top3000")
    sub = p.add_subparsers(dest="cmd", required=True)
    fr = sub.add_parser("freeze")
    fr.add_argument("-n", type=int, default=DEFAULT_N)
    sub.add_parser("status")
    rn = sub.add_parser("run")
    rn.add_argument("-n", type=int, default=DEFAULT_N)
    sm = sub.add_parser("sample-gate")
    sm.add_argument("--seed", type=int, default=20260728)
    sm.add_argument("--round", type=int, default=1)
    args = p.parse_args(argv)
    if args.cmd == "freeze":
        path = freeze_body(n=args.n)
        print(json.dumps({"out": str(path), "n": len(load_body())}, ensure_ascii=False))
        return 0
    if args.cmd == "status":
        print(json.dumps(status(), ensure_ascii=False))
        return 0
    if args.cmd == "run":
        print(json.dumps(run(n=args.n), ensure_ascii=False))
        return 0
    if args.cmd == "sample-gate":
        print(json.dumps(sample_gate_new(seed=args.seed, round_id=args.round), ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
