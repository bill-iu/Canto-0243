"""Export stratified full-system POS audit samples for P0/P1/P2/P3."""
from __future__ import annotations

import csv
import json
import random
from collections import defaultdict
from pathlib import Path

from ingest.project_pos import parse_project_pos_tsv
from ingest.project_pos_audit import sample_size_for
from ingest.project_pos_p0 import load_p0_mother_body
from ingest.project_pos_p1 import load_p1_mother_body
from ingest.project_pos_p2 import load_p2_body
from ingest.project_pos_p3 import load_p3_body

SEED = 20260720
ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "data" / "pos" / "audit" / "full_r1"


def stratum_row(lit: str, t) -> str:
    r = t[lit]
    fam = "idiom" if r.family == "idiom" else "plain"
    if r.gate_pos():
        g = "gate"
    elif r.pos <= frozenset({"u"}):
        g = "u"
    elif r.trust() == "low" and r.formal_pos():
        g = "low"
    else:
        g = "other"
    return f"{r.trust()}|{g}|{fam}"


def main() -> None:
    rng = random.Random(SEED)
    t = parse_project_pos_tsv()
    p0 = set(load_p0_mother_body())
    p1 = set(load_p1_mother_body())
    p2 = {lit for lit, _ in load_p2_body() if lit in t and t[lit].family == "idiom"}
    p3 = {lit for _, lit in load_p3_body()}
    phases = {
        "p0": sorted(p0),
        "p1": sorted(p1),
        "p2_idiom": sorted(p2),
        "p3": sorted(p3),
    }
    AUDIT.mkdir(parents=True, exist_ok=True)
    summary: dict = {"seed": SEED, "threshold": 0.90, "phases": {}}
    header = [
        "phase",
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
    all_samples: list[dict] = []
    for phase, lits in phases.items():
        buckets: dict[str, list[str]] = defaultdict(list)
        for lit in lits:
            if lit not in t:
                continue
            buckets[stratum_row(lit, t)].append(lit)
        phase_sample: list[dict] = []
        strata_meta: dict = {}
        for sk, members in sorted(buckets.items()):
            n = sample_size_for(len(members))
            pick = members if n >= len(members) else rng.sample(members, n)
            strata_meta[sk] = {"universe": len(members), "sample": len(pick)}
            for lit in sorted(pick):
                r = t[lit]
                phase_sample.append(
                    {
                        "phase": phase,
                        "literal": lit,
                        "pos": ",".join(sorted(r.pos)),
                        "family": r.family,
                        "voice": r.voice,
                        "note": r.note,
                        "trust": r.trust(),
                        "stratum": sk,
                        "verdict": "",
                        "fix_pos": "",
                        "fix_family": "",
                        "fix_voice": "",
                        "audit_note": "",
                    }
                )
        out = AUDIT / f"{phase}_sample.tsv"
        with out.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header, delimiter="\t", lineterminator="\n")
            w.writeheader()
            w.writerows(phase_sample)
        summary["phases"][phase] = {
            "universe": len(lits),
            "sample_n": len(phase_sample),
            "strata": strata_meta,
            "out": str(out),
        }
        all_samples.extend(phase_sample)
        print(phase, "universe", len(lits), "sample", len(phase_sample), "strata", len(strata_meta))

    out = AUDIT / "all_phases_sample.tsv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(all_samples)
    summary["total_sample"] = len(all_samples)
    summary["combined_out"] = str(out)
    (AUDIT / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("TOTAL", len(all_samples))


if __name__ == "__main__":
    main()
