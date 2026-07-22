"""詞性清單分層抽樣審核（P0/P1）；sample_size 鏡射 campaign 公式。"""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import argparse
import csv
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from ingest.project_pos import (
    DEFAULT_META,
    DEFAULT_TSV,
    PosRow,
    ProjectPosError,
    load_meta,
    parse_project_pos_tsv,
    split_pos,
    write_carrier,
)

POS_DIR = ROOT / "data" / "pos"
AUDIT_DIR = POS_DIR / "audit"

SAMPLE_HEADER = (
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
)


def sample_size_for(n: int) -> int:
    if n <= 0:
        return 0
    return min(n, max(50, math.ceil(n * 0.05)))


def stratum_of(row: PosRow) -> str:
    t = row.trust()
    if row.pos <= frozenset({"u"}):
        return f"{t}|u"
    if row.gate_pos():
        return f"{t}|gate"
    if row.formal_pos():
        return f"{t}|draft"
    return f"{t}|other"


def load_body_literals(body_path: Path) -> List[str]:
    text = body_path.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    # p1 has header rank\tliteral\tfreq
    if "\t" in lines[0] and lines[0].startswith("rank"):
        out: List[str] = []
        for ln in lines[1:]:
            parts = ln.split("\t")
            if len(parts) >= 2:
                out.append(parts[1].strip())
        return out
    # p0 plain one-per-line
    return lines


def stratified_sample(
    body: Sequence[str],
    table: Dict[str, PosRow],
    *,
    seed: int = 20260718,
) -> Dict[str, List[str]]:
    rng = random.Random(seed)
    buckets: Dict[str, List[str]] = defaultdict(list)
    for lit in body:
        row = table.get(lit)
        if not row:
            buckets["missing"].append(lit)
            continue
        buckets[stratum_of(row)].append(lit)
    sampled: Dict[str, List[str]] = {}
    for key, lits in sorted(buckets.items()):
        n = sample_size_for(len(lits))
        if n <= 0:
            continue
        pick = lits if n >= len(lits) else rng.sample(lits, n)
        sampled[key] = sorted(pick)
    return sampled


def write_audit_sample(
    sampled: Dict[str, List[str]],
    table: Dict[str, PosRow],
    out_path: Path,
    *,
    body_rank: Optional[Dict[str, int]] = None,
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(SAMPLE_HEADER), delimiter="\t", lineterminator="\n")
        w.writeheader()
        for stratum, lits in sorted(sampled.items()):
            for lit in lits:
                row = table.get(lit)
                if not row:
                    w.writerow(
                        {
                            "literal": lit,
                            "pos": "",
                            "family": "",
                            "voice": "",
                            "note": "",
                            "trust": "",
                            "stratum": stratum,
                            "rank": body_rank.get(lit, "") if body_rank else "",
                            "verdict": "",
                            "fix_pos": "",
                            "fix_family": "",
                            "fix_voice": "",
                            "audit_note": "",
                        }
                    )
                    continue
                w.writerow(
                    {
                        "literal": lit,
                        "pos": ",".join(sorted(row.pos)),
                        "family": row.family,
                        "voice": row.voice,
                        "note": row.note,
                        "trust": row.trust(),
                        "stratum": stratum,
                        "rank": body_rank.get(lit, "") if body_rank else "",
                        "verdict": "",
                        "fix_pos": "",
                        "fix_family": "",
                        "fix_voice": "",
                        "audit_note": "",
                    }
                )
    return out_path


def body_rank_map(body_path: Path) -> Dict[str, int]:
    if not body_path.is_file():
        return {}
    lines = body_path.read_text(encoding="utf-8").splitlines()
    if not lines or not lines[0].startswith("rank"):
        return {lit: i for i, lit in enumerate(load_body_literals(body_path), start=1)}
    out: Dict[str, int] = {}
    for ln in lines[1:]:
        parts = ln.split("\t")
        if len(parts) >= 2:
            try:
                out[parts[1].strip()] = int(parts[0])
            except ValueError:
                continue
    return out


def upsert_ssot_rows(
    corrections: Sequence[dict],
    *,
    tsv: Path = DEFAULT_TSV,
    note_suffix: str = "p1-audit",
) -> dict:
    """Overwrite or append rows by literal; elevates note with review when fixed."""
    table = parse_project_pos_tsv(tsv)
    old_keys = set(table.keys())
    bad = 0
    touched: List[str] = []
    for raw in corrections:
        lit = (raw.get("literal") or "").strip()
        if not lit:
            bad += 1
            continue
        pos_raw = (raw.get("fix_pos") or raw.get("pos") or "").strip()
        if not pos_raw:
            bad += 1
            continue
        try:
            pos = split_pos(pos_raw)
        except ProjectPosError:
            bad += 1
            continue
        fam_src = raw.get("fix_family")
        if fam_src is None or str(fam_src).strip() == "":
            fam_src = raw.get("family") or ""
        voice_src = raw.get("fix_voice")
        if voice_src is None or str(voice_src).strip() == "":
            voice_src = raw.get("voice") or ""
        family = str(fam_src).strip()
        voice = str(voice_src).strip()
        if family not in ("", "idiom") or voice not in ("", "active", "passive"):
            bad += 1
            continue
        base_note = (raw.get("note") or "").strip()
        audit = (raw.get("audit_note") or "").strip()
        note_parts = [p for p in (base_note, note_suffix, "review") if p]
        if audit:
            note_parts.append(audit)
        seen: Set[str] = set()
        note_bits: List[str] = []
        for p in note_parts:
            if p not in seen:
                seen.add(p)
                note_bits.append(p)
        note = ";".join(note_bits)
        table[lit] = PosRow(
            literal=lit,
            pos=frozenset(pos),
            family=family,
            voice=voice,
            note=note,
        )
        touched.append(lit)

    lines = ["literal\tpos\tfamily\tvoice\tnote"]
    for lit in sorted(table.keys()):
        row = table[lit]
        lines.append(
            f"{lit}\t{','.join(sorted(row.pos))}\t{row.family}\t{row.voice}\t{row.note}"
        )
    tsv.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "rows": len(table),
        "touched": len(touched),
        "updated": sum(1 for lit in touched if lit in old_keys),
        "added": sum(1 for lit in touched if lit not in old_keys),
        "bad": bad,
    }


def apply_verdicts_file(path: Path, *, dry_run: bool = False) -> dict:
    """Apply rows with verdict=BAD or FIX that have fix_pos filled."""
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    fixes = []
    stats = {"ok": 0, "soft": 0, "bad": 0, "skip": 0, "fix": 0}
    for r in rows:
        v = (r.get("verdict") or "").strip().upper()
        if v in ("OK", "PASS"):
            stats["ok"] += 1
            continue
        if v in ("SOFT", "SOFT-OK"):
            stats["soft"] += 1
            continue
        if v in ("BAD", "FIX"):
            stats["bad"] += 1
            if (r.get("fix_pos") or "").strip():
                fixes.append(r)
                stats["fix"] += 1
            continue
        stats["skip"] += 1
    n = stats["ok"] + stats["soft"] + stats["bad"]
    ok_n = stats["ok"] + stats["soft"]  # soft counts as acceptable for gate rate
    rate = (ok_n / n) if n else 0.0
    result = {
        "audited": n,
        "ok": stats["ok"],
        "soft_ok": stats["soft"],
        "bad": stats["bad"],
        "skip": stats["skip"],
        "fixes": stats["fix"],
        "ok_rate": round(rate, 4),
        "pass_90": rate >= 0.90 if n else False,
        "dry_run": dry_run,
    }
    if not dry_run and fixes:
        result["upsert"] = upsert_ssot_rows(fixes)
        write_carrier()
    return result


def cmd_sample(args: argparse.Namespace) -> int:
    body_path = Path(args.body)
    table = parse_project_pos_tsv()
    body = load_body_literals(body_path)
    sampled = stratified_sample(body, table, seed=int(args.seed))
    ranks = body_rank_map(body_path)
    phase = args.phase or body_path.stem.replace("_mother_body", "")
    out = Path(args.out) if args.out else AUDIT_DIR / f"{phase}_sample.tsv"
    write_audit_sample(sampled, table, out, body_rank=ranks)
    summary = {
        "phase": phase,
        "body": len(body),
        "seed": int(args.seed),
        "strata": {k: {"universe": None, "sample": len(v)} for k, v in sampled.items()},
        "out": str(out),
        "total_sample": sum(len(v) for v in sampled.values()),
    }
    # fill universe sizes
    buckets: Dict[str, int] = defaultdict(int)
    for lit in body:
        row = table.get(lit)
        if row:
            buckets[stratum_of(row)] += 1
        else:
            buckets["missing"] += 1
    for k in summary["strata"]:
        summary["strata"][k]["universe"] = buckets.get(k, 0)
        summary["strata"][k]["formula_n"] = sample_size_for(buckets.get(k, 0))
    meta_path = out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    path = Path(args.verdicts)
    result = apply_verdicts_file(path, dry_run=bool(args.dry_run))
    print(json.dumps(result, ensure_ascii=False))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_audit")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample", help="stratified sample for audit")
    s.add_argument("--body", required=True, help="p0_mother_body.txt or p1_mother_body.txt")
    s.add_argument("--phase", default="")
    s.add_argument("--seed", type=int, default=20260718)
    s.add_argument("--out", default="")
    a = sub.add_parser("apply", help="apply verdict TSV (BAD/FIX with fix_pos)")
    a.add_argument("--verdicts", required=True)
    a.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if args.cmd == "sample":
        return cmd_sample(args)
    if args.cmd == "apply":
        return cmd_apply(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
