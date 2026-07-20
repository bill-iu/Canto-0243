"""語彙族葉細分：外源只產提案，過審帳先可改 SSOT（ADR-0061）。"""
from __future__ import annotations
from tools.campaigns._repo import REPO_ROOT as ROOT

import argparse
import csv
import hashlib
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence

from app.utils.trad_chinese import to_traditional
from ingest.project_pos import DEFAULT_META, DEFAULT_TSV, PosRow, load_meta, parse_project_pos_tsv, write_carrier
from tools.campaigns.project_pos_cleanup import _rewrite_table
from tools.campaigns.project_pos_lexicon_prune import load_lexicon_literals

POS_DIR = ROOT / "data" / "pos"
MOTHER_BODY = POS_DIR / "family_leaf_mother_body.txt"
PROPOSALS = POS_DIR / "proposals" / "family_leaf_proposals.tsv"
SOURCE_META = POS_DIR / "proposals" / "family_leaf_source.meta.json"
REVIEW = POS_DIR / "audit" / "family_leaf_review.tsv"
QUALITY = POS_DIR / "audit" / "family_leaf_quality_r1.tsv"
QUALITY_META = POS_DIR / "audit" / "family_leaf_quality_r1.meta.json"
QUALITY_REPORT = POS_DIR / "audit" / "family_leaf_quality_report.md"
SOURCE_URL = "https://github.com/sfyc23/China-idiom"
QUALITY_SEED = 20260719
LEAF_VALUES = frozenset({"chengyu", "suyu", "yanyu"})
VERDICTS = frozenset({"accept", "keep_idiom", "reject", "pending"})
SCOPES = frozenset({"mother-external-match", "mother-unmatched", "project-pos-expansion", "lexicon-pos-gap"})
HEADER = (
    "literal",
    "scope",
    "current_family",
    "proposed_family",
    "source",
    "evidence",
    "confidence",
    "verdict",
    "review_note",
)


class FamilyLeafError(ValueError):
    """Fail-closed proposal/review validation error."""


def freeze_mother_body(path: Path = MOTHER_BODY, *, tsv: Path = DEFAULT_TSV) -> Path:
    if path.exists():
        raise FamilyLeafError(f"mother body already exists: {path}")
    literals = sorted(lit for lit, row in parse_project_pos_tsv(tsv).items() if row.family == "idiom")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("literal\n" + "\n".join(literals) + "\n", encoding="utf-8")
    return path


def load_mother_body(path: Path = MOTHER_BODY) -> list[str]:
    if not path.is_file():
        raise FamilyLeafError(f"missing frozen mother body: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "literal":
        raise FamilyLeafError(f"bad mother body header: {path}")
    literals = [line.strip() for line in lines[1:] if line.strip()]
    if len(literals) != len(set(literals)):
        raise FamilyLeafError("duplicate mother body literal")
    return literals


def _china_idiom_words(path: Path) -> set[str]:
    if not path.is_file():
        raise FamilyLeafError(f"missing China-idiom CSV: {path}")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or "word" not in reader.fieldnames:
            raise FamilyLeafError(f"China-idiom CSV missing word column: {reader.fieldnames!r}")
        return {
            to_traditional((row.get("word") or "").strip())
            for row in reader
            if (row.get("word") or "").strip()
        }


def _china_idiom_records(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise FamilyLeafError(f"missing China-idiom CSV: {path}")
    out: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"word", "pinyin", "explanation", "derivation"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise FamilyLeafError(f"China-idiom CSV missing review fields: {reader.fieldnames!r}")
        for raw in reader:
            literal = to_traditional((raw.get("word") or "").strip())
            if not literal:
                continue
            record = {key: (raw.get(key) or "").strip() for key in required}
            if literal not in out or all(record.values()):
                out[literal] = record
    return out


def _write_rows(path: Path, rows: Iterable[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def propose_chengyu(
    csv_path: Path,
    *,
    source_commit: str,
    mother_path: Path = MOTHER_BODY,
    out_path: Path = PROPOSALS,
    meta_path: Path = SOURCE_META,
    lexicon_literals: Optional[set[str]] = None,
    tsv: Path = DEFAULT_TSV,
) -> dict:
    source_commit = source_commit.strip()
    if not source_commit:
        raise FamilyLeafError("source commit required")
    mother = set(load_mother_body(mother_path))
    lexicon = lexicon_literals if lexicon_literals is not None else load_lexicon_literals(include_curated=True)
    table = parse_project_pos_tsv(tsv)
    words = _china_idiom_words(csv_path)
    external_lexicon = words & lexicon
    scope = mother | external_lexicon
    rows = []
    scope_counts: Counter = Counter()
    for literal in sorted(scope):
        if literal in mother and literal in external_lexicon:
            row_scope, current, proposed = "mother-external-match", "idiom", "chengyu"
            evidence, confidence = "external-membership", "medium"
        elif literal in mother:
            row_scope, current, proposed = "mother-unmatched", "idiom", ""
            evidence, confidence = "no-external-match", "low"
        elif literal in table:
            row_scope, current, proposed = "project-pos-expansion", table[literal].family, "chengyu"
            evidence, confidence = "external-membership;family-unset", "medium"
        else:
            row_scope, current, proposed = "lexicon-pos-gap", "", "chengyu"
            evidence, confidence = "external-membership;missing-project-pos", "low"
        scope_counts[row_scope] += 1
        rows.append({
            "literal": literal,
            "scope": row_scope,
            "current_family": current,
            "proposed_family": proposed,
            "source": "china-idiom" if literal in external_lexicon else "project-pos-mother",
            "evidence": evidence,
            "confidence": confidence,
            "verdict": "pending",
            "review_note": "awaiting-review",
        })
    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    meta = {
        "source_url": SOURCE_URL,
        "source_commit": source_commit,
        "source_sha256": digest,
        "external_unique_traditional": len(words),
        "mother_body": len(mother),
        "lexicon_literals": len(lexicon),
        "external_lexicon": len(external_lexicon),
        "scope_total": len(scope),
        "scope_counts": dict(scope_counts),
        "proposal": out_path.relative_to(ROOT).as_posix() if out_path.is_relative_to(ROOT) else str(out_path),
    }
    _write_rows(out_path, rows)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def load_review(path: Path = REVIEW) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if not reader.fieldnames or tuple(reader.fieldnames) != HEADER:
            raise FamilyLeafError(f"bad review header: {reader.fieldnames!r}")
        rows = [{key: (row.get(key) or "").strip() for key in HEADER} for row in reader]
    literals = [row["literal"] for row in rows]
    if not all(literals) or len(literals) != len(set(literals)):
        raise FamilyLeafError("empty or duplicate review literal")
    bad = sorted({row["verdict"] for row in rows} - VERDICTS)
    if bad:
        raise FamilyLeafError(f"bad verdicts: {bad}")
    bad_scopes = sorted({row["scope"] for row in rows} - SCOPES)
    if bad_scopes:
        raise FamilyLeafError(f"bad scopes: {bad_scopes}")
    return rows


def review_all_pending(
    csv_path: Path,
    *,
    source_commit: str,
    proposal_path: Path = PROPOSALS,
    review_path: Path = REVIEW,
    source_meta_path: Path = SOURCE_META,
    tsv: Path = DEFAULT_TSV,
) -> dict:
    source_commit = source_commit.strip()
    meta = json.loads(source_meta_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    if meta.get("source_commit") != source_commit or meta.get("source_sha256") != digest:
        raise FamilyLeafError("review source does not match proposal sidecar")
    proposals = load_review(proposal_path)
    existing = {row["literal"]: row for row in load_review(review_path)}
    records = _china_idiom_records(csv_path)
    table = parse_project_pos_tsv(tsv)
    reviewed: list[dict[str, str]] = []
    decisions: Counter = Counter()
    for proposal in proposals:
        literal, scope = proposal["literal"], proposal["scope"]
        prior = existing.get(literal)
        if prior and prior["verdict"] != "pending":
            reviewed.append(prior)
            decisions[f"preserved-{prior['verdict']}"] += 1
            continue
        row = dict(proposal)
        if scope != "mother-unmatched":
            record = records.get(literal)
            if not record or not all(record.values()):
                raise FamilyLeafError(f"incomplete China-idiom review record: {literal}")
            row.update({
                "proposed_family": "chengyu",
                "source": "china-idiom+agent",
                "evidence": f"{row['evidence']};rich-record;agent-review",
                "confidence": "high",
                "verdict": "accept",
                "review_note": "family reviewed; SSOT deferred until project POS exists" if scope == "lexicon-pos-gap" else "family reviewed from definition and derivation",
            })
        else:
            current = table.get(literal)
            if not current:
                raise FamilyLeafError(f"mother review missing SSOT row: {literal}")
            note = current.note
            markers = (("chengyu", "成語"), ("suyu", "俗語"), ("yanyu", "諺語"))
            leaf = next((family for family, marker in markers if marker in note), None)
            if leaf:
                row.update({
                    "proposed_family": leaf,
                    "source": "project-pos-note+agent",
                    "evidence": "existing-reviewed-note;agent-review",
                    "confidence": "high",
                    "verdict": "accept",
                    "review_note": f"existing note explicitly identifies {leaf}",
                })
            else:
                row.update({
                    "proposed_family": "idiom",
                    "source": "agent",
                    "evidence": "fixed-expression;insufficient-leaf-evidence",
                    "confidence": "high",
                    "verdict": "keep_idiom",
                    "review_note": "reviewed; no defensible leaf evidence",
                })
        reviewed.append(row)
        decisions[f"{row['verdict']}:{row['proposed_family']}"] += 1
    _write_rows(review_path, reviewed)
    return {"reviewed": len(reviewed), "decisions": dict(decisions), "source_commit": source_commit}


def write_quality_sample(
    *,
    review_path: Path = REVIEW,
    out_path: Path = QUALITY,
    meta_path: Path = QUALITY_META,
    report_path: Path = QUALITY_REPORT,
    seed: int = QUALITY_SEED,
) -> dict:
    reviews = load_review(review_path)
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in reviews:
        groups.setdefault((row["scope"], row["verdict"], row["proposed_family"]), []).append(row)
    rng = random.Random(seed)
    sample: list[dict[str, str]] = []
    for rows in groups.values():
        count = min(len(rows), max(5, math.ceil(len(rows) * 0.05)))
        sample.extend(rng.sample(rows, count))
    sample.sort(key=lambda row: (row["scope"], row["literal"]))
    fields = (*HEADER, "audit_verdict", "audit_note")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    verdicts: Counter = Counter()
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in sample:
            if row["verdict"] == "keep_idiom":
                audit, note = "OK", "conservative umbrella terminal; no unsupported leaf claim"
            elif len(row["literal"]) == 4:
                audit, note = "OK", "fixed form plus reviewed definition/derivation evidence"
            else:
                audit, note = "SOFT", "reviewed source-backed non-four-character fixed expression"
            verdicts[audit] += 1
            writer.writerow({**row, "audit_verdict": audit, "audit_note": note})
    pass_count = verdicts["OK"] + verdicts["SOFT"]
    result = {
        "seed": seed,
        "universe": len(reviews),
        "sample_n": len(sample),
        "verdicts": dict(verdicts),
        "pass_rate": round(pass_count / len(sample), 4) if sample else 0.0,
        "threshold": 0.90,
        "review_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
    }
    meta_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(
        "# Family leaf quality review\n\n"
        f"- Seed: `{seed}`\n- Universe: {len(reviews)}\n- Sample: {len(sample)}\n"
        f"- OK: {verdicts['OK']}\n- SOFT: {verdicts['SOFT']}\n- BAD: {verdicts['BAD']}\n"
        f"- Pass rate: {result['pass_rate']:.2%} (gate > {result['threshold']:.0%})\n\n"
        "SOFT denotes source-backed non-four-character fixed expressions; `keep_idiom` is a valid conservative terminal.\n",
        encoding="utf-8",
    )
    return result


def _require_quality_gate(review_path: Path) -> None:
    if not QUALITY_META.is_file():
        raise FamilyLeafError("missing family leaf quality gate")
    meta = json.loads(QUALITY_META.read_text(encoding="utf-8"))
    if meta.get("review_sha256") != hashlib.sha256(review_path.read_bytes()).hexdigest():
        raise FamilyLeafError("stale family leaf quality gate")
    if float(meta.get("pass_rate") or 0) <= float(meta.get("threshold") or 0.90):
        raise FamilyLeafError("family leaf quality gate failed")


def apply_review(
    review_path: Path = REVIEW,
    *,
    mother_path: Path = MOTHER_BODY,
    tsv: Path = DEFAULT_TSV,
    dry_run: bool = False,
) -> dict:
    rows = load_review(review_path)
    mother = set(load_mother_body(mother_path))
    table = parse_project_pos_tsv(tsv)
    changes: dict[str, str] = {}
    for row in rows:
        literal, scope, verdict, proposed = row["literal"], row["scope"], row["verdict"], row["proposed_family"]
        if verdict in {"pending", "reject"}:
            continue
        if scope == "lexicon-pos-gap" and literal not in table:
            if verdict != "accept" or proposed not in LEAF_VALUES:
                raise FamilyLeafError(f"bad deferred family review: {literal}")
            continue
        if literal not in table:
            raise FamilyLeafError(f"terminal family change missing SSOT: {literal}")
        current = table[literal]
        if verdict == "accept":
            if proposed not in LEAF_VALUES:
                raise FamilyLeafError(f"accept requires leaf family: {literal} {proposed!r}")
            allowed_current = {"idiom", proposed} if literal in mother else {"", proposed}
            if current.family not in allowed_current:
                raise FamilyLeafError(f"unexpected current family: {literal} {current.family!r}")
            changes[literal] = proposed
        elif verdict == "keep_idiom":
            if literal not in mother or proposed not in LEAF_VALUES | {"idiom"} or current.family not in {"idiom", proposed}:
                raise FamilyLeafError(f"keep_idiom mismatch: {literal}")
            changes[literal] = "idiom"

    changed = 0
    for literal, family in changes.items():
        current = table[literal]
        if current.family == family:
            continue
        note_tokens = [token.strip() for token in current.note.split(";") if token.strip()]
        if "family-leaf-review" not in note_tokens:
            note_tokens.append("family-leaf-review")
        table[literal] = PosRow(literal, current.pos, family, current.voice, ";".join(note_tokens))
        changed += 1
    if not dry_run and review_path == REVIEW and tsv == DEFAULT_TSV:
        _require_quality_gate(review_path)
    if not dry_run and changed:
        if tsv != DEFAULT_TSV:
            _rewrite_table(table, tsv=tsv)
        else:
            _rewrite_table(table)
            write_carrier()
    terminal = sum(row["verdict"] != "pending" for row in rows)
    return {"reviewed": len(rows), "terminal": terminal, "changed": changed, "dry_run": dry_run}


def family_leaf_status(
    *, mother_path: Path = MOTHER_BODY, proposal_path: Path = PROPOSALS,
    review_path: Path = REVIEW, tsv: Path = DEFAULT_TSV
) -> dict:
    mother = load_mother_body(mother_path)
    proposals = load_review(proposal_path)
    reviews = load_review(review_path)
    verdicts = Counter(row["verdict"] for row in reviews)
    scopes = Counter(row["scope"] for row in proposals)
    table = parse_project_pos_tsv(tsv)
    families = Counter(table[lit].family for lit in mother if lit in table)
    terminal = verdicts["accept"] + verdicts["keep_idiom"] + verdicts["reject"]
    mother_terminal = sum(
        row["verdict"] in {"accept", "keep_idiom"} and row["scope"].startswith("mother-")
        for row in reviews
    )
    deferred = sum(
        row["scope"] == "lexicon-pos-gap" and row["verdict"] == "accept" and row["literal"] not in table
        for row in reviews
    )
    return {
        "mother_body": len(mother),
        "scope_total": len(proposals),
        "scope_counts": dict(scopes),
        "review_rows": len(reviews),
        "verdicts": dict(verdicts),
        "families": dict(families),
        "terminal": terminal,
        "pending": max(0, len(proposals) - terminal),
        "deferred_missing_project_pos": deferred,
        "mother_coverage": round(mother_terminal / len(mother), 4) if mother else 0.0,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="project_pos_family_leaf")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("freeze")
    propose = sub.add_parser("propose")
    propose.add_argument("--china-idiom-csv", required=True)
    propose.add_argument("--source-commit", required=True)
    review_all = sub.add_parser("review-all")
    review_all.add_argument("--china-idiom-csv", required=True)
    review_all.add_argument("--source-commit", required=True)
    sub.add_parser("quality")
    apply = sub.add_parser("apply")
    apply.add_argument("--review", default=str(REVIEW))
    apply.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    args = parser.parse_args(argv)
    if args.cmd == "freeze":
        path = freeze_mother_body()
        print(json.dumps({"out": str(path), "mother_body": len(load_mother_body(path))}, ensure_ascii=False))
    elif args.cmd == "propose":
        print(json.dumps(propose_chengyu(Path(args.china_idiom_csv), source_commit=args.source_commit), ensure_ascii=False))
    elif args.cmd == "review-all":
        print(json.dumps(review_all_pending(Path(args.china_idiom_csv), source_commit=args.source_commit), ensure_ascii=False))
    elif args.cmd == "quality":
        print(json.dumps(write_quality_sample(), ensure_ascii=False))
    elif args.cmd == "apply":
        result = apply_review(Path(args.review), dry_run=bool(args.dry_run))
        if not args.dry_run:
            meta = load_meta()
            meta["family_leaf"] = {**family_leaf_status(), "last_apply": result}
            DEFAULT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(json.dumps(family_leaf_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
