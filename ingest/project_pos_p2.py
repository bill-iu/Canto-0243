"""P2 語彙族・熟語傘：len4 固定語候選（CONTEXT § 語彙族 / 詞性覆蓋母體 P2）。"""
from __future__ import annotations

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
    PosRow,
    load_meta,
    parse_project_pos_tsv,
    write_carrier,
)
from ingest.project_pos_cleanup import _rewrite_table
from ingest.project_pos_p0 import _LEN4_N_SUFFIXES, _looks_numeral, load_p0_mother_body
from ingest.project_pos_p1 import load_p1_mother_body

ROOT = Path(__file__).resolve().parents[1]
POS_DIR = ROOT / "data" / "pos"
P2_BODY = POS_DIR / "p2_mother_body.txt"
P2_PROPOSE = POS_DIR / "proposals" / "p2_idiom_proposals.tsv"
AUDIT_DIR = POS_DIR / "audit"
DEFAULT_SEED = 20260719


def _is_ordinary_np(lit: str) -> bool:
    """Ordinary compound NP — not 熟語 (suffix table only; 之-forms may be 熟語)."""
    if len(lit) != 4:
        return False
    return any(lit.endswith(s) for s in _LEN4_N_SUFFIXES)


def idiom_pattern(lit: str) -> Optional[str]:
    """Return pattern id if looks like fixed 4-char expression, else None."""
    if len(lit) != 4 or _looks_numeral(lit) or _is_ordinary_np(lit):
        return None
    a, b, c, d = lit[0], lit[1], lit[2], lit[3]
    # 統購統銷／統A統B 政策術語 — 唔入 ABAC
    if a == c == "統":
        return None
    if a == b and c == d:
        return "AABB"
    if a == c and b == d:
        return "ABAB"
    if a == c and b != d:
        return "ABAC"
    if a == b and c != d:
        return "AABC"
    if a == "不" and c == "不":
        return "不X不Y"
    if a == "一" and c in "一二三四無有":
        return "一X?Y"
    if a in "有無" and c in "有無不":
        return "有無對"
    if b == "之" or c == "之":
        # 在此之後／自此以後 — transparent temporal, not 熟語
        if lit.startswith(("在此", "自此", "從此", "至此")) and lit.endswith(("之後", "以後", "之前", "以前")):
            return None
        return "之字格"
    if a == d and b != c:
        return "AxxA"
    # ABAC technical parallel (電解電容): both halves look like tech/chemical stems
    if a == c and b != d:
        tech = "電液氣光磁熱力壓容阻感晶體膜管"
        if b in tech and d in tech:
            return None
    return None


def collect_p2_candidates() -> List[Tuple[str, str]]:
    """(literal, pattern) for P0∪P1 len4 matching idiom patterns."""
    table = parse_project_pos_tsv()
    scope = set(load_p0_mother_body()) | set(load_p1_mother_body())
    out: List[Tuple[str, str]] = []
    for lit in sorted(scope):
        if len(lit) != 4 or lit not in table:
            continue
        pat = idiom_pattern(lit)
        if pat:
            out.append((lit, pat))
    return out


def freeze_p2(path: Path = P2_BODY) -> Path:
    rows = collect_p2_candidates()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["literal\tpattern\talready_idiom"]
    table = parse_project_pos_tsv()
    for lit, pat in rows:
        already = "1" if table[lit].family == "idiom" else "0"
        lines.append(f"{lit}\t{pat}\t{already}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_p2_body(path: Path = P2_BODY) -> List[Tuple[str, str]]:
    if not path.is_file():
        freeze_p2(path)
    out: List[Tuple[str, str]] = []
    with path.open(encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh, delimiter="\t")
        for row in r:
            lit = (row.get("literal") or "").strip()
            pat = (row.get("pattern") or "").strip()
            if lit:
                out.append((lit, pat))
    return out


def apply_idiom_family(
    candidates: Sequence[Tuple[str, str]],
    *,
    only_missing: bool = True,
) -> dict:
    table = parse_project_pos_tsv()
    added = 0
    skipped = 0
    for lit, pat in candidates:
        row = table.get(lit)
        if not row:
            skipped += 1
            continue
        if only_missing and row.family == "idiom":
            skipped += 1
            continue
        note = row.note
        bits = [b for b in (f"p2-idiom:{pat}", "p2-idiom-heuristic") if b]
        have = {t.strip() for t in note.split(";") if t.strip()}
        for b in bits:
            if b not in have:
                note = f"{note};{b}" if note else b
                have.add(b)
        # family display needs high trust — add review for pattern-based high-confidence patterns
        high_pat = pat in {"AABB", "ABAB", "不X不Y", "一X?Y", "有無對", "之字格"}
        if high_pat and "review" not in have:
            note = f"{note};review"
            have.add("review")
        table[lit] = PosRow(
            literal=lit,
            pos=row.pos,
            family="idiom",
            voice=row.voice,
            note=note,
        )
        added += 1
    _rewrite_table(table)
    write_carrier()
    return {"tagged": added, "skipped": skipped}


def p2_status() -> dict:
    body = load_p2_body()
    table = parse_project_pos_tsv()
    lits = [lit for lit, _ in body]
    tagged = sum(1 for lit in lits if table.get(lit) and table[lit].family == "idiom")
    displayable = sum(
        1
        for lit in lits
        if table.get(lit)
        and table[lit].family == "idiom"
        and table[lit].trust() == "high"
    )
    by_pat: Counter = Counter(pat for _, pat in body)
    return {
        "phase": "p2",
        "mother_body": len(lits),
        "idiom_tagged": tagged,
        "idiom_display_high": displayable,
        "coverage": round(tagged / len(lits), 4) if lits else 0.0,
        "by_pattern": dict(by_pat),
        # complete = mother frozen + nearly all tagged (audit may clear a few BAD)
        "p2_complete": len(lits) > 0 and tagged / len(lits) >= 0.94,
    }


def sample_size_for(n: int) -> int:
    if n <= 0:
        return 0
    return min(n, max(50, math.ceil(n * 0.05)))


def write_quality_sample(*, seed: int = DEFAULT_SEED, round_id: int = 1) -> dict:
    table = parse_project_pos_tsv()
    body = load_p2_body()
    # universe: just tagged as idiom in p2 body
    universe = [lit for lit, _ in body if table.get(lit) and table[lit].family == "idiom"]
    n = sample_size_for(len(universe))
    rng = random.Random(seed)
    sample = sorted(rng.sample(universe, n)) if n < len(universe) else sorted(universe)
    out = AUDIT_DIR / f"p2_idiom_quality_r{round_id}.tsv"
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    header = [
        "literal",
        "pos",
        "family",
        "voice",
        "note",
        "trust",
        "pattern",
        "verdict",
        "fix_family",
        "audit_note",
    ]
    pat_map = {lit: pat for lit, pat in body}
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
                    "pattern": pat_map.get(lit, ""),
                    "verdict": "",
                    "fix_family": "",
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


def apply_family_verdicts(path: Path, *, dry_run: bool = False) -> dict:
    """OK/SOFT keep idiom; BAD with fix_family empty clears family."""
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    ok = soft = bad = 0
    clears: List[str] = []
    for r in rows:
        v = (r.get("verdict") or "").strip().upper()
        if v in ("OK", "PASS"):
            ok += 1
        elif v in ("SOFT", "SOFT-OK"):
            soft += 1
        elif v in ("BAD", "FIX"):
            bad += 1
            ff = (r.get("fix_family") or "").strip()
            if ff == "" or ff.lower() in ("none", "-", "empty", "普通"):
                clears.append((r.get("literal") or "").strip())
        else:
            pass
    n = ok + soft + bad
    rate = (ok + soft) / n if n else 0.0
    result = {
        "audited": n,
        "ok": ok,
        "soft": soft,
        "bad": bad,
        "ok_rate": round(rate, 4),
        "pass_90": rate > 0.90 if n else False,
        "clears": len(clears),
        "dry_run": dry_run,
    }
    if not dry_run and clears:
        table = parse_project_pos_tsv()
        for lit in clears:
            if not lit or lit not in table:
                continue
            row = table[lit]
            note = row.note
            if "p2-audit-clear" not in note:
                note = f"{note};p2-audit-clear" if note else "p2-audit-clear"
            table[lit] = PosRow(
                literal=lit,
                pos=row.pos,
                family="",
                voice=row.voice,
                note=note,
            )
        _rewrite_table(table)
        write_carrier()
    return result


def cmd_freeze(_: argparse.Namespace) -> int:
    path = freeze_p2()
    st = p2_status()
    print(json.dumps({"out": str(path), **{k: st[k] for k in ("mother_body", "by_pattern")}}, ensure_ascii=False))
    return 0


def cmd_apply(_: argparse.Namespace) -> int:
    body = load_p2_body()
    stats = apply_idiom_family(body, only_missing=True)
    st = p2_status()
    meta = load_meta()
    meta["version"] = "0.2.0"
    meta["p2"] = {**st, "apply": stats}
    DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"apply": stats, "status": st}, ensure_ascii=False))
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    if not P2_BODY.is_file():
        freeze_p2()
    st = p2_status()
    print(json.dumps(st, ensure_ascii=False))
    return 0


def cmd_sample(args: argparse.Namespace) -> int:
    meta = write_quality_sample(seed=int(args.seed), round_id=int(args.round))
    print(json.dumps(meta, ensure_ascii=False))
    return 0


def cmd_audit_apply(args: argparse.Namespace) -> int:
    result = apply_family_verdicts(Path(args.verdicts), dry_run=bool(args.dry_run))
    if not args.dry_run:
        st = p2_status()
        meta = load_meta()
        meta["p2"] = {**(meta.get("p2") or {}), **st, "last_audit": result}
        DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    freeze_p2()
    body = load_p2_body()
    stats = apply_idiom_family(body, only_missing=True)
    sample_meta = write_quality_sample(seed=int(args.seed), round_id=1)
    st = p2_status()
    meta = load_meta()
    meta["version"] = "0.2.0"
    meta["p2"] = {**st, "apply": stats, "sample_r1": sample_meta}
    DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"apply": stats, "status": st, "sample": sample_meta}, ensure_ascii=False))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_p2")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("freeze", help="freeze pattern-based 熟語 mother body")
    sub.add_parser("apply", help="set family=idiom on mother body")
    sub.add_parser("status")
    s = sub.add_parser("sample", help="quality sample of tagged idioms")
    s.add_argument("--seed", type=int, default=DEFAULT_SEED)
    s.add_argument("--round", type=int, default=1)
    a = sub.add_parser("audit-apply", help="apply BAD clears from verdict TSV")
    a.add_argument("--verdicts", required=True)
    a.add_argument("--dry-run", action="store_true")
    r = sub.add_parser("run", help="freeze+apply+sample r1")
    r.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = p.parse_args(argv)
    if args.cmd == "freeze":
        return cmd_freeze(args)
    if args.cmd == "apply":
        return cmd_apply(args)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "sample":
        return cmd_sample(args)
    if args.cmd == "audit-apply":
        return cmd_audit_apply(args)
    if args.cmd == "run":
        return cmd_run(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
