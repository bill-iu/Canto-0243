"""syn_len4 final-audit stratified sample (maintainer one-shot).

Post-apply aware:
- nn / adequate / accepted terminals by ledger + undirected project_syn coverage
  (not batch_id regex alone — includes syn-len4-final-audit-* rows).
- Accepted pairs: TSV head direction when head is campaign-accepted; plus covering
  edges for campaign-accepted heads that only appear as TSV tail.
- Stratify by campaign_syn_len4.tsv batch_index (manifest), never undirected min.

Reaudit seed defaults to 20260719 (post first-audit apply). Historical first
audit used 20260718 (fixtures overwritten on re-run).

Usage:
  PYTHONIOENCODING=utf-8 python scripts/_syn_len4_final_audit_sample.py
"""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import csv
import hashlib
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set, Tuple

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.domain.relations.valid_term import normalize_literal  # noqa: E402
from ingest.project_antonyms import sample_pairs, sample_size_for  # noqa: E402
from tools.campaigns.project_antonyms_campaign import stratified_sample_no_natural  # noqa: E402
from ingest.project_synonyms import (  # noqa: E402
    DEFAULT_ADEQUATE_TSV,
    DEFAULT_NO_NATURAL_TSV,
    DEFAULT_TSV,
    load_lexicon_literals,
    parse_project_synonyms_tsv,
)
from tools.campaigns.project_synonyms_campaign import LEN4_SYN_SPEC  # noqa: E402

# Reaudit after final-audit apply (first audit seed was 20260718)
SEED = 20260719
BATCH_PREFIX = "syn-len4-"
_BATCH_RE = re.compile(r"^syn-len4-b(\d{2})-")
_LEN4_BATCH_ANY = re.compile(r"^syn-len4-")
FIXTURES = ROOT / "data" / "syn_ant" / "project" / "fixtures"
ACC_OUT = FIXTURES / "syn_len4_final_audit_accepted_sample.tsv"
NN_OUT = FIXTURES / "syn_len4_final_audit_no_natural_sample.tsv"
ADEQ_OUT = FIXTURES / "syn_len4_final_audit_adequate_sample.tsv"
SYN_TSV = DEFAULT_TSV
NN_TSV = DEFAULT_NO_NATURAL_TSV
ADEQ_TSV = DEFAULT_ADEQUATE_TSV


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _batch_index_from_id(batch_id: str) -> int | None:
    """Legacy helper for bNN batch ids; final-audit ids return None."""
    m = _BATCH_RE.match(batch_id.strip())
    return int(m.group(1)) if m else None


def _is_len4_batch(batch_id: str) -> bool:
    return bool(_LEN4_BATCH_ANY.match(batch_id.strip()))


def _load_manifest() -> Tuple[Dict[str, int], set[str]]:
    rows = list(
        csv.DictReader(
            LEN4_SYN_SPEC.manifest_tsv.open(encoding="utf-8"), delimiter="\t"
        )
    )
    head_batch = {
        (normalize_literal(r["head"].strip()) or r["head"].strip()): int(
            r["batch_index"]
        )
        for r in rows
    }
    return head_batch, set(head_batch)


def _load_terminals(
    campaign: set[str],
) -> Tuple[Set[str], Set[str], Set[str], Dict[str, List[str]]]:
    """Return (acc_heads, nn_heads, adeq_heads, cover_adj)."""
    lex = load_lexicon_literals()
    cover: Dict[str, List[str]] = {}
    for p in parse_project_synonyms_tsv(SYN_TSV, membership=lex):
        a, b = p.canonical_key()
        cover.setdefault(a, []).append(b)
        cover.setdefault(b, []).append(a)

    nn: Set[str] = set()
    with NN_TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            h = normalize_literal(r["head"].strip()) or r["head"].strip()
            if h in campaign:
                nn.add(h)

    adeq: Set[str] = set()
    with ADEQ_TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            h = normalize_literal(r["head"].strip()) or r["head"].strip()
            if h in campaign:
                adeq.add(h)

    acc: Set[str] = set()
    for h in campaign:
        covered = h in cover
        is_nn = h in nn
        is_adq = h in adeq
        n = int(covered and not is_adq and not is_nn) + int(is_nn) + int(is_adq)
        if n > 1:
            raise SystemExit(f"terminal conflict on {h!r}")
        if covered and not is_adq and not is_nn:
            acc.add(h)
        elif not is_nn and not is_adq and not covered:
            raise SystemExit(f"unresolved campaign head {h!r}")
    if nn & adeq or acc & nn or acc & adeq:
        raise SystemExit(
            f"overlap acc∩nn={acc & nn} acc∩adeq={acc & adeq} nn∩adeq={nn & adeq}"
        )
    if acc | nn | adeq != campaign:
        raise SystemExit(
            f"incomplete: missing={sorted(campaign - (acc | nn | adeq))[:20]} "
            f"|acc|={len(acc)} |nn|={len(nn)} |adeq|={len(adeq)}"
        )
    return acc, nn, adeq, cover


def _load_accepted_pairs(
    campaign: set[str],
    acc_heads: set[str],
    head_batch: Dict[str, int],
    cover: Dict[str, List[str]],
) -> List[Tuple[str, str, int]]:
    """(review_head, tail, batch_index) for sampling.

    Prefer TSV generation direction when head ∈ acc; backfill only-tail heads
    via any covering neighbor.
    """
    out: List[Tuple[str, str, int]] = []
    seen_heads: Set[str] = set()
    with SYN_TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            h = normalize_literal(r["head"].strip()) or r["head"].strip()
            t = normalize_literal(r["tail"].strip()) or r["tail"].strip()
            if h not in acc_heads:
                continue
            bi = head_batch.get(h)
            if bi is None:
                continue
            out.append((h, t, bi))
            seen_heads.add(h)

    for h in sorted(acc_heads - seen_heads):
        bi = head_batch[h]
        neigh = cover.get(h) or []
        if not neigh:
            raise SystemExit(f"accepted head {h!r} has no covering edge")
        # stable: first neighbor by literal order
        t = sorted(neigh)[0]
        out.append((h, t, bi))
    return out


def _load_nn_rows(campaign: set[str]) -> List[Tuple[str, str, str]]:
    rows: List[Tuple[str, str, str]] = []
    with NN_TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            h = normalize_literal(r["head"].strip()) or r["head"].strip()
            if h in campaign:
                rows.append((h, r["reason"].strip(), r["batch_id"].strip()))
    return rows


def _load_adeq_rows(campaign: set[str]) -> List[Tuple[str, str, str]]:
    rows: List[Tuple[str, str, str]] = []
    with ADEQ_TSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            h = normalize_literal(r["head"].strip()) or r["head"].strip()
            if h in campaign:
                rows.append((h, r["note"].strip(), r["batch_id"].strip()))
    return rows


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
    assert len(campaign) == 5000, len(campaign)
    batch_count = max(head_batch.values())

    acc_heads, nn_heads, adeq_heads, cover = _load_terminals(campaign)
    print(
        f"complete: accepted={len(acc_heads)} nn={len(nn_heads)} "
        f"adequate={len(adeq_heads)} total={len(campaign)}"
    )

    acc_rows = _load_accepted_pairs(campaign, acc_heads, head_batch, cover)
    # parent_n for accepted = number of sample units (pairs), may exceed unique heads
    # when multi-tail; completeness already checked on heads.
    nn_all = _load_nn_rows(campaign)
    adeq_all = _load_adeq_rows(campaign)
    assert {h for h, _, _ in nn_all} == nn_heads
    assert {h for h, _, _ in adeq_all} == adeq_heads

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

    print(f"manifest_sha256={_sha256(LEN4_SYN_SPEC.manifest_tsv)}")
    print(f"seed={SEED}")
    for name, pack in (("accepted", acc), ("no_natural", nn), ("adequate", adeq)):
        print(
            f"{name}: parent_n={pack['sample_parent_n']} sample_n={pack['sample_n']} "
            f"strata={pack['strata']}"
        )
        for s in pack["strata"]:
            expect = sample_size_for(s["parent_n"])
            if s["sample_n"] != expect:
                raise SystemExit(
                    f"{name} batch {s['batch_index']}: {s['sample_n']}!={expect}"
                )
    print(f"wrote {ACC_OUT.relative_to(ROOT)}")
    print(f"wrote {NN_OUT.relative_to(ROOT)}")
    print(f"wrote {ADEQ_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
