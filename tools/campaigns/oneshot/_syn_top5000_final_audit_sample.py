"""syn_top5000 final-audit stratified sample (maintainer one-shot).

Attributes accepted pairs by TSV head (campaign seed) → batch_index, not
undirected min — mirrors batch_id attribution and avoids cross-batch drift
when both endpoints are campaign heads.

Usage:
  PYTHONIOENCODING=utf-8 python scripts/_syn_top5000_final_audit_sample.py
"""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import csv
import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest.project_antonyms import sample_pairs, sample_size_for  # noqa: E402
from tools.campaigns.project_antonyms_campaign import stratified_sample_no_natural  # noqa: E402
from tools.campaigns.project_synonyms_campaign import TOP5000_SYN_SPEC  # noqa: E402

SEED = 20260718
BATCH_PREFIX = "syn-top5000-"
FIXTURES = ROOT / "data" / "syn_ant" / "project" / "fixtures"
ACC_OUT = FIXTURES / "syn_top5000_final_audit_accepted_sample.tsv"
NN_OUT = FIXTURES / "syn_top5000_final_audit_no_natural_sample.tsv"
ADEQ_OUT = FIXTURES / "syn_top5000_final_audit_adequate_sample.tsv"
SYN_TSV = ROOT / "data" / "syn_ant" / "project" / "project_synonyms.tsv"
NN_TSV = ROOT / "data" / "syn_ant" / "project" / "project_no_natural_synonyms.tsv"
ADEQ_TSV = ROOT / "data" / "syn_ant" / "project" / "project_adequate_existing.tsv"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _load_manifest() -> Tuple[Dict[str, int], set[str]]:
    rows = list(
        csv.DictReader(
            TOP5000_SYN_SPEC.manifest_tsv.open(encoding="utf-8"), delimiter="\t"
        )
    )
    head_batch = {r["head"]: int(r["batch_index"]) for r in rows}
    return head_batch, set(head_batch)


def _load_accepted(
    campaign: set[str],
) -> List[Tuple[str, str, int]]:
    """Return (head, tail, batch_index) for this campaign only."""
    out: List[Tuple[str, str, int]] = []
    with SYN_TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if not str(r.get("batch_id", "")).startswith(BATCH_PREFIX):
                continue
            h, t = r["head"].strip(), r["tail"].strip()
            if h not in campaign:
                continue
            # batch_index from manifest head (seed), not undirected min
            bi = int(str(r["batch_id"]).split("-b")[1][:2])
            out.append((h, t, bi))
    return out


def stratified_sample_accepted_by_head(
    rows: Sequence[Tuple[str, str, int]],
    *,
    seed: int,
    batch_count: int,
) -> dict[str, Any]:
    by_batch: Dict[int, List[Tuple[str, str]]] = {i: [] for i in range(1, batch_count + 1)}
    for h, t, bi in rows:
        if 1 <= bi <= batch_count:
            by_batch[bi].append((h, t))
    sampled: List[Tuple[str, str]] = []
    strata: List[dict[str, int]] = []
    for bi in range(1, batch_count + 1):
        pop = by_batch[bi]
        n = len(pop)
        if n == 0:
            continue
        layer_seed = seed + bi
        layer = sample_pairs(pop, seed=layer_seed)
        sampled.extend(layer)
        strata.append(
            {
                "batch_index": bi,
                "parent_n": n,
                "sample_n": len(layer),
                "sample_seed": layer_seed,
            }
        )
    return {
        "status": "ok" if strata else "skipped_empty",
        "sample_seed": seed,
        "sample_n": len(sampled),
        "sample_parent_n": sum(s["parent_n"] for s in strata),
        "sampled": sampled,
        "strata": strata,
    }


def stratified_sample_adequate(
    rows: Sequence[Tuple[str, str, str]],
    head_batch: Dict[str, int],
    *,
    seed: int,
    batch_count: int,
) -> dict[str, Any]:
    """Same shape as stratified_sample_no_natural; rows=(head, note, batch_id)."""
    return stratified_sample_no_natural(
        rows, head_batch, seed=seed, batch_count=batch_count
    )


def _write_pairs(path: Path, pairs: Sequence[Tuple[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["head", "tail"])
        for h, t in pairs:
            w.writerow([h, t])


def _write_nn(path: Path, rows: Sequence[Tuple[str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["head", "reason", "batch_id"])
        for h, r, b in rows:
            w.writerow([h, r, b])


def _write_adeq(path: Path, rows: Sequence[Tuple[str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["head", "note", "batch_id"])
        for h, note, b in rows:
            w.writerow([h, note, b])


def main() -> None:
    head_batch, campaign = _load_manifest()
    assert len(campaign) == 1148, len(campaign)
    batch_count = max(head_batch.values())

    acc_rows = _load_accepted(campaign)
    acc_heads = {h for h, _, _ in acc_rows}

    nn_all: List[Tuple[str, str, str]] = []
    with NN_TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if not str(r.get("batch_id", "")).startswith(BATCH_PREFIX):
                continue
            h = r["head"].strip()
            if h in campaign:
                nn_all.append((h, r["reason"].strip(), r["batch_id"].strip()))
    nn_heads = {h for h, _, _ in nn_all}

    adeq_all: List[Tuple[str, str, str]] = []
    with ADEQ_TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            if not str(r.get("batch_id", "")).startswith(BATCH_PREFIX):
                continue
            h = r["head"].strip()
            if h in campaign:
                adeq_all.append((h, r["note"].strip(), r["batch_id"].strip()))
    adeq_heads = {h for h, _, _ in adeq_all}

    # Completion: exactly one terminal per campaign head
    if acc_heads & nn_heads or acc_heads & adeq_heads or nn_heads & adeq_heads:
        raise SystemExit(
            f"terminal overlap: acc∩nn={acc_heads & nn_heads} "
            f"acc∩adeq={acc_heads & adeq_heads} nn∩adeq={nn_heads & adeq_heads}"
        )
    resolved = acc_heads | nn_heads | adeq_heads
    if resolved != campaign:
        raise SystemExit(
            f"incomplete: missing={sorted(campaign - resolved)[:20]} "
            f"extra={sorted(resolved - campaign)[:20]} "
            f"|acc|={len(acc_heads)} |nn|={len(nn_heads)} |adeq|={len(adeq_heads)}"
        )
    print(
        f"complete: accepted={len(acc_heads)} nn={len(nn_heads)} "
        f"adequate={len(adeq_heads)} total={len(resolved)}"
    )

    acc = stratified_sample_accepted_by_head(
        acc_rows, seed=SEED, batch_count=batch_count
    )
    nn = stratified_sample_no_natural(
        nn_all, head_batch, seed=SEED, batch_count=batch_count
    )
    adeq = stratified_sample_adequate(
        adeq_all, head_batch, seed=SEED, batch_count=batch_count
    )

    _write_pairs(ACC_OUT, acc["sampled"])
    _write_nn(NN_OUT, nn["sampled"])
    _write_adeq(ADEQ_OUT, adeq["sampled"])

    print(f"manifest_sha256={_sha256(TOP5000_SYN_SPEC.manifest_tsv)}")
    for name, pack in (("accepted", acc), ("no_natural", nn), ("adequate", adeq)):
        print(
            f"{name}: parent_n={pack['sample_parent_n']} sample_n={pack['sample_n']} "
            f"strata={pack['strata']}"
        )
        # sanity: layer sizes match sample_size_for
        for s in pack["strata"]:
            expect = sample_size_for(s["parent_n"])
            if s["sample_n"] != expect:
                raise SystemExit(f"{name} batch {s['batch_index']}: {s['sample_n']}!={expect}")
    print(f"wrote {ACC_OUT.relative_to(ROOT)}")
    print(f"wrote {NN_OUT.relative_to(ROOT)}")
    print(f"wrote {ADEQ_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
