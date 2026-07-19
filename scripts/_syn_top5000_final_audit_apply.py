"""Apply syn_top5000 final-audit fails (maintainer-confirmed).

1. Drop accepted fail pairs (+ 節目/欄目 weak edge from adequate fail).
2. Move freed campaign heads → no_natural (keep campaign complete).
3. nn pending_rejudge: reason fixes; flip 會話/好少/無人 where membership allows.
4. Remove 欄目 from adequate_existing.

Usage:
  PYTHONIOENCODING=utf-8 python scripts/_syn_top5000_final_audit_apply.py --dry-run
  PYTHONIOENCODING=utf-8 python scripts/_syn_top5000_final_audit_apply.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    write_adequate_existing,
    write_no_natural_synonyms,
)

META_AUDIT = ROOT / "data" / "syn_ant" / "project" / "campaign_syn_top5000_final_audit.meta.json"
MANIFEST = ROOT / "data" / "syn_ant" / "project" / "campaign_syn_top5000.tsv"
BATCH_FIX = "syn-top5000-final-audit-20260718"

# audit suggested tails blocked by lexicon → stay no_natural
NN_TO_ACCEPTED = {
    "好少": "稀少",
    "無人": "冇人",
}
# already covered by undirected accepted pair 對話↔會話
NN_DROP_COVERED = {"會話"}

NN_REASON_FIX = {
    "荃灣": "proper_name_or_deixis",
    "九龍": "proper_name_or_deixis",
    "淘寶": "proper_name_or_deixis",
    "柯南": "proper_name_or_deixis",
    "情人節": "proper_name_or_deixis",
    "關我事": "other_documented",
    "握手": "no_stable_near_synonym",
    "考研": "no_stable_near_synonym",
    "設計師": "no_stable_near_synonym",
    "陰毛": "no_stable_near_synonym",
    "冷汗": "no_stable_near_synonym",
    "話費": "no_stable_near_synonym",
    "車型": "no_stable_near_synonym",
    "麻甩佬": "no_stable_near_synonym",
    "做愛": "no_stable_near_synonym",
    "射出": "no_stable_near_synonym",
    "嬴": "no_stable_near_synonym",
    "搖搖板": "no_stable_near_synonym",
    # membership-blocked flips stay nn with stable reason
    "下次": "no_stable_near_synonym",
    "踢波": "no_stable_near_synonym",
    "點講": "no_stable_near_synonym",
    "夜貓": "no_stable_near_synonym",
}

EXTRA_DROP = [("節目", "欄目")]  # adequate fail implies weak covering edge


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
                note = parts[1]
                batch = parts[2] if len(parts) >= 3 else ""
                by[h] = (h, note, batch)
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
    pending = meta["accepted"].get("pending_removal") or []
    drop = {(r["head"], r["tail"]) for r in pending}
    drop |= set(EXTRA_DROP)
    return {
        "drop_n": len(drop),
        "drop": sorted(drop),
        "nn_to_accepted": NN_TO_ACCEPTED,
        "nn_drop_covered": sorted(NN_DROP_COVERED),
        "nn_reason_fix_n": len(NN_REASON_FIX),
        "adeq_drop": ["欄目"],
    }


def apply() -> dict:
    meta = json.loads(META_AUDIT.read_text(encoding="utf-8"))
    if meta.get("apply_status") == "applied":
        raise SystemExit("already applied (meta.apply_status=applied)")

    campaign = _campaign_heads()
    lex = load_lexicon_literals()
    pending = meta["accepted"].get("pending_removal") or []
    drop = {(r["head"], r["tail"]) for r in pending}
    drop |= set(EXTRA_DROP)
    drop_keys = {pair_undirected_key(h, t) for h, t in drop}

    # Register fix batch in list meta before any parse that validates batch_id.
    list_meta = load_meta(DEFAULT_META)
    list_meta.setdefault("batches", {})[BATCH_FIX] = {
        "k": len(NN_TO_ACCEPTED),
        "accepted_pairs": len(NN_TO_ACCEPTED),
        "no_natural_heads": 0,
        "adequate_existing_heads": 0,
        "model_note": "final-audit apply: nn→accepted flips (membership-ok)",
        "ok_rate": 1.0,
        "ok_rate_threshold": 0.9,
        "sample_n": len(NN_TO_ACCEPTED),
        "sample_ok": len(NN_TO_ACCEPTED),
    }
    save_meta(list_meta, DEFAULT_META)

    # 1) drop accepted pairs (idempotent if already dropped)
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
        if key in drop_keys or (parts[0], parts[1]) in drop:
            removed.append(ln)
            for side in (parts[0], parts[1]):
                n = normalize_literal(side)
                if n and n in campaign:
                    freed.add(n)
        else:
            kept.append(ln)
    # also count already-absent drop pairs as freed campaign heads
    existing_keys = {
        pair_undirected_key(ln.split("\t")[0], ln.split("\t")[1])
        for ln in kept
        if ln.strip() and len(ln.split("\t")) >= 2
    }
    for h, t in drop:
        if pair_undirected_key(h, t) not in existing_keys:
            for side in (h, t):
                n = normalize_literal(side)
                if n and n in campaign:
                    freed.add(n)
    DEFAULT_TSV.write_text(
        header + "\n" + "\n".join(kept) + ("\n" if kept else "\n"),
        encoding="utf-8",
        newline="\n",
    )

    # 2) append membership-ok flips (skip if batch already present)
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
        # resume: ensure flip pairs exist
        have = {
            pair_undirected_key(ln.split("\t")[0], ln.split("\t")[1])
            for ln in tsv_text.splitlines()[1:]
            if ln.strip() and len(ln.split("\t")) >= 2
        }
        missing = [
            (h, t)
            for h, t in new_pairs
            if pair_undirected_key(h, t) not in have
        ]
        if missing:
            raise SystemExit(f"batch present but missing flips: {missing}")

    # 3) rewrite no_natural
    nn = _load_nn()
    for h in NN_DROP_COVERED:
        nn.pop(normalize_literal(h) or h, None)
    for h in NN_TO_ACCEPTED:
        nn.pop(normalize_literal(h) or h, None)
    for h, reason in NN_REASON_FIX.items():
        hn = normalize_literal(h) or h
        if hn in nn:
            nn[hn] = (hn, reason, nn[hn][2])
        elif hn in campaign:
            # only touch if was pending; skip strangers
            pass
    # 4) adequate: drop 欄目 first (so freed 欄目 can go nn)
    adq = _load_adq()
    adq.pop("欄目", None)
    _write_adq_full(adq)

    covered_now: set[str] = set()
    for p in parse_project_synonyms_tsv(DEFAULT_TSV, membership=lex):
        a, b = p.canonical_key()
        covered_now.add(a)
        covered_now.add(b)

    for h in freed:
        if h in NN_TO_ACCEPTED or h in NN_DROP_COVERED:
            continue
        if h in covered_now or h in adq:
            nn.pop(h, None)
            continue
        batch = BATCH_FIX
        if h in nn:
            batch = nn[h][2] or batch
        nn[h] = (h, "no_stable_near_synonym", batch)
    # 欄目 from adequate → nn
    if "欄目" not in covered_now:
        nn["欄目"] = ("欄目", "no_stable_near_synonym", BATCH_FIX)

    # Drop nn rows that are already accepted-covered (pre-existing duals + cleanup)
    for h in list(nn):
        if h in covered_now or h in adq:
            nn.pop(h, None)
    _write_nn_full(nn)

    # 5) completeness: exactly one终局
    # accepted = covered ∧ ¬adq ∧ ¬nn；adequate = adq（可同時 covered）；nn = nn ∧ ¬covered
    nn_h = set(nn)
    adq_h = set(adq)
    unresolved = []
    conflicts = []
    for h in sorted(campaign):
        is_adq = h in adq_h
        is_nn = h in nn_h
        is_acc = h in covered_now and not is_adq
        n = int(is_adq) + int(is_nn) + int(is_acc)
        if n == 0:
            unresolved.append(h)
        elif n > 1:
            conflicts.append(h)
    if unresolved or conflicts:
        raise SystemExit(
            f"completeness fail unresolved={unresolved[:20]} conflicts={conflicts[:20]}"
        )

    # 6) stamp audit meta
    meta["apply_status"] = "applied"
    meta["apply_batch_id"] = BATCH_FIX
    meta["apply_removed_accepted"] = len(removed)
    meta["apply_new_accepted"] = [{"head": h, "tail": t} for h, t in new_pairs]
    meta["apply_note"] = (
        f"removed {len(removed)} pairs; nn flips {list(NN_TO_ACCEPTED)}; "
        f"dropped nn covered {sorted(NN_DROP_COVERED)}; "
        f"reason fixes {len(NN_REASON_FIX)}; adeq drop 欄目; "
        f"freed→nn {len(freed)}"
    )
    META_AUDIT.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "removed": len(removed),
        "kept_pairs": len(kept),
        "new_accepted": new_pairs,
        "nn_n": len(nn),
        "adq_n": len(adq),
        "freed_to_nn": sorted(h for h in freed if h in nn),
        "campaign": len(campaign),
        "covered": len(covered_now & campaign),
    }


def main() -> int:
    if "--dry-run" in sys.argv:
        print(json.dumps(plan(), ensure_ascii=False, indent=2))
        return 0
    out = apply()
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
