"""Apply syn_len4 reaudit sample fails (post PASS gate cleanup).

1. Drop accepted sample fails (+ reverse covering edges for adeq fails).
2. nn→accepted (membership-ok flips from reaudit).
3. Drop failed adequate heads → no_natural when uncovered.
4. Keep campaign_syn_len4 5000／5000 complete.

Usage:
  PYTHONIOENCODING=utf-8 python scripts/_syn_len4_final_audit_reaudit_apply.py --dry-run
  PYTHONIOENCODING=utf-8 python scripts/_syn_len4_final_audit_reaudit_apply.py
"""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import json
import sys
from pathlib import Path

sys.path.insert(0, str(ROOT))

from app.domain.relations.valid_term import normalize_literal  # noqa: E402
from ingest.project_antonyms import pair_undirected_key  # noqa: E402
from ingest.project_synonyms import (  # noqa: E402
    DEFAULT_ADEQUATE_TSV,
    DEFAULT_META,
    DEFAULT_NO_NATURAL_TSV,
    DEFAULT_TSV,
    NO_NATURAL_REASONS,
    append_synonym_pairs,
    load_lexicon_literals,
    load_meta,
    parse_project_synonyms_tsv,
    save_meta,
)

META_AUDIT = ROOT / "data" / "syn_ant" / "project" / "campaign_syn_len4_final_audit.meta.json"
MANIFEST = ROOT / "data" / "syn_ant" / "project" / "campaign_syn_len4.tsv"
BATCH_FIX = "syn-len4-reaudit-20260719"

# Covering edges for adeq fails (drop so heads are not falsely covered)
EXTRA_DROP = [
    ("喃喃", "喃喃自語"),
    ("一線希望", "一線生機"),
    ("指名道姓", "直呼其名"),
    ("收買人心", "籠絡人心"),
]

NN_TO_ACCEPTED = {
    "無藥可救": "不可救藥",
    "倒背如流": "滾瓜爛熟",
    "自相殘殺": "同類相殘",
    "反覆思量": "思前想後",
    "體外受精": "試管受孕",
}


def _campaign_heads() -> set[str]:
    out: set[str] = set()
    for ln in MANIFEST.read_text(encoding="utf-8").splitlines()[1:]:
        if not ln.strip():
            continue
        out.add(normalize_literal(ln.split("\t")[1]) or ln.split("\t")[1])
    return out


def _load_nn() -> dict[str, tuple[str, str, str]]:
    by: dict[str, tuple[str, str, str]] = {}
    for i, ln in enumerate(DEFAULT_NO_NATURAL_TSV.read_text(encoding="utf-8").splitlines()):
        if i == 0 or not ln.strip():
            continue
        parts = ln.split("\t")
        if len(parts) >= 3:
            h = normalize_literal(parts[0])
            if h:
                by[h] = (h, parts[1], parts[2])
    return by


def _load_adq() -> dict[str, tuple[str, str, str]]:
    by: dict[str, tuple[str, str, str]] = {}
    for i, ln in enumerate(DEFAULT_ADEQUATE_TSV.read_text(encoding="utf-8").splitlines()):
        if i == 0 or not ln.strip():
            continue
        parts = ln.split("\t")
        if len(parts) >= 2:
            h = normalize_literal(parts[0])
            if h:
                by[h] = (h, parts[1], parts[2] if len(parts) >= 3 else "")
    return by


def _write_nn_full(by: dict[str, tuple[str, str, str]]) -> None:
    for _h, reason, _b in by.values():
        if reason not in NO_NATURAL_REASONS:
            raise SystemExit(f"bad reason {reason!r}")
    lines = ["head\treason\tbatch_id"]
    for h, reason, batch_id in sorted(by.values(), key=lambda r: r[0]):
        lines.append(f"{h}\t{reason}\t{batch_id}")
    DEFAULT_NO_NATURAL_TSV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_adq_full(by: dict[str, tuple[str, str, str]]) -> None:
    lines = ["head\tnote\tbatch_id"]
    for h, note, batch_id in sorted(by.values(), key=lambda r: r[0]):
        lines.append(f"{h}\t{note}\t{batch_id}")
    DEFAULT_ADEQUATE_TSV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plan() -> dict:
    meta = json.loads(META_AUDIT.read_text(encoding="utf-8"))
    pending = meta.get("accepted", {}).get("pending_removal") or []
    return {
        "apply_status": meta.get("reaudit_apply_status"),
        "gate_status": meta.get("gate_status"),
        "pending_removal_n": len(pending),
        "extra_drop_n": len(EXTRA_DROP),
        "nn_to_accepted_n": len(NN_TO_ACCEPTED),
        "adeq_rejudge_n": len(meta.get("adequate_existing", {}).get("pending_rejudge") or []),
    }


def apply() -> dict:
    meta = json.loads(META_AUDIT.read_text(encoding="utf-8"))
    if meta.get("reaudit_apply_status") == "applied":
        raise SystemExit("already applied (meta.reaudit_apply_status=applied)")
    if meta.get("gate_status") != "PASSED":
        raise SystemExit(f"gate_status={meta.get('gate_status')!r} (want PASSED)")

    campaign = _campaign_heads()
    lex = load_lexicon_literals()
    pending = meta.get("accepted", {}).get("pending_removal") or []
    adeq_fail_heads = {
        normalize_literal(r["head"]) or r["head"]
        for r in (meta.get("adequate_existing", {}).get("pending_rejudge") or [])
    }

    drop = {(r["head"], r["tail"]) for r in pending}
    drop |= set(EXTRA_DROP)
    drop_keys = {pair_undirected_key(h, t) for h, t in drop}

    list_meta = load_meta(DEFAULT_META)
    list_meta.setdefault("batches", {})[BATCH_FIX] = {
        "k": len(NN_TO_ACCEPTED),
        "accepted_pairs": len(NN_TO_ACCEPTED),
        "no_natural_heads": 0,
        "adequate_existing_heads": 0,
        "model_note": "syn_len4 reaudit apply: nn→accepted flips",
        "ok_rate": 1.0,
        "ok_rate_threshold": 0.9,
        "sample_n": len(NN_TO_ACCEPTED),
        "sample_ok": len(NN_TO_ACCEPTED),
    }
    save_meta(list_meta, DEFAULT_META)

    lines = DEFAULT_TSV.read_text(encoding="utf-8").splitlines()
    header, body = lines[0], lines[1:]
    kept, removed = [], []
    freed: set[str] = set()
    for ln in body:
        if not ln.strip():
            continue
        parts = ln.split("\t")
        if len(parts) < 2:
            kept.append(ln)
            continue
        key = pair_undirected_key(parts[0], parts[1])
        if key in drop_keys:
            removed.append(ln)
            for side in (parts[0], parts[1]):
                n = normalize_literal(side)
                if n and n in campaign:
                    freed.add(n)
        else:
            kept.append(ln)
    DEFAULT_TSV.write_text(
        header + "\n" + "\n".join(kept) + ("\n" if kept else "\n"),
        encoding="utf-8",
        newline="\n",
    )

    new_pairs: list[tuple[str, str]] = []
    for h, t in NN_TO_ACCEPTED.items():
        nh, nt = normalize_literal(h), normalize_literal(t)
        if not nh or not nt or nh not in lex or nt not in lex:
            raise SystemExit(f"flip not in lexicon: {h}/{t}")
        new_pairs.append((nh, nt))
        freed.discard(nh)

    tsv_text = DEFAULT_TSV.read_text(encoding="utf-8")
    if BATCH_FIX not in tsv_text:
        append_synonym_pairs(new_pairs, batch_id=BATCH_FIX)
    else:
        have = {
            pair_undirected_key(ln.split("\t")[0], ln.split("\t")[1])
            for ln in tsv_text.splitlines()[1:]
            if ln.strip() and len(ln.split("\t")) >= 2
        }
        missing = [
            (h, t) for h, t in new_pairs if pair_undirected_key(h, t) not in have
        ]
        if missing:
            raise SystemExit(f"batch present but missing flips: {missing}")

    covered_now: set[str] = set()
    for p in parse_project_synonyms_tsv(DEFAULT_TSV, membership=lex):
        a, b = p.canonical_key()
        covered_now.add(a)
        covered_now.add(b)

    nn = _load_nn()
    adq = _load_adq()

    for h in adeq_fail_heads:
        adq.pop(h, None)

    for h in NN_TO_ACCEPTED:
        nn.pop(normalize_literal(h) or h, None)

    for h in freed:
        if h in covered_now or h in adq:
            nn.pop(h, None)
            continue
        batch = nn[h][2] if h in nn else BATCH_FIX
        nn[h] = (h, "no_stable_near_synonym", batch)

    for h in list(nn):
        if h in covered_now or h in adq:
            nn.pop(h, None)

    for h in list(adq):
        if h not in covered_now:
            adq.pop(h, None)
            if h in campaign:
                nn[h] = (h, "no_stable_near_synonym", BATCH_FIX)

    # adeq fails that lost cover → nn
    for h in adeq_fail_heads:
        if h in campaign and h not in covered_now and h not in adq:
            nn[h] = (h, "no_stable_near_synonym", BATCH_FIX)

    _write_nn_full(nn)
    _write_adq_full(adq)

    nn_h, adq_h = set(nn), set(adq)
    unresolved, conflicts = [], []
    for h in sorted(campaign):
        is_adq = h in adq_h
        is_nn = h in nn_h
        is_acc = h in covered_now and not is_adq and not is_nn
        n = int(is_adq) + int(is_nn) + int(is_acc)
        if n == 0:
            unresolved.append(h)
        elif n > 1:
            conflicts.append(h)
    if unresolved or conflicts:
        raise SystemExit(
            f"completeness fail unresolved={unresolved[:30]} conflicts={conflicts[:30]}"
        )

    meta["reaudit_apply_status"] = "applied"
    meta["reaudit_apply_batch_id"] = BATCH_FIX
    meta["reaudit_apply_removed_accepted"] = len(removed)
    meta["reaudit_apply_new_accepted"] = [{"head": h, "tail": t} for h, t in new_pairs]
    meta["reaudit_apply_note"] = (
        f"reaudit apply: removed {len(removed)} pairs; "
        f"nn→accepted {len(new_pairs)}; adeq fails dropped {len(adeq_fail_heads)}; "
        f"post-apply 5000/5000 complete"
    )
    meta["gate_status_post_reaudit_apply"] = "passed_cleaned"
    META_AUDIT.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    acc_n = sum(1 for h in campaign if h in covered_now and h not in adq_h and h not in nn_h)
    return {
        "removed": len(removed),
        "new_accepted": new_pairs,
        "nn_n": len(nn),
        "adq_n": len(adq),
        "acc_heads": acc_n,
        "campaign": len(campaign),
        "sum": acc_n + len(nn) + len(adq),
    }


def main() -> int:
    if "--dry-run" in sys.argv:
        print(json.dumps(plan(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(apply(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
