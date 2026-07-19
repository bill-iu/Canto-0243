"""專案自建近義 campaign：高頻過稀 Top 母體 + len4 Top-K（freeze）。"""
from __future__ import annotations

import json
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Set

from app.domain.relations.valid_term import is_valid_term, normalize_literal
from app.lexicon.essay_index import get_essay_frequency
from ingest.project_synonyms import (
    DEFAULT_DB,
    DEFAULT_TSV,
    PROJECT_DIR,
    SPARSE_LT,
    ProjectSynonymsError,
    build_direct_syn_adj,
    file_sha256,
    load_lexicon_literals,
    project_syn_heads_from_tsv,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ESSAY = ROOT / "data" / "essay" / "essay-cantonese.txt"
DEFAULT_CILIN = ROOT / "data" / "cilin" / "new_cilin.txt"
DEFAULT_GUOTONG_SYN = ROOT / "data" / "thesaurus" / "dict_synonym.txt"

MANIFEST_HEADER = ("rank", "head", "essay_frequency", "batch_index", "direct_syn_tails")


@dataclass(frozen=True, slots=True)
class SynCampaignHead:
    rank: int
    head: str
    essay_frequency: int
    batch_index: int
    direct_syn_tails: int


@dataclass(frozen=True, slots=True)
class SynCampaignSpec:
    campaign_id: str
    batch_size: int
    # "essay_top_intersect_sparse" | "len4_sparse_top_k"
    mode: str
    essay_top_k: Optional[int]
    campaign_k: Optional[int]  # len4 truncate; None = all deduped sparse
    length_filter: Optional[int]
    manifest_tsv: Path
    manifest_meta: Path


TOP5000_SYN_SPEC = SynCampaignSpec(
    campaign_id="syn_top5000",
    batch_size=200,
    mode="essay_top_intersect_sparse",
    essay_top_k=5000,
    campaign_k=None,
    length_filter=None,
    manifest_tsv=PROJECT_DIR / "campaign_syn_top5000.tsv",
    manifest_meta=PROJECT_DIR / "campaign_syn_top5000.meta.json",
)

LEN4_SYN_SPEC = SynCampaignSpec(
    campaign_id="syn_len4",
    batch_size=500,
    mode="len4_sparse_top_k",
    essay_top_k=None,
    campaign_k=5000,
    length_filter=4,
    manifest_tsv=PROJECT_DIR / "campaign_syn_len4.tsv",
    manifest_meta=PROJECT_DIR / "campaign_syn_len4.meta.json",
)

_SPECS = {
    TOP5000_SYN_SPEC.campaign_id: TOP5000_SYN_SPEC,
    LEN4_SYN_SPEC.campaign_id: LEN4_SYN_SPEC,
}


def get_syn_campaign_spec(campaign_id: str) -> SynCampaignSpec:
    key = (campaign_id or "").strip().lower()
    spec = _SPECS.get(key)
    if spec is None:
        raise ProjectSynonymsError(
            f"unknown syn campaign_id {campaign_id!r}; allowed={sorted(_SPECS)}"
        )
    return spec


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
        raise ProjectSynonymsError(f"cannot resolve git ref {ref!r}: {exc}") from exc


def essay_top_in_lex(
    lex: Set[str],
    k: int,
    *,
    essay_freq: Callable[[str], int] = get_essay_frequency,
) -> List[str]:
    scored = [(lit, int(essay_freq(lit))) for lit in lex if is_valid_term(lit)]
    scored.sort(key=lambda t: (-t[1], t[0]))
    return [lit for lit, _ in scored[:k]]


def rank_syn_campaign_heads(
    *,
    spec: SynCampaignSpec,
    db_path: Path | str = DEFAULT_DB,
    essay_freq: Callable[[str], int] = get_essay_frequency,
    exclude_heads: Optional[Set[str]] = None,
    prior_campaign_heads: Optional[Set[str]] = None,
) -> List[SynCampaignHead]:
    """Freeze 排名；排除已有 project_syn 覆蓋與 prior campaign 字面。"""
    lex = load_lexicon_literals(db_path)
    adj = build_direct_syn_adj(db_path=db_path, lex=lex)
    exclude = set(exclude_heads or ())
    exclude |= set(prior_campaign_heads or ())
    try:
        exclude |= project_syn_heads_from_tsv(DEFAULT_TSV)
    except ProjectSynonymsError:
        pass

    candidates: List[tuple[str, int, int]] = []  # head, freq, tails

    if spec.mode == "essay_top_intersect_sparse":
        assert spec.essay_top_k is not None
        for head in essay_top_in_lex(lex, spec.essay_top_k, essay_freq=essay_freq):
            if head in exclude:
                continue
            tails = len(adj.get(head, ()))
            if tails >= SPARSE_LT:
                continue
            candidates.append((head, int(essay_freq(head)), tails))
    elif spec.mode == "len4_sparse_top_k":
        for head in lex:
            if len(head) != (spec.length_filter or 4):
                continue
            if not is_valid_term(head) or head in exclude:
                continue
            lit = normalize_literal(head) or head
            if lit in exclude:
                continue
            tails = len(adj.get(lit, ()))
            if tails >= SPARSE_LT:
                continue
            candidates.append((lit, int(essay_freq(lit)), tails))
        candidates.sort(key=lambda t: (-t[1], t[0]))
        if spec.campaign_k is not None:
            candidates = candidates[: spec.campaign_k]
    else:
        raise ProjectSynonymsError(f"unknown mode {spec.mode!r}")

    if spec.mode == "essay_top_intersect_sparse":
        candidates.sort(key=lambda t: (-t[1], t[0]))

    out: List[SynCampaignHead] = []
    for i, (head, freq, tails) in enumerate(candidates, start=1):
        out.append(
            SynCampaignHead(
                rank=i,
                head=head,
                essay_frequency=freq,
                batch_index=(i - 1) // spec.batch_size + 1,
                direct_syn_tails=tails,
            )
        )
    return out


def write_syn_campaign_manifest(
    heads: Sequence[SynCampaignHead], path: Path | str
) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(MANIFEST_HEADER)]
    for h in heads:
        lines.append(
            f"{h.rank}\t{h.head}\t{h.essay_frequency}\t{h.batch_index}\t{h.direct_syn_tails}"
        )
    text = "\n".join(lines) + "\n"
    p.write_text(text, encoding="utf-8")
    digest = file_sha256(p)
    if not digest:
        raise ProjectSynonymsError(f"cannot hash manifest: {p}")
    return digest


def build_syn_campaign_meta(
    heads: Sequence[SynCampaignHead],
    *,
    spec: SynCampaignSpec,
    db_path: Path | str = DEFAULT_DB,
    essay_path: Path | str = DEFAULT_ESSAY,
) -> dict:
    k = len(heads)
    if k < 1:
        raise ProjectSynonymsError("syn campaign freeze requires at least one head")
    batch_counts: Dict[str, int] = {}
    for h in heads:
        key = str(h.batch_index)
        batch_counts[key] = batch_counts.get(key, 0) + 1
    n_batches = int(math.ceil(k / spec.batch_size)) if k else 0
    return {
        "campaign_id": spec.campaign_id,
        "mode": spec.mode,
        "sparse_lt": SPARSE_LT,
        "k": k,
        "batch_size": spec.batch_size,
        "batch_count": n_batches,
        "essay_top_k": spec.essay_top_k,
        "campaign_k_cap": spec.campaign_k,
        "length_filter": spec.length_filter,
        "freeze_git_commit": _git_rev_parse("HEAD"),
        "db_sha256": file_sha256(db_path),
        "essay_sha256": file_sha256(essay_path),
        "cilin_sha256": file_sha256(DEFAULT_CILIN),
        "guotong_syn_sha256": file_sha256(DEFAULT_GUOTONG_SYN),
        "batch_counts": batch_counts,
        "sparse_zero": sum(1 for h in heads if h.direct_syn_tails == 0),
        "sparse_one": sum(1 for h in heads if h.direct_syn_tails == 1),
    }


def freeze_syn_campaign(
    *,
    campaign_id: str = "syn_top5000",
    db_path: Path | str = DEFAULT_DB,
    force: bool = False,
) -> dict:
    spec = get_syn_campaign_spec(campaign_id)
    if spec.manifest_tsv.is_file() and not force:
        raise ProjectSynonymsError(
            f"manifest exists (pass force=True to overwrite): {spec.manifest_tsv}"
        )
    prior: Set[str] = set()
    if spec.campaign_id == "syn_len4":
        # 高頻優先：若已 freeze syn_top5000，len4 排除其字面
        top_spec = TOP5000_SYN_SPEC
        if top_spec.manifest_tsv.is_file():
            for line in top_spec.manifest_tsv.read_text(encoding="utf-8").splitlines()[1:]:
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    prior.add(parts[1])

    heads = rank_syn_campaign_heads(
        spec=spec, db_path=db_path, prior_campaign_heads=prior
    )
    manifest_sha = write_syn_campaign_manifest(heads, spec.manifest_tsv)
    meta = build_syn_campaign_meta(heads, spec=spec, db_path=db_path)
    meta["manifest_sha256"] = manifest_sha
    spec.manifest_meta.parent.mkdir(parents=True, exist_ok=True)
    spec.manifest_meta.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "ok": True,
        "campaign_id": spec.campaign_id,
        "k": len(heads),
        "manifest": str(spec.manifest_tsv.relative_to(ROOT)).replace("\\", "/"),
        "meta": str(spec.manifest_meta.relative_to(ROOT)).replace("\\", "/"),
        "sparse_zero": meta["sparse_zero"],
        "sparse_one": meta["sparse_one"],
        "batch_count": meta["batch_count"],
    }


__all__ = [
    "LEN4_SYN_SPEC",
    "MANIFEST_HEADER",
    "SynCampaignHead",
    "SynCampaignSpec",
    "TOP5000_SYN_SPEC",
    "freeze_syn_campaign",
    "get_syn_campaign_spec",
    "rank_syn_campaign_heads",
    "write_syn_campaign_manifest",
]
