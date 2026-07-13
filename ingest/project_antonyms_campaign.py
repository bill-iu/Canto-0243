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
    PROJECT_ANT_SOURCE,
    ProjectAntonymsError,
    chars_with_direct_ant,
    chars_with_syn,
    file_sha256,
    parse_ok_rate_threshold,
    passes_quality_gate,
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
DEFAULT_THESAURUS_ANT = ROOT / "data" / "thesaurus" / "dict_antonym.txt"
DEFAULT_ESSAY = ROOT / "data" / "essay" / "essay-cantonese.txt"

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
    """Replay no-natural sample; fails must be removed from TSV rows for batch."""
    batch_rows = [(h, r, b) for h, r, b in rows if b == batch_id]
    removed = entry["removed_sample_fails"]
    removed_heads = {normalize_literal(str(r["head"]).strip()) for r in removed}
    removed_heads = {h for h in removed_heads if h}
    current_heads = {h for h, _, _ in batch_rows}
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
        if head not in removed_heads:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}] sample_verdicts[{i}] fail "
                f"{head} missing from removed_sample_fails"
            )
        if head in current_heads:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}] fail head {head} still in no-natural TSV"
            )
    if removed_heads - fail_heads:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] removed_sample_fails has heads "
            f"not marked fail: {sorted(removed_heads - fail_heads)}"
        )

    parent: List[Tuple[str, str, str]] = list(batch_rows)
    for r in removed:
        head = normalize_literal(str(r["head"]).strip())
        reason = str(r["reason"]).strip()
        if head:
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
    batches = meta.get("batches") or {}
    if not isinstance(batches, dict):
        raise ProjectAntonymsError(f"{meta_path}: batches must be an object")
    rows = parse_no_natural_tsv(
        tsv_path, campaign_heads=campaign_heads, require_file=True
    )
    used = {b for _, _, b in rows}
    for batch_id in sorted(used):
        if batch_id not in batches:
            raise ProjectAntonymsError(
                f"{tsv_path}: unknown batch_id {batch_id!r} (missing no-natural meta)"
            )
        validate_no_natural_batch_meta(batch_id, batches[batch_id], path=Path(meta_path))
        assert_no_natural_sample_replayable(
            batch_id, batches[batch_id], rows, path=Path(meta_path)
        )
    return rows


__all__ = [
    "CAMPAIGN_BASELINE_COMMIT",
    "CAMPAIGN_BATCH_SIZE",
    "CAMPAIGN_K",
    "CampaignHead",
    "DEFAULT_MANIFEST_META",
    "DEFAULT_MANIFEST_TSV",
    "DEFAULT_NO_NATURAL_META",
    "DEFAULT_NO_NATURAL_TSV",
    "DEFAULT_UNRESOLVED_SAMPLE",
    "MANIFEST_HEADER",
    "NO_NATURAL_HEADER",
    "NO_NATURAL_REASONS",
    "accepted_coverage_heads",
    "assert_campaign_complete",
    "assert_first_batch_matches_seeds",
    "assert_no_natural_sample_replayable",
    "assert_no_terminal_conflict",
    "build_campaign_meta",
    "campaign_exclude_sources",
    "chars_with_direct_ant_excluding_project",
    "compute_campaign_progress",
    "ensure_no_natural_tsv",
    "load_campaign_meta",
    "load_no_natural_meta",
    "parse_campaign_manifest",
    "parse_no_natural_tsv",
    "rank_campaign_heads",
    "render_manifest_tsv",
    "sample_no_natural_rows",
    "unresolved_heads_for_batch",
    "validate_campaign_meta",
    "validate_no_natural_batch_meta",
    "validate_no_natural_ledger",
    "write_campaign_manifest",
    "write_empty_no_natural_meta",
    "write_empty_no_natural_tsv",
]
