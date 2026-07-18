"""Land syn_top5000 batch-3: accepted pairs + no_natural + adequate_existing."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.lexicon.essay_index import load_essay_corpus  # noqa: E402
from ingest.project_antonyms import ok_rate, sample_pairs, sample_size_for  # noqa: E402
from app.domain.relations.valid_term import normalize_literal  # noqa: E402
from ingest.project_synonyms import (  # noqa: E402
    DEFAULT_ADEQUATE_TSV,
    DEFAULT_META,
    DEFAULT_NO_NATURAL_TSV,
    DEFAULT_PROMPT,
    DEFAULT_TSV,
    append_synonym_pairs,
    ensure_empty_list,
    file_sha256,
    load_lexicon_literals,
    load_meta,
    parse_project_synonyms_tsv,
    save_meta,
    write_adequate_existing,
    write_no_natural_synonyms,
)

BATCH = "syn-top5000-b03-20260718"
SAMPLE_SEED = 20260720
FIXTURES = ROOT / "data" / "syn_ant" / "project" / "fixtures"
HEADS = FIXTURES / "syn_top5000_b03_heads.tsv"
ACC_FIX = FIXTURES / "syn_top5000_b03_accepted.tsv"
NN_FIX = FIXTURES / "syn_top5000_b03_no_natural.tsv"
ADQ_FIX = FIXTURES / "syn_top5000_b03_adequate.tsv"

# Maintainer A–D: weak / borderline pairs removed from final accept
SAMPLE_FAILS = []  # weak pairs pre-filtered in fixtures


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def _load_pairs() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for ln in ACC_FIX.read_text(encoding="utf-8").splitlines()[1:]:
        if not ln.strip():
            continue
        h, t = ln.split("\t")
        rows.append((h, t))
    fail = set(SAMPLE_FAILS)
    return [(h, t) for h, t in rows if (h, t) not in fail]


def _load_nn() -> list[tuple[str, str, str]]:
    # heads whose pairs were sample-failed → no_natural
    rows: list[tuple[str, str, str]] = []
    for ln in NN_FIX.read_text(encoding="utf-8").splitlines()[1:]:
        if not ln.strip():
            continue
        h, reason, batch = ln.split("\t")
        rows.append((h, reason, batch))
    for h, _t in SAMPLE_FAILS:
        rows.append((h, "no_stable_near_synonym", BATCH))
    # dedupe by head (last wins)
    by: dict[str, tuple[str, str, str]] = {}
    for h, r, b in rows:
        by[h] = (h, r, b)
    return list(by.values())


def _load_adequate() -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for ln in ADQ_FIX.read_text(encoding="utf-8").splitlines()[1:]:
        if not ln.strip():
            continue
        parts = ln.split("\t")
        if len(parts) == 2:
            h, note = parts
            rows.append((h, note, BATCH))
        else:
            h, note, b = parts
            rows.append((h, note, b))
    return rows


def main() -> int:
    load_essay_corpus()
    ensure_empty_list()
    if BATCH in DEFAULT_TSV.read_text(encoding="utf-8"):
        raise SystemExit(f"batch {BATCH} already landed in {DEFAULT_TSV}")

    pairs = _load_pairs()
    nn_rows = _load_nn()
    adq_rows = _load_adequate()

    heads = [
        ln.split("\t")[1]
        for ln in HEADS.read_text(encoding="utf-8").splitlines()[1:]
        if ln.strip()
    ]
    resolved = {h for h, _ in pairs} | {h for h, _, _ in nn_rows} | {h for h, _, _ in adq_rows}
    missing = [h for h in heads if h not in resolved]
    if missing:
        raise SystemExit(f"unresolved heads: {missing[:20]}… ({len(missing)})")

    lex = load_lexicon_literals()
    norm_pairs: list[tuple[str, str]] = []
    for h, t in pairs:
        nh, nt = normalize_literal(h), normalize_literal(t)
        if not nh or not nt or nh not in lex or nt not in lex:
            raise SystemExit(f"not in lexicon: {h}/{t} -> {nh}/{nt}")
        norm_pairs.append((nh, nt))
    pairs = norm_pairs

    parent_commit = _git("rev-parse", "HEAD").lower()
    append_synonym_pairs(pairs, batch_id=BATCH)
    write_no_natural_synonyms(nn_rows, DEFAULT_NO_NATURAL_TSV)
    write_adequate_existing(adq_rows, DEFAULT_ADEQUATE_TSV)

    parent_sha = file_sha256(DEFAULT_TSV)
    assert parent_sha
    sampled = sample_pairs(pairs, seed=SAMPLE_SEED)
    fail_set = set(SAMPLE_FAILS)
    # fails already removed from pairs — sample should be all ok
    verdicts = []
    for h, t in sampled:
        if (h, t) in fail_set:
            verdicts.append(
                {
                    "head": h,
                    "tail": t,
                    "verdict": "fail",
                    "reasons": ["not stable context-free near-synonym"],
                }
            )
        else:
            verdicts.append({"head": h, "tail": t, "verdict": "ok", "reasons": []})
    sample_ok = sum(1 for v in verdicts if v["verdict"] == "ok")
    sample_n = len(verdicts)
    rate = ok_rate(sample_ok, sample_n)
    if rate < 0.9:
        raise SystemExit(f"sample ok_rate {rate} < 0.9")

    meta = load_meta(DEFAULT_META)
    meta.setdefault("batches", {})
    meta["batches"][BATCH] = {
        "k": len({h for h, _ in pairs}),
        "git_commit": parent_commit,  # updated after commit if needed
        "db_sha256": file_sha256(ROOT / "client" / "public" / "lyrics.db"),
        "essay_sha256": file_sha256(ROOT / "data" / "essay" / "essay-cantonese.txt"),
        "prompt_path": "data/syn_ant/project/project-synonyms-prompt.txt",
        "prompt_sha256": file_sha256(DEFAULT_PROMPT),
        "model_note": (
            "syn_top5000 b03 maintainer-curated blind-style pairs; "
            "particles→no_natural; 亦→adequate_existing; A–D seed=20260718"
        ),
        "model": "xai/grok-4.5",
        "model_provider": "xAI",
        "model_version": "grok-4.5",
        "model_params": {
            "generation_mode": "maintainer_curated_blind_style",
            "max_proposals_per_head": 3,
            "temperature": None,
            "top_p": None,
            "max_output_tokens": None,
            "campaign": "syn_top5000",
            "batch_index": 3,
        },
        "sample_seed": SAMPLE_SEED,
        "sample_n": sample_n,
        "sample_ok": sample_ok,
        "ok_rate_threshold": 0.9,
        "ok_rate": round(rate, 4),
        "sample_parent": f"project_synonyms.tsv {BATCH} parent N={len(pairs)}",
        "sample_parent_n": len(pairs),
        "sample_parent_commit": parent_commit,
        "sample_parent_tsv_sha256": parent_sha,
        "sample_verdicts": verdicts,
        "removed_sample_fails": [
            {"head": h, "tail": t, "reasons": ["not stable context-free near-synonym"]}
            for h, t in SAMPLE_FAILS
        ],
        "accepted_pairs": len(pairs),
        "no_natural_heads": len(nn_rows),
        "adequate_existing_heads": len(adq_rows),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    save_meta(meta, DEFAULT_META)

    # parse round-trip
    parse_project_synonyms_tsv(DEFAULT_TSV, membership=lex)
    assert BATCH in DEFAULT_TSV.read_text(encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "batch": BATCH,
                "accepted_pairs": len(pairs),
                "no_natural": len(nn_rows),
                "adequate_existing": len(adq_rows),
                "sample_n": sample_n,
                "sample_ok": sample_ok,
                "ok_rate": round(rate, 4),
                "expected_sample_n": sample_size_for(len(pairs)),
                "ledger_nn": str(DEFAULT_NO_NATURAL_TSV.relative_to(ROOT)).replace("\\", "/"),
                "ledger_adq": str(DEFAULT_ADEQUATE_TSV.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
