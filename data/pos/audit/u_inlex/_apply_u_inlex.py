"""Apply u_inlex agent labels (+ optional idiom_u) into project_pos SSOT."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter
from pathlib import Path

from ingest.project_pos import DEFAULT_META, load_meta, parse_project_pos_tsv, write_carrier
from ingest.project_pos_audit import upsert_ssot_rows

INLEX = Path(__file__).resolve().parent
ROOT = INLEX.parents[3]  # data/pos/audit/u_inlex → repo
ALLOWED = set("nvarx")


def _norm_pos(raw: str) -> str | None:
    raw = (raw or "").strip()
    if not raw or raw == "u":
        return None
    tags = [t.strip() for t in raw.split(",") if t.strip()]
    if not tags or any(t not in ALLOWED for t in tags):
        return None
    if "u" in tags:
        return None
    return ",".join(sorted(set(tags)))


def load_label_parts() -> list[dict]:
    fixes: list[dict] = []
    keep_u: list[dict] = []
    seen: set[str] = set()
    for p in sorted(INLEX.glob("label_part*.tsv")):
        if p.name.startswith("_"):
            continue
        with p.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                lit = (r.get("literal") or "").strip()
                if not lit or lit in seen:
                    continue
                seen.add(lit)
                pos = _norm_pos(r.get("pos") or "")
                if not pos:
                    keep_u.append(
                        {
                            "literal": lit,
                            "pos": (r.get("pos") or "u").strip() or "u",
                            "note": (r.get("note") or "").strip(),
                            "src": p.name,
                        }
                    )
                    continue
                fam = (r.get("family") or "").strip()
                if fam not in ("", "idiom"):
                    fam = ""
                voice = (r.get("voice") or "").strip()
                if voice not in ("", "active", "passive"):
                    voice = ""
                note = (r.get("note") or "").strip()
                fixes.append(
                    {
                        "literal": lit,
                        "fix_pos": pos,
                        "fix_family": fam,
                        "fix_voice": voice,
                        "note": note,
                        "audit_note": "u-inlex-agent",
                        "src": p.name,
                    }
                )
    return fixes, keep_u


def load_idiom_u() -> list[dict]:
    path = INLEX / "idiom_u_auto.tsv"
    if not path.exists():
        return []
    out: list[dict] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh, delimiter="\t"):
            lit = (r.get("literal") or "").strip()
            pos = _norm_pos(r.get("pos") or "")
            if not lit or not pos:
                continue
            pat = (r.get("pattern") or "").strip()
            out.append(
                {
                    "literal": lit,
                    "fix_pos": pos,
                    "fix_family": "idiom",
                    "fix_voice": "",
                    "note": f"p2-idiom:{pat}" if pat else "p2-idiom-heuristic",
                    "audit_note": "u-inlex-idiom-auto",
                }
            )
    return out


def apply_fixes(fixes: list[dict], *, note_suffix: str) -> dict:
    table = parse_project_pos_tsv()
    usable = []
    skipped = Counter()
    for f in fixes:
        lit = f["literal"]
        row = table.get(lit)
        if not row:
            skipped["missing"] += 1
            continue
        if row.pos != frozenset({"u"}):
            skipped["already_formal"] += 1
            continue
        usable.append(f)
    up = upsert_ssot_rows(usable, note_suffix=note_suffix)
    write_carrier()
    return {"upsert": up, "usable": len(usable), "skipped": dict(skipped)}


def sample_promotions(*, seed: int = 42, round_id: int = 1) -> dict:
    """Sample from rows whose note mentions u-inlex-agent (or idiom-auto)."""
    table = parse_project_pos_tsv()
    universe = [
        lit
        for lit, r in table.items()
        if "u-inlex-agent" in (r.note or "")
        and r.pos != frozenset({"u"})
    ]
    n = min(len(universe), max(50, math.ceil(len(universe) * 0.05))) if universe else 0
    rng = random.Random(seed)
    sample = sorted(rng.sample(universe, n)) if n and n < len(universe) else sorted(universe)
    out = INLEX / f"u_inlex_gate_r{round_id}.tsv"
    header = [
        "literal",
        "pos",
        "family",
        "voice",
        "note",
        "trust",
        "verdict",
        "fix_pos",
        "fix_family",
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
                    "verdict": "",
                    "fix_pos": "",
                    "fix_family": "",
                    "audit_note": "",
                }
            )
    meta = {
        "round": round_id,
        "seed": seed,
        "universe": len(universe),
        "sample_n": n,
        "out": str(out.relative_to(ROOT)).replace("\\", "/"),
        "threshold": 0.90,
    }
    out.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return meta


def ssot_u_stats() -> dict:
    table = parse_project_pos_tsv()
    u = sum(1 for r in table.values() if r.pos == frozenset({"u"}))
    formal = sum(1 for r in table.values() if r.pos != frozenset({"u"}))
    return {"rows": len(table), "u": u, "formal": formal}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "cmd",
        choices=["apply-labels", "apply-idiom", "sample", "status", "run-labels"],
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--round", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.cmd == "status":
        fixes, keep_u = load_label_parts()
        idioms = load_idiom_u()
        print(
            json.dumps(
                {
                    "ssot": ssot_u_stats(),
                    "label_formal": len(fixes),
                    "label_keep_u": len(keep_u),
                    "idiom_u": len(idioms),
                    "keep_u_sample": [k["literal"] for k in keep_u[:30]],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.cmd in ("apply-labels", "run-labels"):
        fixes, keep_u = load_label_parts()
        before = ssot_u_stats()
        if args.dry_run:
            print(
                json.dumps(
                    {"dry_run": True, "would_apply": len(fixes), "keep_u": len(keep_u), "before": before},
                    ensure_ascii=False,
                )
            )
            return 0
        result = apply_fixes(fixes, note_suffix="u-inlex")
        after = ssot_u_stats()
        # stamp meta
        meta = load_meta()
        meta["u_inlex"] = {
            "applied_formal": result["usable"],
            "keep_u": len(keep_u),
            "upsert": result["upsert"],
            "skipped": result["skipped"],
            "before": before,
            "after": after,
        }
        DEFAULT_META.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({"apply_labels": result, "before": before, "after": after}, ensure_ascii=False, indent=2))
        if args.cmd == "run-labels":
            sm = sample_promotions(seed=args.seed, round_id=args.round)
            print(json.dumps({"sample": sm}, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "apply-idiom":
        idioms = load_idiom_u()
        before = ssot_u_stats()
        if args.dry_run:
            print(json.dumps({"dry_run": True, "would_apply": len(idioms), "before": before}, ensure_ascii=False))
            return 0
        result = apply_fixes(idioms, note_suffix="u-inlex-idiom")
        after = ssot_u_stats()
        meta = load_meta()
        meta["u_inlex_idiom"] = {
            "applied": result["usable"],
            "upsert": result["upsert"],
            "skipped": result["skipped"],
            "before": before,
            "after": after,
            "note": "blanket pos from idiom_u_auto (mostly v,a); gate separately",
        }
        DEFAULT_META.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({"apply_idiom": result, "before": before, "after": after}, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "sample":
        sm = sample_promotions(seed=args.seed, round_id=args.round)
        print(json.dumps(sm, ensure_ascii=False, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
