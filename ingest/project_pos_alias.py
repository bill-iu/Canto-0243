"""詞性字面別名 + fragment 標記（ADR-0060 / CONTEXT § 詞性碎片）。"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from ingest.project_pos import DEFAULT_META, PosRow, load_meta, parse_project_pos_tsv, write_carrier
from ingest.project_pos_cleanup import _rewrite_table

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ALIAS = ROOT / "data" / "pos" / "alias.tsv"
DEFAULT_PROPOSALS = ROOT / "data" / "pos" / "alias_proposals.tsv"
ALIAS_HEADER = ("source", "target", "kind", "note")
PROP_HEADER = ("source", "target", "kind", "score", "note")
FRAGMENT_KINDS = frozenset({"residual", "clause-slice", "opaque"})
# u_inlex keep-u seeds (residual pairs live in alias.tsv)
CLAUSE_SLICE_SEED = "我見 將我 你估 我識 總有 個月 講乜 仲話 不知幾 人嚟 我架 你仲記".split()
OPAQUE_SEED = "然 侏 咖 咇 企響度".split()
TARGET_POS = {"曱甴": "n", "蘿蔔": "n", "骷髏": "n"}


def load_alias(path: Path = DEFAULT_ALIAS) -> List[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def alias_map(rows: Optional[Sequence[dict]] = None) -> Dict[str, str]:
    rows = list(rows) if rows is not None else load_alias()
    out: Dict[str, str] = {}
    for r in rows:
        src = (r.get("source") or "").strip()
        tgt = (r.get("target") or "").strip()
        if src and tgt:
            out[src] = tgt
    return out


def covered_literals(table: Optional[dict] = None) -> set:
    """SSOT keys plus residual sources whose alias target is on the main table."""
    table = table if table is not None else parse_project_pos_tsv()
    amap = alias_map()
    keys = set(table.keys())
    return keys | {src for src, tgt in amap.items() if tgt in keys}


def _note_tokens(note: str) -> List[str]:
    return [t.strip() for t in (note or "").split(";") if t.strip()]


def _with_tokens(note: str, *add: str) -> str:
    seen = set()
    bits: List[str] = []
    for t in _note_tokens(note) + list(add):
        if t and t not in seen:
            seen.add(t)
            bits.append(t)
    return ";".join(bits)


def is_fragment_note(note: str) -> bool:
    toks = set(_note_tokens(note))
    if "fragment" not in toks:
        return False
    return bool(toks & FRAGMENT_KINDS) or "residual" in toks


def dual_coverage(table: Optional[dict] = None) -> dict:
    table = table if table is not None else parse_project_pos_tsv()
    amap = alias_map()
    n_all = len(table)
    formal = sum(1 for r in table.values() if r.pos != frozenset({"u"}))
    # fragment: note-tagged OR residual source still present (should be rare after apply)
    frag_lits = set()
    for lit, r in table.items():
        if is_fragment_note(r.note) or lit in amap:
            frag_lits.add(lit)
    n_frag = len(frag_lits)
    non_frag = n_all - n_frag
    formal_non = sum(
        1 for lit, r in table.items() if lit not in frag_lits and r.pos != frozenset({"u"})
    )
    return {
        "rows": n_all,
        "formal": formal,
        "u": n_all - formal,
        "fragment": n_frag,
        "formal_over_all": round(formal / n_all, 4) if n_all else 0.0,
        "formal_over_non_fragment": round(formal_non / non_frag, 4) if non_frag else 0.0,
        "non_fragment": non_frag,
        "formal_non_fragment": formal_non,
        "d4_pass_95": (formal_non / non_frag >= 0.95) if non_frag else False,
        "alias_n": len(amap),
    }


def ensure_targets(table: dict) -> List[str]:
    """Ensure alias targets exist with formal POS (must ∈ db∪curated)."""
    from ingest.project_pos_lexicon_prune import load_lexicon_literals

    try:
        lex = load_lexicon_literals(include_curated=True)
    except FileNotFoundError:
        lex = None
    added: List[str] = []
    for tgt in sorted(set(alias_map().values())):
        if lex is not None and tgt not in lex:
            continue
        pos = frozenset(TARGET_POS.get(tgt, "n").split(","))
        row = table.get(tgt)
        if row is None:
            table[tgt] = PosRow(tgt, pos, "", "", _with_tokens("", "alias-target", "review", "u-inlex-residual"))
            added.append(tgt)
        elif row.pos == frozenset({"u"}):
            table[tgt] = PosRow(
                tgt, pos, row.family, row.voice, _with_tokens(row.note, "alias-target", "review", "u-inlex-residual")
            )
            added.append(tgt)
    return added


def strip_residual_sources(table: dict) -> List[str]:
    """Remove residual sources from SSOT main table (R3)."""
    removed = [src for src in alias_map() if src in table]
    for src in removed:
        del table[src]
    return removed


def _tag_kind(table: dict, lits: Sequence[str], kind: str, stats: Counter, key: str) -> None:
    for lit in lits:
        row = table.get(lit)
        if not row:
            stats[f"{key}_missing"] += 1
            continue
        table[lit] = PosRow(lit, frozenset({"u"}), row.family, row.voice, _with_tokens(row.note, "fragment", kind))
        stats[f"{key}_tagged"] += 1


def tag_fragments(table: dict) -> dict:
    stats: Counter = Counter()
    _tag_kind(table, CLAUSE_SLICE_SEED, "clause-slice", stats, "clause")
    _tag_kind(table, OPAQUE_SEED, "opaque", stats, "opaque")
    return dict(stats)


def propose_residual(path: Path = DEFAULT_PROPOSALS) -> dict:
    """A2 eye: u-char pairs forming an SSOT literal — report only (no auto apply)."""
    table = parse_project_pos_tsv()
    u_sing = [lit for lit, r in table.items() if r.pos == frozenset({"u"}) and len(lit) == 1]
    have = {(r["source"], r["target"]) for r in load_alias()}
    best: Dict[Tuple[str, str], dict] = {}
    for a in u_sing:
        for b in u_sing:
            if a == b:
                continue
            full = a + b
            if full not in table:
                continue
            score = 1.0 if table[full].pos != frozenset({"u"}) else 0.3
            for src in (a, b):
                key = (src, full)
                if key in have:
                    continue
                row = {
                    "source": src,
                    "target": full,
                    "kind": "residual",
                    "score": f"{score:.2f}",
                    "note": "auto-pair; needs human apply",
                }
                if key not in best or score > float(best[key]["score"]):
                    best[key] = row
    rows = sorted(best.values(), key=lambda x: (-float(x["score"]), x["source"], x["target"]))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(PROP_HEADER), delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return {"proposals": len(rows), "out": str(path.relative_to(ROOT)).replace("\\", "/")}


def apply_pipeline(*, dry_run: bool = False) -> dict:
    table = parse_project_pos_tsv()
    before = dual_coverage(table)
    added = ensure_targets(table)
    removed = strip_residual_sources(table)
    frag_stats = tag_fragments(table)
    after_cov = dual_coverage(table)
    result = {
        "dry_run": dry_run,
        "targets_ensured": added,
        "residuals_removed_from_ssot": removed,
        "fragment_tags": frag_stats,
        "before": before,
        "after": after_cov,
    }
    if dry_run:
        return result
    _rewrite_table(table)
    write_carrier()
    meta = load_meta()
    meta["u_inlex_fragment_alias"] = result
    DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def cmd_status(_: argparse.Namespace) -> int:
    print(json.dumps({"alias": len(load_alias()), "coverage": dual_coverage()}, ensure_ascii=False, indent=2))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="project_pos_alias")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="dual coverage + alias count")
    sub.add_parser("propose", help="write alias_proposals.tsv (report only)")
    ap = sub.add_parser("apply", help="ensure targets, strip residual sources, tag fragments")
    ap.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)
    if args.cmd == "status":
        return cmd_status(args)
    if args.cmd == "propose":
        print(json.dumps(propose_residual(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "apply":
        print(json.dumps(apply_pipeline(dry_run=args.dry_run), ensure_ascii=False, indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
