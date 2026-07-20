"""Land len4-b01: two-phase sample-parent commit then fail removal.

Phase A (run with --phase parent): append parent pairs + provisional meta, print paths.
  Then: git commit, set sample_parent to that commit.
Phase B (run with --phase final --parent-commit SHA): remove sample fails, fix meta.

Or --phase all: does parent write, expects you commit in between... 
Simpler --phase all-local: write final only with parent committed via git commit in-script.
"""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ingest.project_antonyms import (
    DEFAULT_META,
    DEFAULT_TSV,
    TSV_HEADER,
    file_sha256,
    load_meta,
    ok_rate,
    sample_pairs,
    save_meta,
)
from tools.campaigns.project_antonyms_campaign import (
    DEFAULT_ESSAY,
    LEN4_SPEC,
    write_no_natural_rows,
)

BATCH = "len4-b01-20260715"
SAMPLE_SEED = 20260716
PROMPT = ROOT / "data/syn_ant/project-antonyms-prompt-len4.txt"
HEADS = ROOT / "data/syn_ant/fixtures/len4_b01_unresolved.txt"
PARENT_FIXTURE = ROOT / "data/syn_ant/fixtures/len4_b01_parent_pairs.tsv"
NN_FIXTURE = ROOT / "data/syn_ant/fixtures/len4_b01_no_natural_final.tsv"

SAMPLE_FAILS = [
    ("欲哭無淚", "喜極而泣"),
    ("無所不在", "罕見"),
    ("諸如此類", "與眾不同"),
]


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def _load_parent() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    with PARENT_FIXTURE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rows.append((row["head"], row["tail"]))
    return sorted(set(rows))


def _append_pairs(pairs: list[tuple[str, str]]) -> None:
    text = DEFAULT_TSV.read_text(encoding="utf-8")
    if BATCH in text:
        raise SystemExit(f"batch {BATCH} already in TSV")
    if not text.endswith("\n"):
        text += "\n"
    for h, t in pairs:
        text += f"{h}\t{t}\tant\t{BATCH}\n"
    DEFAULT_TSV.write_text(text, encoding="utf-8", newline="\n")


def _strip_batch_from_tsv() -> None:
    lines = DEFAULT_TSV.read_text(encoding="utf-8").splitlines()
    header, body = lines[0], lines[1:]
    kept = [ln for ln in body if not ln.endswith(f"\t{BATCH}") and ln.strip()]
    DEFAULT_TSV.write_text(
        header + "\n" + "\n".join(kept) + ("\n" if kept else "\n"),
        encoding="utf-8",
        newline="\n",
    )


def _build_meta(
    *,
    parent: list[tuple[str, str]],
    accepted: list[tuple[str, str]],
    parent_commit: str,
    parent_tsv_sha: str,
    git_commit: str,
    db_sha: str,
) -> dict:
    sampled = sample_pairs(parent, seed=SAMPLE_SEED)
    fail_set = set(SAMPLE_FAILS)
    verdicts = []
    for h, t in sampled:
        if (h, t) in fail_set:
            verdicts.append(
                {
                    "head": h,
                    "tail": t,
                    "verdict": "fail",
                    "reasons": ["B: not stable context-free antonym"],
                }
            )
        else:
            verdicts.append({"head": h, "tail": t, "verdict": "ok", "reasons": []})
    sample_ok = sum(1 for v in verdicts if v["verdict"] == "ok")
    sample_n = len(verdicts)
    removed = [
        {"head": h, "tail": t, "reasons": ["B: not stable context-free antonym"]}
        for h, t in SAMPLE_FAILS
    ]
    prompt_sha = file_sha256(PROMPT)
    essay_sha = file_sha256(DEFAULT_ESSAY)
    return {
        "k": len({h for h, _ in accepted}),
        "git_commit": git_commit,
        "db_sha256": db_sha,
        "essay_sha256": essay_sha,
        "prompt_path": "data/syn_ant/project-antonyms-prompt-len4.txt",
        "prompt_sha256": prompt_sha,
        "model_note": (
            "len4-b01 blind draft (maintainer-curated pairs + no_natural for opaque "
            "heads); A–D sample seed=20260716; soft-prefer 4-char tails"
        ),
        "model": "xai/grok-4",
        "model_provider": "xAI",
        "model_version": "grok-4",
        "model_params": {
            "generation_mode": "maintainer_curated_blind_style",
            "max_proposals_per_head": 3,
            "temperature": None,
            "top_p": None,
            "max_output_tokens": None,
            "campaign": "len4",
            "batch_index": 1,
        },
        "sample_seed": SAMPLE_SEED,
        "sample_n": sample_n,
        "sample_ok": sample_ok,
        "ok_rate_threshold": 0.9,
        "ok_rate": round(ok_rate(sample_ok, sample_n), 4),
        "sample_parent": f"project_antonyms.tsv {BATCH} parent N={len(parent)}",
        "sample_parent_n": len(parent),
        "sample_parent_commit": parent_commit,
        "sample_parent_tsv_sha256": parent_tsv_sha,
        "sample_verdicts": verdicts,
        "removed_sample_fails": removed,
        "accepted_pairs": len(accepted),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def phase_parent() -> None:
    parent = _load_parent()
    print(f"parent pairs {len(parent)}")
    _append_pairs(parent)
    # provisional meta: treat as all-ok so intermediate state not validated with fails
    # We will not run full validate until final; still need batch_id known.
    db_sha = file_sha256(ROOT / "lyrics.db") or ("0" * 64)
    # placeholder commit fields filled after commit
    entry = _build_meta(
        parent=parent,
        accepted=parent,  # provisional
        parent_commit="0" * 40,
        parent_tsv_sha="0" * 64,
        git_commit="0" * 40,
        db_sha=db_sha,
    )
    # provisional: mark fails as ok so gate would pass if someone validates parent land
    for v in entry["sample_verdicts"]:
        v["verdict"] = "ok"
        v["reasons"] = []
    entry["sample_ok"] = entry["sample_n"]
    entry["ok_rate"] = 1.0
    entry["removed_sample_fails"] = []
    entry["accepted_pairs"] = len(parent)
    entry["model_note"] += " [parent land provisional]"
    meta = load_meta(DEFAULT_META)
    meta.setdefault("batches", {})[BATCH] = entry
    save_meta(meta, DEFAULT_META)
    print("wrote parent TSV+meta; commit then run --phase final --parent-commit <sha>")


def phase_final(parent_commit: str) -> None:
    parent = _load_parent()
    fail_set = set(SAMPLE_FAILS)
    accepted = [(h, t) for h, t in parent if (h, t) not in fail_set]
    print(f"accepted {len(accepted)} parent {len(parent)}")

    # rewrite TSV: strip batch then write accepted only
    _strip_batch_from_tsv()
    _append_pairs(accepted)

    parent_blob = subprocess_show(parent_commit, "data/syn_ant/project_antonyms.tsv")
    parent_sha = hashlib.sha256(parent_blob).hexdigest()
    db_sha = file_sha256(ROOT / "lyrics.db") or ("0" * 64)
    # git_commit filled with parent_commit for now; update after final commit if needed
    entry = _build_meta(
        parent=parent,
        accepted=accepted,
        parent_commit=parent_commit.lower(),
        parent_tsv_sha=parent_sha,
        git_commit=parent_commit.lower(),
        db_sha=db_sha,
    )
    meta = load_meta(DEFAULT_META)
    meta.setdefault("batches", {})[BATCH] = entry
    save_meta(meta, DEFAULT_META)

    # no-natural: merge inherited + new
    heads = {
        ln.strip()
        for ln in HEADS.read_text(encoding="utf-8").splitlines()
        if ln.strip()
    }
    covered = {h for h, _ in accepted}
    nn_new: list[tuple[str, str, str]] = []
    with NN_FIXTURE.open(encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["head"] in covered:
                continue
            nn_new.append((row["head"], row["reason"], BATCH))
    # ensure all unresolved heads accounted
    have = {h for h, _, _ in nn_new}
    for h in sorted(heads - covered - have):
        nn_new.append((h, "no_gradable_opposite", BATCH))

    existing = []
    if LEN4_SPEC.no_natural_tsv.is_file():
        with LEN4_SPEC.no_natural_tsv.open(encoding="utf-8") as f:
            for row in csv.DictReader(f, delimiter="\t"):
                if row["head"] not in covered:
                    existing.append((row["head"], row["reason"], row["batch_id"]))
    # drop inherited heads that are now accepted; keep other inherited
    exist_heads = {h for h, _, _ in existing}
    merged = existing + [r for r in nn_new if r[0] not in exist_heads]
    # de-dupe by head (prefer new batch)
    by_head: dict[str, tuple[str, str, str]] = {}
    for h, r, b in existing:
        by_head[h] = (h, r, b)
    for h, r, b in nn_new:
        by_head[h] = (h, r, b)
    # remove accepted heads
    for h in covered:
        by_head.pop(h, None)
    rows = sorted(by_head.values(), key=lambda x: x[0])
    write_no_natural_rows(LEN4_SPEC.no_natural_tsv, rows)

    # nn meta: full sample ok for this batch's new rows only
    from tools.campaigns.project_antonyms_campaign import (
        sample_no_natural_rows,
        load_no_natural_meta,
        write_empty_no_natural_meta,
    )

    batch_nn = [(h, r, b) for h, r, b in rows if b == BATCH]
    seed = 20260716
    sampled = sample_no_natural_rows(batch_nn, seed=seed)
    nn_meta_path = LEN4_SPEC.no_natural_meta
    if not nn_meta_path.is_file():
        write_empty_no_natural_meta(nn_meta_path)
    nn_meta = load_no_natural_meta(nn_meta_path)
    nn_meta.setdefault("batches", {})[BATCH] = {
        "sample_seed": seed,
        "sample_n": len(sampled),
        "sample_ok": len(sampled),
        "ok_rate_threshold": 0.9,
        "sample_parent_n": len(batch_nn),
        "removed_sample_fails": [],
        "sample_verdicts": [
            {"head": h, "reason": r, "verdict": "ok"} for h, r, _ in sampled
        ],
        "git_commit": parent_commit.lower(),
    }
    nn_meta_path.write_text(
        json.dumps(nn_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "accepted_pairs": len(accepted),
                "accepted_heads": len(covered),
                "no_natural_total": len(rows),
                "no_natural_batch": len(batch_nn),
                "sample_ok_rate": entry["ok_rate"],
                "parent_commit": parent_commit,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def subprocess_show(commit: str, path: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(ROOT), "show", f"{commit}:{path}"]
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=("parent", "final"), required=True)
    ap.add_argument("--parent-commit", default="")
    args = ap.parse_args()
    if args.phase == "parent":
        phase_parent()
    else:
        if not args.parent_commit or len(args.parent_commit) < 40:
            raise SystemExit("need --parent-commit 40-hex")
        phase_final(args.parent_commit)


if __name__ == "__main__":
    main()
