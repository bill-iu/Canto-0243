"""Build reviewed word familiarity from pinned observations and explicit judgments.

Maintainer-only: no corpus download or statistical inference runs in the product.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import lzma
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.lexicon.essay_index import get_essay_frequency
from app.lexicon.word_usage import reset_word_usage_for_tests
from app.utils.trad_chinese import to_traditional
from ingest.lexicon_build import collect_lexicon_candidates

PIN = "7cb5fb36add76b83a266d1967536e1a1d3faa513"
CORPUS_SHA = "7744ecfeede7e7b53ae95107ba828ab66f32f545cdc474813eb3c38bc035e2a2"
BASE = ROOT / "data/lexicon"
FIELDS = ["char", "usage_rank", "basis", "essay_frequency", "subtitle_count", "subtitle_channels", "note", "action"]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def observations(archive: Path, inventory: set[str], cache: Path | None) -> dict:
    if sha(archive) != CORPUS_SHA:
        raise ValueError("TUBELEX source fingerprint mismatch")
    inventory_sha = hashlib.sha256("\n".join(sorted(inventory)).encode()).hexdigest()
    if cache and cache.is_file():
        saved = json.loads(cache.read_text(encoding="utf-8"))
        if saved.get("corpus_sha256") == CORPUS_SHA and saved.get("inventory_sha256") == inventory_sha:
            return saved["observed"]
    observed: dict[str, dict] = {}
    text = lzma.decompress(archive.read_bytes()).decode("utf-8")
    for raw in csv.DictReader(io.StringIO(text), delimiter="\t"):
        literal = to_traditional(raw["word"])
        if literal not in inventory:
            continue
        item = observed.setdefault(literal, {"count": 0, "channels": 0})
        item["count"] += int(raw["count"])
        # Different written forms may occur in the same channel. This is a lower
        # bound, never an invented distinct-channel union.
        item["channels"] = max(item["channels"], int(raw["channels"]))
    if cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"corpus_sha256": CORPUS_SHA, "inventory_sha256": inventory_sha, "observed": observed}, ensure_ascii=False), encoding="utf-8", newline="\n")
    return observed


def judgments(path: Path, inventory: set[str]) -> dict[str, tuple[int, str]]:
    if not path.is_file():
        return {}
    out: dict[str, tuple[int, str]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            literal = to_traditional(row["char"])
            rank, note = int(row["usage_rank"]), row["note"].strip()
            if literal not in inventory or rank not in range(4) or not note or any(c in note for c in "\t\r\n"):
                raise ValueError(f"Invalid contextual word judgment: {literal}")
            value = rank, note
            if literal in out and out[literal] != value:
                raise ValueError(f"Conflicting contextual word judgment: {literal}")
            out[literal] = value
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--observed-cache", type=Path)
    args = parser.parse_args()
    curated_path = BASE / "curated_lexicon.json"
    original = json.loads(curated_path.read_text(encoding="utf-8"))
    curated = {to_traditional(r["char"]) for r in original}
    reset_word_usage_for_tests()
    inventory = {r.char for r in collect_lexicon_candidates(use_layer_cache=True)} | curated
    observed = observations(args.corpus, inventory, args.observed_cache)
    review_path = BASE / "word_usage_judgments.tsv"
    review = judgments(review_path, inventory)
    output = []
    pending = []
    for literal in sorted(set(observed) | curated | set(review)):
        essay = get_essay_frequency(literal)
        counts = observed.get(literal)
        channels = counts["channels"] if counts else 0
        rank = 0 if channels >= 20 or essay >= 1000 else 1 if channels >= 5 or essay >= 500 else 2
        basis = "tubelex" if counts else "essay" if essay else "pending"
        note = ""
        if literal in review:
            rank, note = review[literal]
            basis = "ai-context"
        elif basis == "pending":
            pending.append(literal)
        output.append(dict(zip(FIELDS, [literal, rank, basis, essay, counts["count"] if counts else "", channels, note, "withdraw_curated" if rank == 3 else "keep"])))
    if pending:
        raise ValueError(f"Review word familiarity before building ({len(pending)} pending): {', '.join(pending[:12])}")
    out = BASE / "word_usage.tsv"
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(output)
    withdrawn = {r["char"] for r in output if r["action"] == "withdraw_curated" and r["char"] in curated}
    meta = dict(
        date="2026-11-06", corpus_repository="https://github.com/naist-nlp/tubelex", corpus_commit=PIN,
        corpus_path="frequencies/tubelex-zh.tsv.xz", corpus_sha256=CORPUS_SHA, corpus_license="BSD-3-Clause",
        corpus_total_word_tokens=18021001, source_normalization="Existing project s2hk and exact lexical restorations; spelling counts summed, channel range uses maximum as a lower bound",
        reviewer="AI-assisted word familiarity judgments; not human item-by-item approval or measured phrase frequencies",
        grade_labels=["日常高頻", "通用書面與填詞", "較少用或專門", "冷僻退回"],
        automatic_bands="0: subtitle channels>=20 or Essay>=1000; 1: channels>=5 or Essay>=500; otherwise 2. Absence alone never withdraws a word.",
        curated_sha256=sha(curated_path), output_sha256=sha(out), judgments_sha256=sha(review_path) if review_path.is_file() else None,
        curated_literals=len(curated), observed_literals=len(observed), graded_literals=len(output),
        contextual_judgments=len(review), pending_curated_literals=len(pending),
        curated_grades=dict(Counter(str(r["usage_rank"]) for r in output if r["char"] in curated)),
        withdrawn_curated_literals=len(withdrawn), withdrawn_curated_readings=sum(to_traditional(r["char"]) in withdrawn for r in original),
        validation={},
    )
    out.with_suffix(".meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: meta[k] for k in ["curated_literals", "observed_literals", "contextual_judgments", "pending_curated_literals", "curated_grades", "withdrawn_curated_literals", "withdrawn_curated_readings"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
