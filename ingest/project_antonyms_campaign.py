"""高頻 Top-5000 專案自建反義 campaign（WP-07）。

ponytail: 300-line limit exemption — campaign freeze/validate contracts stay together.
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from sqlalchemy.orm import Session

from app.domain.relations.ranking import DERIVED_ANT_SOURCES
from app.domain.relations.valid_term import is_valid_term, normalize_literal
from app.lexicon.essay_index import get_essay_frequency
from ingest.project_antonyms import (
    OK_RATE_THRESHOLD_CAMPAIGN,
    PROJECT_ANT_SOURCE,
    ProjectAntonymsError,
    chars_with_direct_ant,
    chars_with_syn,
    file_sha256,
    pair_undirected_key,
    parse_ok_rate_threshold,
    passes_quality_gate,
    sample_pairs,
    sample_size_for,
)

_GIT_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_CAMPAIGN_BATCH_COUNT = 10
_FINGERPRINT_FIELDS = ("db_sha256", "essay_sha256", "thesaurus_ant_sha256")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_TSV = ROOT / "data" / "syn_ant" / "campaign_top5000.tsv"
DEFAULT_MANIFEST_META = ROOT / "data" / "syn_ant" / "campaign_top5000.meta.json"
DEFAULT_NO_NATURAL_TSV = ROOT / "data" / "syn_ant" / "project_no_natural_antonyms.tsv"
DEFAULT_NO_NATURAL_META = ROOT / "data" / "syn_ant" / "project_no_natural_antonyms.meta.json"
DEFAULT_FINAL_AUDIT_META = ROOT / "data" / "syn_ant" / "campaign_final_audit.meta.json"
DEFAULT_THESAURUS_ANT = ROOT / "data" / "thesaurus" / "dict_antonym.txt"
DEFAULT_ESSAY = ROOT / "data" / "essay" / "essay-cantonese.txt"
FINAL_AUDIT_OK_RATE_THRESHOLD = OK_RATE_THRESHOLD_CAMPAIGN

CAMPAIGN_K = 5000
CAMPAIGN_BATCH_SIZE = 500
CAMPAIGN_BASELINE_COMMIT = "89edbb39c855e84bb36063bdd86ed8e717332bed"

MANIFEST_HEADER = ("rank", "head", "essay_frequency", "batch_index")
NO_NATURAL_HEADER = ("head", "reason", "batch_id")

# Controlled reasons only — fail-closed allowlist.
NO_NATURAL_REASONS = frozenset(
    {
        "no_gradable_opposite",
        "proper_name_or_deixis",
        "polysemous_no_stable_sense",
        "function_word",
        "cultural_no_binary",
        "other_documented",
    }
)


@dataclass(frozen=True, slots=True)
class CampaignHead:
    rank: int
    head: str
    essay_frequency: int
    batch_index: int


def campaign_exclude_sources() -> Set[str]:
    """Direct-ant sources ignored when ranking the frozen campaign."""
    return set(DERIVED_ANT_SOURCES) | {PROJECT_ANT_SOURCE}


def chars_with_direct_ant_excluding_project(
    db: Session,
    *,
    static_ant_heads: Optional[Iterable[str]] = None,
) -> Set[str]:
    """直連反義 heads，邏輯排除 project_ant（campaign freeze 用）。"""
    return chars_with_direct_ant(
        db,
        static_ant_heads=static_ant_heads,
        exclude_sources={PROJECT_ANT_SOURCE},
    )


def rank_campaign_heads(
    db: Session,
    *,
    k: int = CAMPAIGN_K,
    essay_freq: Callable[[str], int] = get_essay_frequency,
    membership: Optional[Set[str]] = None,
    static_ant_heads: Optional[Iterable[str]] = None,
) -> List[CampaignHead]:
    """有近無直連反 ∩ Essay Top-K；排除 project_ant 以免母體滑動。"""
    syns = chars_with_syn(db)
    directs = chars_with_direct_ant_excluding_project(
        db, static_ant_heads=static_ant_heads
    )
    candidates = syns - directs
    if membership is not None:
        candidates &= membership
    candidates = {c for c in candidates if is_valid_term(c)}
    ranked = sorted(candidates, key=lambda ch: (-int(essay_freq(ch)), ch))
    if k <= 0:
        return []
    out: List[CampaignHead] = []
    for i, head in enumerate(ranked[:k], start=1):
        out.append(
            CampaignHead(
                rank=i,
                head=head,
                essay_frequency=int(essay_freq(head)),
                batch_index=(i - 1) // CAMPAIGN_BATCH_SIZE + 1,
            )
        )
    return out


def _git_rev_parse(ref: str = "HEAD") -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "-C", str(ROOT), "rev-parse", ref],
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
            .lower()
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        raise ProjectAntonymsError(f"cannot resolve git ref {ref!r}: {exc}") from exc


def _require_git_sha1(value: Any, *, field: str, path: Path) -> str:
    text = str(value or "").strip().lower()
    if not _GIT_SHA1_RE.fullmatch(text):
        raise ProjectAntonymsError(f"{path}: {field} must be 40-hex git sha1")
    return text


def _require_sha256(value: Any, *, field: str, path: Path) -> str:
    text = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(text):
        raise ProjectAntonymsError(f"{path}: {field} must be 64-hex sha256")
    return text


def validate_campaign_meta(
    meta: dict[str, Any],
    *,
    path: Path | str,
    manifest_sha256: str,
) -> None:
    """Fail-closed audit of frozen campaign meta (fingerprints + shape)."""
    p = Path(path)
    if not isinstance(meta, dict) or not meta:
        raise ProjectAntonymsError(f"{p}: campaign meta must be a non-empty object")

    baseline = _require_git_sha1(meta.get("baseline_commit"), field="baseline_commit", path=p)
    if baseline != CAMPAIGN_BASELINE_COMMIT.lower():
        raise ProjectAntonymsError(
            f"{p}: baseline_commit {baseline!r} != {CAMPAIGN_BASELINE_COMMIT}"
        )
    _require_git_sha1(meta.get("freeze_git_commit"), field="freeze_git_commit", path=p)

    try:
        k = int(meta.get("k"))
        batch_size = int(meta.get("batch_size"))
        batch_count = int(meta.get("batch_count"))
    except (TypeError, ValueError) as exc:
        raise ProjectAntonymsError(
            f"{p}: k/batch_size/batch_count must be integers"
        ) from exc
    if k != CAMPAIGN_K:
        raise ProjectAntonymsError(f"{p}: k must be {CAMPAIGN_K}, got {k}")
    if batch_size != CAMPAIGN_BATCH_SIZE:
        raise ProjectAntonymsError(
            f"{p}: batch_size must be {CAMPAIGN_BATCH_SIZE}, got {batch_size}"
        )
    if batch_count != _CAMPAIGN_BATCH_COUNT:
        raise ProjectAntonymsError(
            f"{p}: batch_count must be {_CAMPAIGN_BATCH_COUNT}, got {batch_count}"
        )

    excl = meta.get("exclude_sources")
    expected_excl = sorted(campaign_exclude_sources())
    if not isinstance(excl, list) or [str(x) for x in excl] != expected_excl:
        raise ProjectAntonymsError(
            f"{p}: exclude_sources must be {expected_excl}, got {excl!r}"
        )

    for field in _FINGERPRINT_FIELDS:
        _require_sha256(meta.get(field), field=field, path=p)

    meta_manifest = _require_sha256(
        meta.get("manifest_sha256"), field="manifest_sha256", path=p
    )
    got = str(manifest_sha256 or "").strip().lower()
    if not _SHA256_RE.fullmatch(got) or meta_manifest != got:
        raise ProjectAntonymsError(
            f"{p}: manifest_sha256 mismatch meta={meta_manifest!r} file={got!r}"
        )

    counts = meta.get("batch_counts")
    if not isinstance(counts, dict):
        raise ProjectAntonymsError(f"{p}: batch_counts must be an object")
    expected_keys = {str(i) for i in range(1, _CAMPAIGN_BATCH_COUNT + 1)}
    if set(counts) != expected_keys:
        raise ProjectAntonymsError(
            f"{p}: batch_counts keys must be {sorted(expected_keys)}, got {sorted(counts)}"
        )
    for key in sorted(expected_keys, key=int):
        try:
            n = int(counts[key])
        except (TypeError, ValueError) as exc:
            raise ProjectAntonymsError(
                f"{p}: batch_counts[{key!r}] must be int"
            ) from exc
        if n != CAMPAIGN_BATCH_SIZE:
            raise ProjectAntonymsError(
                f"{p}: batch_counts[{key!r}] must be {CAMPAIGN_BATCH_SIZE}, got {n}"
            )


def build_campaign_meta(
    *,
    heads: Sequence[CampaignHead],
    db_path: Path | str,
    baseline_commit: str = CAMPAIGN_BASELINE_COMMIT,
    essay_path: Path | str = DEFAULT_ESSAY,
    thesaurus_ant_path: Path | str = DEFAULT_THESAURUS_ANT,
) -> dict[str, Any]:
    if len(heads) != CAMPAIGN_K:
        raise ProjectAntonymsError(
            f"campaign freeze requires exactly {CAMPAIGN_K} heads, got {len(heads)}"
        )
    batch_counts: Dict[int, int] = {}
    for h in heads:
        batch_counts[h.batch_index] = batch_counts.get(h.batch_index, 0) + 1
    if (
        sorted(batch_counts) != list(range(1, _CAMPAIGN_BATCH_COUNT + 1))
        or set(batch_counts.values()) != {CAMPAIGN_BATCH_SIZE}
    ):
        raise ProjectAntonymsError(
            f"expected {_CAMPAIGN_BATCH_COUNT}×{CAMPAIGN_BATCH_SIZE} batches, "
            f"got {batch_counts}"
        )
    baseline = _require_git_sha1(
        baseline_commit, field="baseline_commit", path=Path("<build>")
    )
    if baseline != CAMPAIGN_BASELINE_COMMIT.lower():
        raise ProjectAntonymsError(
            f"baseline_commit {baseline!r} != {CAMPAIGN_BASELINE_COMMIT}"
        )
    fingerprints = {
        "db_sha256": file_sha256(db_path),
        "essay_sha256": file_sha256(essay_path),
        "thesaurus_ant_sha256": file_sha256(thesaurus_ant_path),
    }
    for field, digest in fingerprints.items():
        if not digest:
            raise ProjectAntonymsError(f"missing fingerprint source for {field}")
        _require_sha256(digest, field=field, path=Path("<build>"))
    return {
        "baseline_commit": baseline,
        "freeze_git_commit": _git_rev_parse("HEAD"),
        "k": CAMPAIGN_K,
        "batch_size": CAMPAIGN_BATCH_SIZE,
        "batch_count": _CAMPAIGN_BATCH_COUNT,
        "exclude_sources": sorted(campaign_exclude_sources()),
        **fingerprints,
        "batch_counts": {
            str(i): batch_counts[i] for i in range(1, _CAMPAIGN_BATCH_COUNT + 1)
        },
    }


def render_manifest_tsv(heads: Sequence[CampaignHead]) -> str:
    lines = ["\t".join(MANIFEST_HEADER)]
    for h in heads:
        lines.append(
            f"{h.rank}\t{h.head}\t{h.essay_frequency}\t{h.batch_index}"
        )
    return "\n".join(lines) + "\n"


def write_campaign_manifest(
    heads: Sequence[CampaignHead],
    meta: dict[str, Any],
    *,
    tsv_path: Path | str = DEFAULT_MANIFEST_TSV,
    meta_path: Path | str = DEFAULT_MANIFEST_META,
) -> None:
    tsv = Path(tsv_path)
    meta_p = Path(meta_path)
    tsv.parent.mkdir(parents=True, exist_ok=True)
    text = render_manifest_tsv(heads)
    tsv.write_text(text, encoding="utf-8", newline="\n")
    meta = dict(meta)
    meta["manifest_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
    meta_p.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def parse_campaign_manifest(
    path: Path | str = DEFAULT_MANIFEST_TSV,
    *,
    meta: Optional[dict[str, Any]] = None,
    meta_path: Path | str = DEFAULT_MANIFEST_META,
    require_file: bool = True,
) -> List[CampaignHead]:
    p = Path(path)
    if not p.is_file():
        if require_file:
            raise ProjectAntonymsError(f"missing campaign manifest: {p}")
        return []
    raw = p.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ProjectAntonymsError(f"manifest must be UTF-8 without BOM: {p}")
    text = raw.decode("utf-8")
    lines = text.splitlines()
    if not lines:
        raise ProjectAntonymsError(f"empty campaign manifest: {p}")
    reader = csv.reader(lines, delimiter="\t")
    try:
        header = tuple(next(reader))
    except StopIteration as exc:
        raise ProjectAntonymsError(f"empty campaign manifest: {p}") from exc
    if header != MANIFEST_HEADER:
        raise ProjectAntonymsError(
            f"bad manifest header {header!r}; expected {MANIFEST_HEADER!r}"
        )
    out: List[CampaignHead] = []
    seen: Set[str] = set()
    for lineno, row in enumerate(reader, start=2):
        if not row or all(not c.strip() for c in row):
            continue
        if len(row) != 4:
            raise ProjectAntonymsError(
                f"{p}:{lineno}: expected 4 columns, got {len(row)}"
            )
        rank_s, head_raw, freq_s, batch_s = (c.strip() for c in row)
        try:
            rank = int(rank_s)
            freq = int(freq_s)
            batch_index = int(batch_s)
        except ValueError as exc:
            raise ProjectAntonymsError(
                f"{p}:{lineno}: non-integer rank/freq/batch_index"
            ) from exc
        head = normalize_literal(head_raw)
        if not head or not is_valid_term(head):
            raise ProjectAntonymsError(f"{p}:{lineno}: invalid head {head_raw!r}")
        if head in seen:
            raise ProjectAntonymsError(f"{p}:{lineno}: duplicate head {head}")
        if rank != len(out) + 1:
            raise ProjectAntonymsError(
                f"{p}:{lineno}: rank {rank} out of order (want {len(out) + 1})"
            )
        if batch_index != (rank - 1) // CAMPAIGN_BATCH_SIZE + 1:
            raise ProjectAntonymsError(
                f"{p}:{lineno}: batch_index {batch_index} mismatch for rank {rank}"
            )
        seen.add(head)
        out.append(
            CampaignHead(
                rank=rank, head=head, essay_frequency=freq, batch_index=batch_index
            )
        )
    if len(out) != CAMPAIGN_K:
        raise ProjectAntonymsError(
            f"{p}: expected {CAMPAIGN_K} heads, got {len(out)}"
        )
    if meta is None:
        meta = load_campaign_meta(meta_path)
    validate_campaign_meta(
        meta,
        path=meta_path,
        manifest_sha256=hashlib.sha256(raw).hexdigest(),
    )
    return out


def load_campaign_meta(path: Path | str = DEFAULT_MANIFEST_META) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise ProjectAntonymsError(f"missing campaign meta: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectAntonymsError(f"invalid campaign meta JSON: {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectAntonymsError(f"campaign meta root must be object: {p}")
    return data


def parse_no_natural_tsv(
    path: Path | str = DEFAULT_NO_NATURAL_TSV,
    *,
    campaign_heads: Optional[Set[str]] = None,
    require_file: bool = True,
) -> List[Tuple[str, str, str]]:
    """Fail-closed no-natural verdicts: head, reason, batch_id."""
    p = Path(path)
    if not p.is_file():
        if require_file:
            raise ProjectAntonymsError(f"missing no-natural TSV: {p}")
        return []
    text = p.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        raise ProjectAntonymsError(f"no-natural TSV must be UTF-8 without BOM: {p}")
    lines = text.splitlines()
    if not lines:
        raise ProjectAntonymsError(f"empty no-natural TSV (need header): {p}")
    reader = csv.reader(lines, delimiter="\t")
    try:
        header = tuple(next(reader))
    except StopIteration as exc:
        raise ProjectAntonymsError(f"empty no-natural TSV: {p}") from exc
    if header != NO_NATURAL_HEADER:
        raise ProjectAntonymsError(
            f"bad no-natural header {header!r}; expected {NO_NATURAL_HEADER!r}"
        )
    out: List[Tuple[str, str, str]] = []
    seen: Set[str] = set()
    for lineno, row in enumerate(reader, start=2):
        if not row or all(not c.strip() for c in row):
            continue
        if len(row) != 3:
            raise ProjectAntonymsError(
                f"{p}:{lineno}: expected 3 columns, got {len(row)}"
            )
        head_raw, reason, batch_id = (c.strip() for c in row)
        head = normalize_literal(head_raw)
        if not head or not is_valid_term(head):
            raise ProjectAntonymsError(f"{p}:{lineno}: invalid head")
        if reason not in NO_NATURAL_REASONS:
            raise ProjectAntonymsError(
                f"{p}:{lineno}: unknown reason {reason!r}; "
                f"allowed={sorted(NO_NATURAL_REASONS)}"
            )
        if not batch_id:
            raise ProjectAntonymsError(f"{p}:{lineno}: empty batch_id")
        if head in seen:
            raise ProjectAntonymsError(f"{p}:{lineno}: duplicate head {head}")
        if campaign_heads is not None and head not in campaign_heads:
            raise ProjectAntonymsError(
                f"{p}:{lineno}: head {head} not in campaign manifest"
            )
        seen.add(head)
        out.append((head, reason, batch_id))
    return out


def write_empty_no_natural_tsv(path: Path | str = DEFAULT_NO_NATURAL_TSV) -> None:
    """Overwrite with header-only TSV (tests / explicit wipe only)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\t".join(NO_NATURAL_HEADER) + "\n", encoding="utf-8", newline="\n")


def ensure_no_natural_tsv(path: Path | str = DEFAULT_NO_NATURAL_TSV) -> bool:
    """Create header-only no-natural TSV only if missing. Never overwrite.

    Returns True if a new file was created.
    """
    p = Path(path)
    if p.is_file():
        return False
    write_empty_no_natural_tsv(p)
    return True


def assert_first_batch_matches_seeds(
    heads: Sequence[CampaignHead],
    seeds: Sequence[str],
) -> None:
    first = [h.head for h in heads[:CAMPAIGN_BATCH_SIZE]]
    if list(seeds) != first:
        raise ProjectAntonymsError(
            "campaign first-500 heads != reference seeds.txt "
            f"(len seeds={len(seeds)}, first={first[:3]!r}, seeds={list(seeds)[:3]!r})"
        )


def accepted_coverage_heads(tsv_path: Path | str) -> Set[str]:
    """ponytail: lightweight head∪tail coverage; full pair audit stays in parse_project_antonyms_tsv."""
    from ingest.project_antonyms import DEFAULT_TSV, TSV_HEADER

    p = Path(tsv_path) if tsv_path else DEFAULT_TSV
    if not p.is_file():
        return set()
    text = p.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        raise ProjectAntonymsError(f"accepted TSV must be UTF-8 without BOM: {p}")
    lines = text.splitlines()
    if not lines:
        return set()
    reader = csv.reader(lines, delimiter="\t")
    header = tuple(next(reader, ()))
    if header != TSV_HEADER:
        raise ProjectAntonymsError(
            f"bad accepted header {header!r}; expected {TSV_HEADER!r}"
        )
    covered: Set[str] = set()
    for lineno, row in enumerate(reader, start=2):
        if not row or all(not c.strip() for c in row):
            continue
        if len(row) < 2:
            raise ProjectAntonymsError(f"{p}:{lineno}: expected head/tail columns")
        for raw in (row[0], row[1]):
            lit = normalize_literal(raw.strip())
            if lit:
                covered.add(lit)
    return covered


def assert_no_terminal_conflict(
    *,
    accepted_heads: Set[str],
    no_natural_heads: Set[str],
) -> None:
    overlap = accepted_heads & no_natural_heads
    if overlap:
        sample = ", ".join(sorted(overlap)[:5])
        raise ProjectAntonymsError(
            f"accepted/no-natural terminal conflict ({len(overlap)}): {sample}"
        )


DEFAULT_UNRESOLVED_SAMPLE = 20


def compute_campaign_progress(
    heads: Sequence[CampaignHead],
    *,
    accepted_heads: Set[str],
    no_natural_heads: Set[str],
    unresolved_sample_n: int = DEFAULT_UNRESOLVED_SAMPLE,
) -> dict[str, Any]:
    """Partition campaign heads into accepted / no-natural / unresolved by manifest batch.

    Fail-closed on terminal conflict, out-of-manifest no-natural, or impossible counts.
    """
    if unresolved_sample_n < 0:
        raise ProjectAntonymsError("unresolved_sample_n must be >= 0")
    k = len(heads)
    if k == 0:
        raise ProjectAntonymsError("campaign progress requires at least one head")
    campaign = {h.head for h in heads}
    if len(campaign) != k:
        raise ProjectAntonymsError("duplicate heads in campaign progress input")

    extra_nn = no_natural_heads - campaign
    if extra_nn:
        sample = ", ".join(sorted(extra_nn)[:5])
        raise ProjectAntonymsError(
            f"no-natural outside campaign ({len(extra_nn)}): {sample}"
        )

    accepted_in = accepted_heads & campaign
    assert_no_terminal_conflict(
        accepted_heads=accepted_in, no_natural_heads=no_natural_heads
    )

    by_batch: Dict[int, List[CampaignHead]] = {}
    for h in heads:
        by_batch.setdefault(h.batch_index, []).append(h)

    batches: List[dict[str, Any]] = []
    total_accepted = 0
    total_nn = 0
    total_unresolved = 0
    for batch_index in sorted(by_batch):
        rows = by_batch[batch_index]
        acc = [h.head for h in rows if h.head in accepted_in]
        nn = [h.head for h in rows if h.head in no_natural_heads]
        unresolved = [
            h.head
            for h in rows
            if h.head not in accepted_in and h.head not in no_natural_heads
        ]
        n_acc, n_nn, n_un = len(acc), len(nn), len(unresolved)
        if n_acc + n_nn + n_un != len(rows):
            raise ProjectAntonymsError(
                f"impossible batch {batch_index} counts: "
                f"accepted={n_acc} no_natural={n_nn} unresolved={n_un} "
                f"heads={len(rows)}"
            )
        total_accepted += n_acc
        total_nn += n_nn
        total_unresolved += n_un
        sample_n = min(unresolved_sample_n, n_un)
        batches.append(
            {
                "batch_index": batch_index,
                "heads": len(rows),
                "accepted_covered": n_acc,
                "no_natural": n_nn,
                "unresolved": n_un,
                "resolved": n_acc + n_nn,
                "unresolved_sample": unresolved[:sample_n],
            }
        )

    if total_accepted + total_nn + total_unresolved != k:
        raise ProjectAntonymsError(
            f"impossible campaign counts: accepted={total_accepted} "
            f"no_natural={total_nn} unresolved={total_unresolved} k={k}"
        )
    if total_accepted != len(accepted_in) or total_nn != len(no_natural_heads):
        raise ProjectAntonymsError(
            "impossible coverage totals vs set sizes "
            f"(accepted {total_accepted}/{len(accepted_in)}, "
            f"no_natural {total_nn}/{len(no_natural_heads)})"
        )

    resolved = total_accepted + total_nn
    return {
        "k": k,
        "accepted_covered": total_accepted,
        "no_natural": total_nn,
        "unresolved": total_unresolved,
        "resolved": resolved,
        "complete": total_unresolved == 0 and resolved == k,
        "batches": batches,
    }


def assert_campaign_complete(progress: dict[str, Any]) -> None:
    """Fail unless every campaign head has a terminal verdict."""
    k = int(progress.get("k") or 0)
    resolved = int(progress.get("resolved") or 0)
    unresolved = int(progress.get("unresolved") or 0)
    if k <= 0 or resolved != k or unresolved != 0 or not progress.get("complete"):
        raise ProjectAntonymsError(
            f"campaign incomplete: resolved={resolved}/{k} unresolved={unresolved}"
        )


def unresolved_heads_for_batch(
    heads: Sequence[CampaignHead],
    *,
    batch_index: int,
    accepted_heads: Set[str],
    no_natural_heads: Set[str],
) -> List[str]:
    """Manifest-ordered unresolved heads in one campaign batch slot."""
    if batch_index < 1:
        raise ProjectAntonymsError(f"batch_index must be >= 1, got {batch_index}")
    progress = compute_campaign_progress(
        heads,
        accepted_heads=accepted_heads,
        no_natural_heads=no_natural_heads,
        unresolved_sample_n=0,
    )
    batch_ids = {b["batch_index"] for b in progress["batches"]}
    if batch_index not in batch_ids:
        raise ProjectAntonymsError(
            f"batch_index {batch_index} not in campaign batches {sorted(batch_ids)}"
        )
    accepted_in = accepted_heads & {h.head for h in heads}
    return [
        h.head
        for h in heads
        if h.batch_index == batch_index
        and h.head not in accepted_in
        and h.head not in no_natural_heads
    ]


def sample_no_natural_rows(
    rows: Sequence[Tuple[str, str, str]],
    *,
    seed: int,
) -> List[Tuple[str, str, str]]:
    """Stable head-ASC sample of no-natural rows (head, reason, batch_id)."""
    ordered = sorted(rows, key=lambda r: r[0])
    n = len(ordered)
    size = sample_size_for(n)
    if size == 0:
        return []
    if size >= n:
        return list(ordered)
    rng = random.Random(seed)
    idxs = sorted(rng.sample(range(n), size))
    return [ordered[i] for i in idxs]


def load_no_natural_meta(path: Path | str = DEFAULT_NO_NATURAL_META) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise ProjectAntonymsError(f"missing no-natural meta: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectAntonymsError(f"invalid no-natural meta JSON: {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectAntonymsError(f"no-natural meta root must be object: {p}")
    return data


def write_empty_no_natural_meta(path: Path | str = DEFAULT_NO_NATURAL_META) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"batches": {}}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def validate_no_natural_batch_meta(
    batch_id: str,
    entry: Any,
    *,
    path: Path,
) -> None:
    """Fail-closed audit for one no-natural batch (head+reason sample gate)."""
    if not isinstance(entry, dict) or not entry:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] must be a non-empty object"
        )
    required = (
        "sample_seed",
        "sample_n",
        "sample_ok",
        "ok_rate_threshold",
        "sample_parent_n",
        "removed_sample_fails",
        "sample_verdicts",
        "git_commit",
    )
    missing = [k for k in required if k not in entry]
    if missing:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] missing fields: {', '.join(missing)}"
        )
    try:
        sample_seed = int(entry["sample_seed"])
        sample_n = int(entry["sample_n"])
        sample_ok = int(entry["sample_ok"])
        sample_parent_n = int(entry["sample_parent_n"])
    except (TypeError, ValueError) as exc:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] numeric fields invalid: {exc}"
        ) from exc
    _ = sample_seed  # validated via int(); used at replay time
    if sample_n <= 0 or sample_ok < 0 or sample_ok > sample_n:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] impossible sample counts "
            f"(ok={sample_ok}, n={sample_n})"
        )
    if sample_parent_n < sample_n:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] sample_parent_n={sample_parent_n} "
            f"< sample_n={sample_n}"
        )
    _require_git_sha1(entry["git_commit"], field="git_commit", path=path)
    threshold = parse_ok_rate_threshold(
        entry["ok_rate_threshold"],
        field="ok_rate_threshold",
        path=path,
        batch_id=batch_id,
    )
    if threshold != OK_RATE_THRESHOLD_CAMPAIGN:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] ok_rate_threshold must be "
            f"{OK_RATE_THRESHOLD_CAMPAIGN:.2f}, got {threshold:.2f}"
        )
    removed = entry.get("removed_sample_fails")
    if not isinstance(removed, list):
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] removed_sample_fails must be a list"
        )
    for i, row in enumerate(removed):
        if not isinstance(row, dict) or "head" not in row or "reason" not in row:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].removed_sample_fails[{i}] "
                f"needs head/reason"
            )
        if not str(row["head"]).strip() or not str(row["reason"]).strip():
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].removed_sample_fails[{i}] empty"
            )
        if str(row["reason"]).strip() not in NO_NATURAL_REASONS:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].removed_sample_fails[{i}] "
                f"unknown reason"
            )
    verdicts = entry.get("sample_verdicts")
    if not isinstance(verdicts, list) or len(verdicts) != sample_n:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] sample_verdicts must be a list "
            f"of length sample_n={sample_n}"
        )
    ok_n = 0
    for i, row in enumerate(verdicts):
        if not isinstance(row, dict):
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].sample_verdicts[{i}] not object"
            )
        for key in ("head", "reason", "verdict"):
            if key not in row:
                raise ProjectAntonymsError(
                    f"{path}: batches[{batch_id!r}].sample_verdicts[{i}] missing {key}"
                )
        if str(row["reason"]).strip() not in NO_NATURAL_REASONS:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].sample_verdicts[{i}] unknown reason"
            )
        verdict = str(row["verdict"]).strip().lower()
        if verdict not in ("ok", "fail"):
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].sample_verdicts[{i}] "
                f"verdict must be ok|fail"
            )
        if verdict == "ok":
            ok_n += 1
    if ok_n != sample_ok:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] sample_ok={sample_ok} != "
            f"verdicts ok count {ok_n}"
        )
    if not passes_quality_gate(sample_ok, sample_n, threshold=threshold):
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] quality gate failed: "
            f"{sample_ok}/{sample_n} < {threshold:.0%}"
        )


def assert_no_natural_sample_replayable(
    batch_id: str,
    entry: dict[str, Any],
    rows: Sequence[Tuple[str, str, str]],
    *,
    path: Path,
) -> None:
    """Replay no-natural sample.

    Sample fails are either removed from the TSV, or kept with a corrected reason
    listed in ``reason_amendments`` (from_reason = sample-time reason).
    """
    batch_rows = [(h, r, b) for h, r, b in rows if b == batch_id]
    current_by_head = {h: r for h, r, _ in batch_rows}
    removed = entry["removed_sample_fails"]
    removed_heads = {normalize_literal(str(r["head"]).strip()) for r in removed}
    removed_heads = {h for h in removed_heads if h}

    amendments_raw = entry.get("reason_amendments") or []
    if not isinstance(amendments_raw, list):
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] reason_amendments must be a list"
        )
    amended: Dict[str, Tuple[str, str]] = {}
    for i, row in enumerate(amendments_raw):
        if not isinstance(row, dict):
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].reason_amendments[{i}] not object"
            )
        head = normalize_literal(str(row.get("head") or "").strip())
        from_r = str(row.get("from_reason") or "").strip()
        to_r = str(row.get("to_reason") or "").strip()
        if not head or from_r not in NO_NATURAL_REASONS or to_r not in NO_NATURAL_REASONS:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].reason_amendments[{i}] "
                f"needs head/from_reason/to_reason"
            )
        if from_r == to_r:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].reason_amendments[{i}] "
                f"from_reason == to_reason"
            )
        if head in amended:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].reason_amendments duplicate {head}"
            )
        amended[head] = (from_r, to_r)

    if removed_heads & set(amended):
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] head cannot be both removed and amended: "
            f"{sorted(removed_heads & set(amended))}"
        )

    fail_heads: Set[str] = set()
    for i, row in enumerate(entry["sample_verdicts"]):
        if str(row["verdict"]).strip().lower() != "fail":
            continue
        head = normalize_literal(str(row["head"]).strip())
        if not head:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].sample_verdicts[{i}] invalid head"
            )
        fail_heads.add(head)
        sample_reason = str(row["reason"]).strip()
        if head in removed_heads:
            if head in current_by_head:
                raise ProjectAntonymsError(
                    f"{path}: batches[{batch_id!r}] fail head {head} still in no-natural TSV"
                )
        elif head in amended:
            from_r, to_r = amended[head]
            if sample_reason != from_r:
                raise ProjectAntonymsError(
                    f"{path}: batches[{batch_id!r}] sample_verdicts[{i}] reason "
                    f"{sample_reason!r} != amendment from_reason {from_r!r}"
                )
            if head not in current_by_head:
                raise ProjectAntonymsError(
                    f"{path}: batches[{batch_id!r}] amended fail {head} missing from TSV"
                )
            if current_by_head[head] != to_r:
                raise ProjectAntonymsError(
                    f"{path}: batches[{batch_id!r}] amended fail {head} TSV reason "
                    f"{current_by_head[head]!r} != to_reason {to_r!r}"
                )
        else:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}] sample_verdicts[{i}] fail "
                f"{head} missing from removed_sample_fails and reason_amendments"
            )
    if removed_heads - fail_heads:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] removed_sample_fails has heads "
            f"not marked fail: {sorted(removed_heads - fail_heads)}"
        )
    if set(amended) - fail_heads:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] reason_amendments has heads "
            f"not marked fail: {sorted(set(amended) - fail_heads)}"
        )

    # Later batches may cover earlier no-natural heads via accepted head∪tail.
    # Keep those heads out of the live TSV but restore them for sample-parent replay.
    superseded_raw = entry.get("superseded_heads") or []
    if not isinstance(superseded_raw, list):
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] superseded_heads must be a list"
        )
    superseded: Dict[str, str] = {}
    for i, row in enumerate(superseded_raw):
        if not isinstance(row, dict):
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].superseded_heads[{i}] not object"
            )
        head = normalize_literal(str(row.get("head") or "").strip())
        reason = str(row.get("reason") or "").strip()
        if not head or reason not in NO_NATURAL_REASONS:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].superseded_heads[{i}] needs head/reason"
            )
        if head in superseded:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].superseded_heads duplicate {head}"
            )
        if head in current_by_head:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}] superseded head {head} still in TSV"
            )
        if head in removed_heads or head in amended:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}] superseded head {head} overlaps "
                f"removed/amended"
            )
        superseded[head] = reason

    # Reconstruct sample-time parent: current rows with amended heads rolled back,
    # plus removed fails, plus later-superseded heads.
    parent: List[Tuple[str, str, str]] = []
    for h, r, b in batch_rows:
        if h in amended:
            parent.append((h, amended[h][0], b))
        else:
            parent.append((h, r, b))
    for r in removed:
        head = normalize_literal(str(r["head"]).strip())
        reason = str(r["reason"]).strip()
        if head:
            parent.append((head, reason, batch_id))
    for head, reason in superseded.items():
        parent.append((head, reason, batch_id))
    parent_n = int(entry["sample_parent_n"])
    if len(parent) != parent_n:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] reconstructed parent size "
            f"{len(parent)} != sample_parent_n={parent_n}"
        )
    if len({h for h, _, _ in parent}) != parent_n:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] reconstructed parent has duplicate heads"
        )
    sampled = sample_no_natural_rows(parent, seed=int(entry["sample_seed"]))
    expected = [
        (
            normalize_literal(str(v["head"]).strip()) or "",
            str(v["reason"]).strip(),
            batch_id,
        )
        for v in entry["sample_verdicts"]
    ]
    # Compare head+reason only (batch_id fixed).
    got = [(h, r) for h, r, _ in sampled]
    exp = [(h, r) for h, r, _ in expected]
    if got != exp:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] no-natural sample replay mismatch "
            f"(seed={entry['sample_seed']}, parent_n={parent_n})"
        )


def validate_no_natural_ledger(
    *,
    tsv_path: Path | str = DEFAULT_NO_NATURAL_TSV,
    meta_path: Path | str = DEFAULT_NO_NATURAL_META,
    campaign_heads: Optional[Set[str]] = None,
) -> List[Tuple[str, str, str]]:
    """Parse no-natural TSV and fail-closed validate referenced batch meta + replay."""
    meta = load_no_natural_meta(meta_path)
    batches = meta.get("batches")
    if not isinstance(batches, dict):
        raise ProjectAntonymsError(f"{meta_path}: batches must be an object")
    if any(not isinstance(batch_id, str) or not batch_id.strip() for batch_id in batches):
        raise ProjectAntonymsError(f"{meta_path}: batch ids must be non-empty strings")
    rows = parse_no_natural_tsv(
        tsv_path, campaign_heads=campaign_heads, require_file=True
    )
    used = {b for _, _, b in rows}
    unknown = used - set(batches)
    if unknown:
        batch_id = sorted(unknown)[0]
        raise ProjectAntonymsError(
            f"{tsv_path}: unknown batch_id {batch_id!r} (missing no-natural meta)"
        )
    for batch_id in sorted(batches):
        validate_no_natural_batch_meta(batch_id, batches[batch_id], path=Path(meta_path))
        assert_no_natural_sample_replayable(
            batch_id, batches[batch_id], rows, path=Path(meta_path)
        )
    return rows


def head_to_batch_index(heads: Sequence[CampaignHead]) -> Dict[str, int]:
    return {h.head: h.batch_index for h in heads}


def pair_campaign_batch_index(
    head: str,
    tail: str,
    head_batch: Dict[str, int],
) -> Optional[int]:
    """Attribute an undirected pair to the lowest campaign batch_index among endpoints."""
    batches = [head_batch[x] for x in (head, tail) if x in head_batch]
    return min(batches) if batches else None


def _sample_stratum_pairs(
    population: Sequence[Tuple[str, str]],
    *,
    seed: int,
) -> List[Tuple[str, str]]:
    return sample_pairs(population, seed=seed)


def _sample_stratum_no_natural(
    population: Sequence[Tuple[str, str, str]],
    *,
    seed: int,
) -> List[Tuple[str, str, str]]:
    return sample_no_natural_rows(population, seed=seed)


def stratified_sample_accepted(
    pairs: Sequence[Tuple[str, str]],
    head_batch: Dict[str, int],
    *,
    seed: int,
    batch_count: int = _CAMPAIGN_BATCH_COUNT,
) -> dict[str, Any]:
    """Per-batch_index sample of accepted pairs; empty layers skipped; total = sum(strata)."""
    by_batch: Dict[int, List[Tuple[str, str]]] = {
        i: [] for i in range(1, batch_count + 1)
    }
    seen: Set[Tuple[str, str]] = set()
    for raw_h, raw_t in pairs:
        key = pair_undirected_key(str(raw_h).strip(), str(raw_t).strip())
        if key in seen:
            continue
        bi = pair_campaign_batch_index(key[0], key[1], head_batch)
        if bi is None:
            continue
        seen.add(key)
        by_batch[bi].append(key)

    sampled: List[Tuple[str, str]] = []
    strata: List[dict[str, int]] = []
    for bi in range(1, batch_count + 1):
        pop = by_batch[bi]
        n = len(pop)
        if n == 0:
            continue
        layer_seed = seed + bi
        layer = _sample_stratum_pairs(pop, seed=layer_seed)
        sampled.extend(layer)
        strata.append(
            {
                "batch_index": bi,
                "parent_n": n,
                "sample_n": len(layer),
                "sample_seed": layer_seed,
            }
        )
    if not strata:
        return {
            "status": "skipped_empty",
            "sample_seed": seed,
            "sample_n": 0,
            "sample_parent_n": 0,
            "sampled": [],
            "strata": [],
        }
    return {
        "status": "ok",
        "sample_seed": seed,
        "sample_n": len(sampled),
        "sample_parent_n": sum(s["parent_n"] for s in strata),
        "sampled": sampled,
        "strata": strata,
    }


def stratified_sample_no_natural(
    rows: Sequence[Tuple[str, str, str]],
    head_batch: Dict[str, int],
    *,
    seed: int,
    batch_count: int = _CAMPAIGN_BATCH_COUNT,
) -> dict[str, Any]:
    """Per-batch_index sample of no-natural rows; empty layers skipped."""
    by_batch: Dict[int, List[Tuple[str, str, str]]] = {
        i: [] for i in range(1, batch_count + 1)
    }
    seen: Set[str] = set()
    for raw_h, raw_r, raw_b in rows:
        head = normalize_literal(str(raw_h).strip()) or str(raw_h).strip()
        if not head or head in seen:
            continue
        bi = head_batch.get(head)
        if bi is None:
            continue
        seen.add(head)
        by_batch[bi].append((head, str(raw_r).strip(), str(raw_b).strip()))

    sampled: List[Tuple[str, str, str]] = []
    strata: List[dict[str, int]] = []
    for bi in range(1, batch_count + 1):
        pop = by_batch[bi]
        n = len(pop)
        if n == 0:
            continue
        layer_seed = seed + bi
        layer = _sample_stratum_no_natural(pop, seed=layer_seed)
        sampled.extend(layer)
        strata.append(
            {
                "batch_index": bi,
                "parent_n": n,
                "sample_n": len(layer),
                "sample_seed": layer_seed,
            }
        )
    if not strata:
        return {
            "status": "skipped_empty",
            "sample_seed": seed,
            "sample_n": 0,
            "sample_parent_n": 0,
            "sampled": [],
            "strata": [],
        }
    return {
        "status": "ok",
        "sample_seed": seed,
        "sample_n": len(sampled),
        "sample_parent_n": sum(s["parent_n"] for s in strata),
        "sampled": sampled,
        "strata": strata,
    }


def load_final_audit_meta(path: Path | str = DEFAULT_FINAL_AUDIT_META) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise ProjectAntonymsError(f"missing final audit meta: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectAntonymsError(f"invalid final audit meta JSON: {p}: {exc}") from exc
    if not isinstance(data, dict) or not data:
        raise ProjectAntonymsError(f"final audit meta must be a non-empty object: {p}")
    return data


def _validate_final_audit_class_shape(
    class_name: str,
    entry: Any,
    *,
    path: Path,
    threshold: float,
    unit: str,
) -> None:
    """unit: 'pair' (head/tail) or 'head' (head/reason)."""
    if not isinstance(entry, dict) or not entry:
        raise ProjectAntonymsError(f"{path}: {class_name} must be a non-empty object")
    status = str(entry.get("status") or "").strip()
    if status not in ("ok", "skipped_empty"):
        raise ProjectAntonymsError(
            f"{path}: {class_name}.status must be ok|skipped_empty, got {status!r}"
        )
    required = (
        "sample_seed",
        "sample_n",
        "sample_ok",
        "sample_parent_n",
        "strata",
        "sample_verdicts",
        "removed_sample_fails",
    )
    missing = [k for k in required if k not in entry]
    if missing:
        raise ProjectAntonymsError(
            f"{path}: {class_name} missing fields: {', '.join(missing)}"
        )
    try:
        sample_seed = int(entry["sample_seed"])
        sample_n = int(entry["sample_n"])
        sample_ok = int(entry["sample_ok"])
        sample_parent_n = int(entry["sample_parent_n"])
    except (TypeError, ValueError) as exc:
        raise ProjectAntonymsError(
            f"{path}: {class_name} numeric fields invalid: {exc}"
        ) from exc
    _ = sample_seed
    strata = entry.get("strata")
    if not isinstance(strata, list):
        raise ProjectAntonymsError(f"{path}: {class_name}.strata must be a list")
    verdicts = entry.get("sample_verdicts")
    removed = entry.get("removed_sample_fails")
    if not isinstance(verdicts, list):
        raise ProjectAntonymsError(f"{path}: {class_name}.sample_verdicts must be a list")
    if not isinstance(removed, list):
        raise ProjectAntonymsError(
            f"{path}: {class_name}.removed_sample_fails must be a list"
        )

    if status == "skipped_empty":
        if sample_n != 0 or sample_ok != 0 or sample_parent_n != 0:
            raise ProjectAntonymsError(
                f"{path}: {class_name} skipped_empty requires zero sample counts"
            )
        if strata or verdicts or removed:
            raise ProjectAntonymsError(
                f"{path}: {class_name} skipped_empty requires empty strata/verdicts/removed"
            )
        return

    if sample_n <= 0 or sample_ok < 0 or sample_ok > sample_n:
        raise ProjectAntonymsError(
            f"{path}: {class_name} impossible sample counts "
            f"(ok={sample_ok}, n={sample_n})"
        )
    if sample_parent_n < sample_n:
        raise ProjectAntonymsError(
            f"{path}: {class_name} sample_parent_n={sample_parent_n} < sample_n={sample_n}"
        )
    if not strata:
        raise ProjectAntonymsError(f"{path}: {class_name} ok status needs non-empty strata")
    if len(verdicts) != sample_n:
        raise ProjectAntonymsError(
            f"{path}: {class_name} sample_verdicts length {len(verdicts)} != sample_n={sample_n}"
        )

    strata_sample_sum = 0
    strata_parent_sum = 0
    seen_bi: Set[int] = set()
    for i, layer in enumerate(strata):
        if not isinstance(layer, dict):
            raise ProjectAntonymsError(f"{path}: {class_name}.strata[{i}] not object")
        try:
            bi = int(layer["batch_index"])
            pn = int(layer["parent_n"])
            sn = int(layer["sample_n"])
            ls = int(layer["sample_seed"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ProjectAntonymsError(
                f"{path}: {class_name}.strata[{i}] invalid: {exc}"
            ) from exc
        if bi < 1 or bi in seen_bi:
            raise ProjectAntonymsError(
                f"{path}: {class_name}.strata[{i}] bad/duplicate batch_index={bi}"
            )
        seen_bi.add(bi)
        if pn <= 0 or sn <= 0 or sn > pn:
            raise ProjectAntonymsError(
                f"{path}: {class_name}.strata[{i}] impossible parent/sample counts"
            )
        if sn != sample_size_for(pn):
            raise ProjectAntonymsError(
                f"{path}: {class_name}.strata[{i}] sample_n={sn} != "
                f"sample_size_for({pn})={sample_size_for(pn)}"
            )
        if ls != int(entry["sample_seed"]) + bi:
            raise ProjectAntonymsError(
                f"{path}: {class_name}.strata[{i}] sample_seed must be "
                f"base+batch_index ({int(entry['sample_seed']) + bi})"
            )
        strata_sample_sum += sn
        strata_parent_sum += pn
    if strata_sample_sum != sample_n:
        raise ProjectAntonymsError(
            f"{path}: {class_name} sample_n={sample_n} != sum(strata)={strata_sample_sum}"
        )
    if strata_parent_sum != sample_parent_n:
        raise ProjectAntonymsError(
            f"{path}: {class_name} sample_parent_n={sample_parent_n} != "
            f"sum(strata parent)={strata_parent_sum}"
        )

    ok_n = 0
    for i, row in enumerate(verdicts):
        if not isinstance(row, dict):
            raise ProjectAntonymsError(
                f"{path}: {class_name}.sample_verdicts[{i}] not object"
            )
        keys = ("head", "tail", "verdict") if unit == "pair" else ("head", "reason", "verdict")
        for key in keys:
            if key not in row:
                raise ProjectAntonymsError(
                    f"{path}: {class_name}.sample_verdicts[{i}] missing {key}"
                )
        if unit == "head" and str(row["reason"]).strip() not in NO_NATURAL_REASONS:
            raise ProjectAntonymsError(
                f"{path}: {class_name}.sample_verdicts[{i}] unknown reason"
            )
        verdict = str(row["verdict"]).strip().lower()
        if verdict not in ("ok", "fail"):
            raise ProjectAntonymsError(
                f"{path}: {class_name}.sample_verdicts[{i}] verdict must be ok|fail"
            )
        if verdict == "ok":
            ok_n += 1
    if ok_n != sample_ok:
        raise ProjectAntonymsError(
            f"{path}: {class_name} sample_ok={sample_ok} != verdicts ok count {ok_n}"
        )

    for i, row in enumerate(removed):
        if not isinstance(row, dict):
            raise ProjectAntonymsError(
                f"{path}: {class_name}.removed_sample_fails[{i}] not object"
            )
        if unit == "pair":
            if "head" not in row or "tail" not in row:
                raise ProjectAntonymsError(
                    f"{path}: {class_name}.removed_sample_fails[{i}] needs head/tail"
                )
            if not str(row["head"]).strip() or not str(row["tail"]).strip():
                raise ProjectAntonymsError(
                    f"{path}: {class_name}.removed_sample_fails[{i}] empty"
                )
        else:
            if "head" not in row or "reason" not in row:
                raise ProjectAntonymsError(
                    f"{path}: {class_name}.removed_sample_fails[{i}] needs head/reason"
                )
            if not str(row["head"]).strip() or not str(row["reason"]).strip():
                raise ProjectAntonymsError(
                    f"{path}: {class_name}.removed_sample_fails[{i}] empty"
                )
            if str(row["reason"]).strip() not in NO_NATURAL_REASONS:
                raise ProjectAntonymsError(
                    f"{path}: {class_name}.removed_sample_fails[{i}] unknown reason"
                )

    if not passes_quality_gate(sample_ok, sample_n, threshold=threshold):
        raise ProjectAntonymsError(
            f"{path}: {class_name} quality gate failed: "
            f"{sample_ok}/{sample_n} < {threshold:.0%}"
        )


def assert_final_audit_accepted_replayable(
    entry: dict[str, Any],
    pairs: Sequence[Tuple[str, str]],
    head_batch: Dict[str, int],
    *,
    path: Path,
    batch_count: int = _CAMPAIGN_BATCH_COUNT,
) -> None:
    if str(entry.get("status")) == "skipped_empty":
        attributed = [
            (h, t)
            for h, t in pairs
            if pair_campaign_batch_index(h, t, head_batch) is not None
        ]
        if attributed:
            raise ProjectAntonymsError(
                f"{path}: accepted skipped_empty but campaign parent has "
                f"{len(attributed)} pairs"
            )
        return
    removed = entry["removed_sample_fails"]
    removed_keys = {
        pair_undirected_key(str(r["head"]).strip(), str(r["tail"]).strip()) for r in removed
    }
    current = {pair_undirected_key(h, t) for h, t in pairs}
    fail_keys: Set[Tuple[str, str]] = set()
    for i, row in enumerate(entry["sample_verdicts"]):
        if str(row["verdict"]).strip().lower() != "fail":
            continue
        key = pair_undirected_key(str(row["head"]).strip(), str(row["tail"]).strip())
        fail_keys.add(key)
        if key not in removed_keys:
            raise ProjectAntonymsError(
                f"{path}: accepted sample_verdicts[{i}] fail {key} "
                f"missing from removed_sample_fails"
            )
        if key in current:
            raise ProjectAntonymsError(
                f"{path}: accepted fail pair {key} still in accepted TSV"
            )
    if removed_keys - fail_keys:
        raise ProjectAntonymsError(
            f"{path}: accepted removed_sample_fails has pairs not marked fail: "
            f"{sorted(removed_keys - fail_keys)}"
        )

    parent = list(current | removed_keys)
    parent_n = int(entry["sample_parent_n"])
    # Only campaign-attributed pairs count toward stratified parent.
    attributed = [
        (h, t)
        for h, t in parent
        if pair_campaign_batch_index(h, t, head_batch) is not None
    ]
    if len(attributed) != parent_n:
        raise ProjectAntonymsError(
            f"{path}: accepted reconstructed campaign parent size "
            f"{len(attributed)} != sample_parent_n={parent_n}"
        )
    result = stratified_sample_accepted(
        attributed, head_batch, seed=int(entry["sample_seed"]), batch_count=batch_count
    )
    expected = [
        pair_undirected_key(str(v["head"]).strip(), str(v["tail"]).strip())
        for v in entry["sample_verdicts"]
    ]
    got = [pair_undirected_key(h, t) for h, t in result["sampled"]]
    if got != expected:
        raise ProjectAntonymsError(
            f"{path}: accepted stratified sample replay mismatch "
            f"(seed={entry['sample_seed']}, parent_n={parent_n})"
        )
    meta_strata = [
        {
            "batch_index": int(s["batch_index"]),
            "parent_n": int(s["parent_n"]),
            "sample_n": int(s["sample_n"]),
            "sample_seed": int(s["sample_seed"]),
        }
        for s in entry["strata"]
    ]
    if meta_strata != result["strata"]:
        raise ProjectAntonymsError(f"{path}: accepted strata replay mismatch")


def assert_final_audit_no_natural_replayable(
    entry: dict[str, Any],
    rows: Sequence[Tuple[str, str, str]],
    head_batch: Dict[str, int],
    *,
    path: Path,
    batch_count: int = _CAMPAIGN_BATCH_COUNT,
) -> None:
    if str(entry.get("status")) == "skipped_empty":
        attributed = [
            row
            for row in rows
            if (normalize_literal(str(row[0]).strip()) or str(row[0]).strip()) in head_batch
        ]
        if attributed:
            raise ProjectAntonymsError(
                f"{path}: no_natural skipped_empty but campaign parent has "
                f"{len(attributed)} heads"
            )
        return
    removed = entry["removed_sample_fails"]
    removed_heads = {
        normalize_literal(str(r["head"]).strip()) or str(r["head"]).strip() for r in removed
    }
    removed_heads = {h for h in removed_heads if h}
    current_by_head = {
        (normalize_literal(h) or h): (normalize_literal(h) or h, r, b) for h, r, b in rows
    }
    fail_heads: Set[str] = set()
    for i, row in enumerate(entry["sample_verdicts"]):
        if str(row["verdict"]).strip().lower() != "fail":
            continue
        head = normalize_literal(str(row["head"]).strip()) or str(row["head"]).strip()
        fail_heads.add(head)
        if head not in removed_heads:
            raise ProjectAntonymsError(
                f"{path}: no_natural sample_verdicts[{i}] fail {head} "
                f"missing from removed_sample_fails"
            )
        if head in current_by_head:
            raise ProjectAntonymsError(
                f"{path}: no_natural fail head {head} still in no-natural TSV"
            )
    if removed_heads - fail_heads:
        raise ProjectAntonymsError(
            f"{path}: no_natural removed_sample_fails has heads not marked fail: "
            f"{sorted(removed_heads - fail_heads)}"
        )

    parent: List[Tuple[str, str, str]] = list(current_by_head.values())
    for r in removed:
        head = normalize_literal(str(r["head"]).strip()) or str(r["head"]).strip()
        reason = str(r["reason"]).strip()
        if head:
            parent.append((head, reason, ""))
    attributed = [row for row in parent if row[0] in head_batch]
    parent_n = int(entry["sample_parent_n"])
    if len(attributed) != parent_n:
        raise ProjectAntonymsError(
            f"{path}: no_natural reconstructed campaign parent size "
            f"{len(attributed)} != sample_parent_n={parent_n}"
        )
    if len({h for h, _, _ in attributed}) != parent_n:
        raise ProjectAntonymsError(
            f"{path}: no_natural reconstructed parent has duplicate heads"
        )
    result = stratified_sample_no_natural(
        attributed, head_batch, seed=int(entry["sample_seed"]), batch_count=batch_count
    )
    expected = [
        (
            normalize_literal(str(v["head"]).strip()) or str(v["head"]).strip(),
            str(v["reason"]).strip(),
        )
        for v in entry["sample_verdicts"]
    ]
    got = [(h, r) for h, r, _ in result["sampled"]]
    if got != expected:
        raise ProjectAntonymsError(
            f"{path}: no_natural stratified sample replay mismatch "
            f"(seed={entry['sample_seed']}, parent_n={parent_n})"
        )
    meta_strata = [
        {
            "batch_index": int(s["batch_index"]),
            "parent_n": int(s["parent_n"]),
            "sample_n": int(s["sample_n"]),
            "sample_seed": int(s["sample_seed"]),
        }
        for s in entry["strata"]
    ]
    if meta_strata != result["strata"]:
        raise ProjectAntonymsError(f"{path}: no_natural strata replay mismatch")


def validate_final_audit_meta(
    meta: dict[str, Any],
    *,
    path: Path | str,
    manifest_sha256: str,
    accepted_pairs: Sequence[Tuple[str, str]],
    no_natural_rows: Sequence[Tuple[str, str, str]],
    heads: Sequence[CampaignHead],
) -> None:
    """Fail-closed final audit contract + stratified replay for both classes."""
    p = Path(path)
    if not isinstance(meta, dict) or not meta:
        raise ProjectAntonymsError(f"{p}: final audit meta must be a non-empty object")
    meta_manifest = _require_sha256(
        meta.get("manifest_sha256"), field="manifest_sha256", path=p
    )
    got = str(manifest_sha256 or "").strip().lower()
    if not _SHA256_RE.fullmatch(got) or meta_manifest != got:
        raise ProjectAntonymsError(
            f"{p}: manifest_sha256 mismatch meta={meta_manifest!r} file={got!r}"
        )
    _require_git_sha1(meta.get("git_commit"), field="git_commit", path=p)
    if "ok_rate_threshold" not in meta:
        raise ProjectAntonymsError(f"{p}: missing ok_rate_threshold")
    threshold = parse_ok_rate_threshold(
        meta["ok_rate_threshold"],
        field="ok_rate_threshold",
        path=p,
        batch_id="final-audit",
    )
    if threshold != FINAL_AUDIT_OK_RATE_THRESHOLD:
        raise ProjectAntonymsError(
            f"{p}: ok_rate_threshold must be {FINAL_AUDIT_OK_RATE_THRESHOLD}, got {threshold}"
        )
    accepted = meta.get("accepted")
    no_natural = meta.get("no_natural")
    _validate_final_audit_class_shape(
        "accepted", accepted, path=p, threshold=threshold, unit="pair"
    )
    _validate_final_audit_class_shape(
        "no_natural", no_natural, path=p, threshold=threshold, unit="head"
    )
    head_batch = head_to_batch_index(heads)
    assert_final_audit_accepted_replayable(
        accepted, accepted_pairs, head_batch, path=p
    )
    assert_final_audit_no_natural_replayable(
        no_natural, no_natural_rows, head_batch, path=p
    )


def accepted_pairs_light(tsv_path: Path | str) -> List[Tuple[str, str]]:
    """Final-audit input must pass the authoritative project TSV validator."""
    from ingest.project_antonyms import parse_project_antonyms_tsv

    pairs = parse_project_antonyms_tsv(tsv_path)
    return [pair.canonical_key() for pair in pairs]


__all__ = [
    "CAMPAIGN_BASELINE_COMMIT",
    "CAMPAIGN_BATCH_SIZE",
    "CAMPAIGN_K",
    "CampaignHead",
    "DEFAULT_FINAL_AUDIT_META",
    "DEFAULT_MANIFEST_META",
    "DEFAULT_MANIFEST_TSV",
    "DEFAULT_NO_NATURAL_META",
    "DEFAULT_NO_NATURAL_TSV",
    "DEFAULT_UNRESOLVED_SAMPLE",
    "FINAL_AUDIT_OK_RATE_THRESHOLD",
    "MANIFEST_HEADER",
    "NO_NATURAL_HEADER",
    "NO_NATURAL_REASONS",
    "accepted_coverage_heads",
    "accepted_pairs_light",
    "assert_campaign_complete",
    "assert_final_audit_accepted_replayable",
    "assert_final_audit_no_natural_replayable",
    "assert_first_batch_matches_seeds",
    "assert_no_natural_sample_replayable",
    "assert_no_terminal_conflict",
    "build_campaign_meta",
    "campaign_exclude_sources",
    "chars_with_direct_ant_excluding_project",
    "compute_campaign_progress",
    "ensure_no_natural_tsv",
    "head_to_batch_index",
    "load_campaign_meta",
    "load_final_audit_meta",
    "load_no_natural_meta",
    "pair_campaign_batch_index",
    "parse_campaign_manifest",
    "parse_no_natural_tsv",
    "rank_campaign_heads",
    "render_manifest_tsv",
    "sample_no_natural_rows",
    "stratified_sample_accepted",
    "stratified_sample_no_natural",
    "unresolved_heads_for_batch",
    "validate_campaign_meta",
    "validate_final_audit_meta",
    "validate_no_natural_batch_meta",
    "validate_no_natural_ledger",
    "write_campaign_manifest",
    "write_empty_no_natural_meta",
    "write_empty_no_natural_tsv",
]
