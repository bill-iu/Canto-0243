"""專案自建反義：種子／過濾／抽樣／清單 loader（CONTEXT § 專案自建反義*）。

ponytail: 300-line limit exemption — batch meta fail-closed audit + TSV loader stay co-located for one trust boundary.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from sqlalchemy.orm import Session, aliased

from app.domain.relations.bulk_insert import RelationTuple, normalize_relation_tuple
from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.ranking import DERIVED_ANT_SOURCES
from app.domain.relations.valid_term import is_valid_term, normalize_literal
from app.lexicon.essay_index import get_essay_frequency
from app.models.word import Word, WordRelation

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TSV = ROOT / "data" / "syn_ant" / "project_antonyms.tsv"
DEFAULT_META = ROOT / "data" / "syn_ant" / "project_antonyms.meta.json"
DEFAULT_PROMPT = ROOT / "data" / "syn_ant" / "project-antonyms-prompt.txt"

PROJECT_ANT_SOURCE = "project_ant"
PROJECT_ANT_SCORE = 0.85
PROJECT_ANT_MERGE_RANK = 12
PROJECT_ANT_RUNTIME_RANK = 12
TSV_HEADER = ("head", "tail", "relation_type", "batch_id")
MAX_PROPOSALS_PER_HEAD = 3
MAX_ACCEPTED_PER_HEAD = 5
DEFAULT_SEED_K = 500
OK_RATE_THRESHOLD = 0.85  # legacy default; batch meta must declare ok_rate_threshold
OK_RATE_THRESHOLD_CAMPAIGN = 0.90
ALLOWED_OK_RATE_THRESHOLDS = frozenset({OK_RATE_THRESHOLD, OK_RATE_THRESHOLD_CAMPAIGN})
LEGACY_BATCH_ID = "batch-20260713"

_GIT_SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MODEL_PROVIDER_RE = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
_MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}$")
_WORKFLOW_MODEL_TOKENS = ("agent", "blind", "draft", "workflow", "cursor")
_GEN_CONTROL_KEYS = ("temperature", "top_p", "max_output_tokens")


class ProjectAntonymsError(ValueError):
    """Fail-closed validation / load error."""


@dataclass(frozen=True, slots=True)
class ProjectAntPair:
    head: str
    tail: str
    batch_id: str
    relation_type: str = "ant"

    def canonical_key(self) -> Tuple[str, str]:
        a, b = self.head, self.tail
        return (a, b) if a <= b else (b, a)


def pair_undirected_key(head: str, tail: str) -> Tuple[str, str]:
    return (head, tail) if head <= tail else (tail, head)


def sample_size_for(n: int) -> int:
    if n <= 0:
        return 0
    return min(n, max(50, math.ceil(n * 0.05)))


def ok_rate(ok_count: int, sample_n: int) -> float:
    if sample_n <= 0:
        return 0.0
    return ok_count / sample_n


def passes_quality_gate(
    ok_count: int,
    sample_n: int,
    *,
    threshold: float = OK_RATE_THRESHOLD,
) -> bool:
    if sample_n <= 0 or ok_count < 0 or ok_count > sample_n:
        return False
    return ok_rate(ok_count, sample_n) >= threshold


def parse_ok_rate_threshold(value: Any, *, field: str, path: Path, batch_id: str) -> float:
    """Fail-closed: batch must declare an allowed ok_rate_threshold."""
    try:
        threshold = float(value)
    except (TypeError, ValueError) as exc:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] {field} must be a float"
        ) from exc
    # Normalize -0 / 0.850000 quirks via round to 2 decimals for allowlist match.
    normalized = round(threshold, 2)
    if normalized not in ALLOWED_OK_RATE_THRESHOLDS:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] {field} must be one of "
            f"{sorted(ALLOWED_OK_RATE_THRESHOLDS)}, got {value!r}"
        )
    return normalized


def _chars_with_relation_type(
    db: Session,
    relation_type: str,
    *,
    exclude_sources: Optional[Set[str]] = None,
    only_sources: Optional[Set[str]] = None,
) -> Set[str]:
    exclude_sources = exclude_sources or set()
    only_sources = only_sources
    chars: Set[str] = set()
    w_head = aliased(Word)
    w_tail = aliased(Word)

    def _accept(source: Optional[str]) -> bool:
        src = source or ""
        if src in exclude_sources:
            return False
        if only_sources is not None and src not in only_sources:
            return False
        return True

    q_head = (
        db.query(w_head.char, WordRelation.source)
        .join(WordRelation, WordRelation.word_id == w_head.id)
        .filter(WordRelation.relation_type == relation_type)
    )
    for ch, source in q_head.all():
        if ch and _accept(source):
            chars.add(ch)
    q_tail = (
        db.query(w_tail.char, WordRelation.source)
        .join(WordRelation, WordRelation.related_id == w_tail.id)
        .filter(WordRelation.relation_type == relation_type)
    )
    for ch, source in q_tail.all():
        if ch and _accept(source):
            chars.add(ch)
    return chars


def chars_with_syn(db: Session) -> Set[str]:
    return _chars_with_relation_type(db, "syn")


def chars_with_direct_ant(
    db: Session,
    *,
    static_ant_heads: Optional[Iterable[str]] = None,
    exclude_sources: Optional[Iterable[str]] = None,
) -> Set[str]:
    """直連反義頭（排除 DERIVED_ANT_SOURCES ± extra）；可合併靜態詞林埠有反義嘅頭。"""
    excluded = set(DERIVED_ANT_SOURCES)
    if exclude_sources:
        excluded |= {s for s in exclude_sources if s}
    chars = _chars_with_relation_type(
        db,
        "ant",
        exclude_sources=excluded,
    )
    if static_ant_heads:
        chars |= {h for h in static_ant_heads if h}
    return chars


def export_seed_literals(
    db: Session,
    *,
    k: int = DEFAULT_SEED_K,
    essay_freq: Callable[[str], int] = get_essay_frequency,
    membership: Optional[Set[str]] = None,
    static_ant_heads: Optional[Iterable[str]] = None,
) -> List[str]:
    """有近無直連反 ∩ Essay Top-K；穩定序 frequency DESC, literal ASC。"""
    syns = chars_with_syn(db)
    directs = chars_with_direct_ant(db, static_ant_heads=static_ant_heads)
    candidates = syns - directs
    if membership is not None:
        candidates &= membership
    candidates = {c for c in candidates if is_valid_term(c)}
    ranked = sorted(candidates, key=lambda ch: (-int(essay_freq(ch)), ch))
    if k <= 0:
        return []
    return ranked[:k]


def syn_pairs_from_db(
    db: Session,
    *,
    exclude_sources: Optional[Iterable[str]] = None,
) -> Set[Tuple[str, str]]:
    """Undirected syn literal pairs from DB; optionally skip sources about to be replaced."""
    exclude = {s for s in (exclude_sources or ()) if s}
    pairs: Set[Tuple[str, str]] = set()
    w_head = aliased(Word)
    w_tail = aliased(Word)
    rows = (
        db.query(w_head.char, w_tail.char, WordRelation.source)
        .select_from(WordRelation)
        .join(w_head, WordRelation.word_id == w_head.id)
        .join(w_tail, WordRelation.related_id == w_tail.id)
        .filter(WordRelation.relation_type == "syn")
        .all()
    )
    for a, b, source in rows:
        if exclude and (source or "") in exclude:
            continue
        if a and b:
            pairs.add(pair_undirected_key(a, b))
    return pairs


def syn_pairs_from_tuples(
    rows: Iterable[RelationTuple],
    id_to_char: Dict[int, str],
) -> Set[Tuple[str, str]]:
    """Undirected syn literal pairs from in-memory RelationTuples (same-round collect)."""
    pairs: Set[Tuple[str, str]] = set()
    for word_id, related_id, rtype, _score, _source, _gc in rows:
        if rtype != "syn":
            continue
        a = id_to_char.get(int(word_id))
        b = id_to_char.get(int(related_id))
        if a and b:
            pairs.add(pair_undirected_key(a, b))
    return pairs


@dataclass
class FilterStats:
    accepted: List[Tuple[str, str]]
    rejected: List[Dict[str, str]]
    guotong_overlap: int = 0


def filter_proposals(
    proposals: Sequence[Tuple[str, str]],
    *,
    membership: Set[str],
    syn_pairs: Optional[Set[Tuple[str, str]]] = None,
    guotong_ant_pairs: Optional[Set[Tuple[str, str]]] = None,
    existing_accepted: Optional[Sequence[Tuple[str, str]]] = None,
    max_proposals_per_head: int = MAX_PROPOSALS_PER_HEAD,
    max_accepted_per_head: int = MAX_ACCEPTED_PER_HEAD,
) -> FilterStats:
    """硬過濾提案；每 head 提案上限後再受清單每頭 cap 約束。"""
    syn_pairs = syn_pairs or set()
    guotong_ant_pairs = guotong_ant_pairs or set()
    rejected: List[Dict[str, str]] = []
    accepted: List[Tuple[str, str]] = []
    seen_undirected: Set[Tuple[str, str]] = set()
    proposal_count: Dict[str, int] = {}
    accepted_count: Dict[str, int] = {}
    overlap = 0

    for head, tail in existing_accepted or ():
        h = normalize_literal(head) or ""
        t = normalize_literal(tail) or ""
        if not h or not t:
            continue
        key = pair_undirected_key(h, t)
        seen_undirected.add(key)
        accepted_count[h] = accepted_count.get(h, 0) + 1

    for raw_head, raw_tail in proposals:
        head = normalize_literal(raw_head)
        tail = normalize_literal(raw_tail)
        if not head or not tail:
            rejected.append({"head": raw_head, "tail": raw_tail, "reason": "invalid_literal"})
            continue
        if head == tail:
            rejected.append({"head": head, "tail": tail, "reason": "self"})
            continue
        if head not in membership or tail not in membership:
            rejected.append({"head": head, "tail": tail, "reason": "not_in_lexicon"})
            continue
        key = pair_undirected_key(head, tail)
        if key in seen_undirected:
            rejected.append({"head": head, "tail": tail, "reason": "duplicate_or_reverse"})
            continue
        if key in syn_pairs:
            rejected.append({"head": head, "tail": tail, "reason": "syn_conflict"})
            continue
        if proposal_count.get(head, 0) >= max_proposals_per_head:
            rejected.append({"head": head, "tail": tail, "reason": "proposal_cap"})
            continue
        if accepted_count.get(head, 0) >= max_accepted_per_head:
            rejected.append({"head": head, "tail": tail, "reason": "accepted_cap"})
            continue
        proposal_count[head] = proposal_count.get(head, 0) + 1
        if key in guotong_ant_pairs:
            overlap += 1
        seen_undirected.add(key)
        accepted_count[head] = accepted_count.get(head, 0) + 1
        accepted.append((head, tail))

    return FilterStats(accepted=accepted, rejected=rejected, guotong_overlap=overlap)


def sample_pairs(
    pairs: Sequence[Tuple[str, str]],
    *,
    seed: int,
) -> List[Tuple[str, str]]:
    ordered = sorted(pairs, key=lambda p: (p[0], p[1]))
    n = len(ordered)
    size = sample_size_for(n)
    if size == 0:
        return []
    if size >= n:
        return list(ordered)
    rng = random.Random(seed)
    idxs = sorted(rng.sample(range(n), size))
    return [ordered[i] for i in idxs]


def static_ant_heads_from_port(port: Any = None) -> Set[str]:
    """Heads with **靜態詞林埠** antonyms (CONTEXT § 直連反義)."""
    if port is None:
        from app.domain.thesaurus.port import StaticThesaurusPort

        port = StaticThesaurusPort(auto_load=True)
    port.ensure_loaded()
    heads: Set[str] = set()
    for head, _tail in port.iter_antonym_edges():
        h = normalize_literal(head)
        if h:
            heads.add(h)
    return heads


def _is_auditable_model_id(model: str) -> bool:
    """provider/model vendor id — reject workflow labels like 'Cursor Agent/blind-draft'."""
    if " " in model or model.count("/") != 1:
        return False
    provider, name = model.split("/", 1)
    if not _MODEL_PROVIDER_RE.fullmatch(provider) or not _MODEL_NAME_RE.fullmatch(name):
        return False
    blob = model.lower()
    return not any(tok in blob for tok in _WORKFLOW_MODEL_TOKENS)


def _require_sha1(value: Any, *, field: str, path: Path, batch_id: str) -> str:
    text = str(value or "").strip().lower()
    if not _GIT_SHA1_RE.fullmatch(text):
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] {field} must be 40-hex git sha1"
        )
    return text


def _require_sha256(value: Any, *, field: str, path: Path, batch_id: str) -> str:
    text = str(value or "").strip().lower()
    if not _SHA256_RE.fullmatch(text):
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] {field} must be 64-hex sha256"
        )
    return text


def validate_batch_meta_entry(batch_id: str, entry: Any, *, path: Path) -> None:
    """Fail-closed: referenced batch must carry auditable fields + declared OK-rate gate."""
    if not isinstance(entry, dict) or not entry:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] must be a non-empty object"
        )
    required = (
        "k",
        "sample_seed",
        "sample_n",
        "sample_ok",
        "ok_rate_threshold",
        "sample_parent_n",
        "sample_parent_commit",
        "sample_parent_tsv_sha256",
        "removed_sample_fails",
        "model_note",
        "model",
        "model_provider",
        "model_version",
        "model_params",
        "git_commit",
        "db_sha256",
        "essay_sha256",
        "prompt_path",
        "prompt_sha256",
    )
    missing = [k for k in required if k not in entry]
    if missing:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] missing fields: {', '.join(missing)}"
        )
    try:
        k = int(entry["k"])
        sample_seed = int(entry["sample_seed"])
        sample_n = int(entry["sample_n"])
        sample_ok = int(entry["sample_ok"])
        sample_parent_n = int(entry["sample_parent_n"])
    except (TypeError, ValueError) as exc:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] numeric fields invalid: {exc}"
        ) from exc
    if k < 0 or sample_n <= 0 or sample_ok < 0 or sample_ok > sample_n:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] impossible sample counts "
            f"(ok={sample_ok}, n={sample_n}, k={k})"
        )
    if sample_parent_n < sample_n:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] sample_parent_n={sample_parent_n} "
            f"< sample_n={sample_n}"
        )
    for key in ("model_note", "model", "model_provider", "model_version", "prompt_path"):
        if not str(entry.get(key) or "").strip():
            raise ProjectAntonymsError(f"{path}: batches[{batch_id!r}] {key} empty")
    model = str(entry["model"]).strip()
    if not _is_auditable_model_id(model):
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] model must be auditable "
            f"provider/model id, got {model!r}"
        )
    _require_sha1(entry["git_commit"], field="git_commit", path=path, batch_id=batch_id)
    _require_sha1(
        entry["sample_parent_commit"],
        field="sample_parent_commit",
        path=path,
        batch_id=batch_id,
    )
    for field in ("db_sha256", "essay_sha256", "prompt_sha256", "sample_parent_tsv_sha256"):
        _require_sha256(entry[field], field=field, path=path, batch_id=batch_id)
    params = entry.get("model_params")
    if not isinstance(params, dict) or not params:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] model_params must be a non-empty object"
        )
    missing_controls = [k for k in _GEN_CONTROL_KEYS if k not in params]
    if missing_controls:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] model_params missing generation "
            f"controls: {', '.join(missing_controls)} (null values allowed)"
        )
    removed = entry.get("removed_sample_fails")
    if not isinstance(removed, list):
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] removed_sample_fails must be a list"
        )
    for i, row in enumerate(removed):
        if not isinstance(row, dict) or "head" not in row or "tail" not in row:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].removed_sample_fails[{i}] "
                f"needs head/tail"
            )
        if not str(row["head"]).strip() or not str(row["tail"]).strip():
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}].removed_sample_fails[{i}] empty literal"
            )
    verdicts = entry.get("sample_verdicts")
    if verdicts is None:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] missing sample_verdicts"
        )
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
        for key in ("head", "tail", "verdict"):
            if key not in row:
                raise ProjectAntonymsError(
                    f"{path}: batches[{batch_id!r}].sample_verdicts[{i}] missing {key}"
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
    threshold = parse_ok_rate_threshold(
        entry["ok_rate_threshold"],
        field="ok_rate_threshold",
        path=path,
        batch_id=batch_id,
    )
    expected_threshold = (
        OK_RATE_THRESHOLD
        if batch_id == LEGACY_BATCH_ID
        else OK_RATE_THRESHOLD_CAMPAIGN
    )
    if threshold != expected_threshold:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] ok_rate_threshold must be "
            f"{expected_threshold:.2f}, got {threshold:.2f}"
        )
    if not passes_quality_gate(sample_ok, sample_n, threshold=threshold):
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] quality gate failed: "
            f"{sample_ok}/{sample_n} < {threshold:.0%}"
        )


def _read_git_blob(commit: str, rel_path: str) -> Optional[bytes]:
    """Return `git show commit:path` bytes when the object is available."""
    if not (ROOT / ".git").exists():
        return None
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "show", f"{commit}:{rel_path}"],
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None


def _tsv_pair_rows(raw: bytes) -> List[Tuple[str, str]]:
    text = raw.decode("utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]
    rows: List[Tuple[str, str]] = []
    for i, line in enumerate(text.splitlines()):
        if not line.strip():
            continue
        if i == 0 and line == "head\ttail\trelation_type\tbatch_id":
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        rows.append((parts[0].strip(), parts[1].strip()))
    return rows


def assert_sample_replayable(
    batch_id: str,
    entry: dict[str, Any],
    accepted: Sequence[ProjectAntPair],
    *,
    path: Path,
) -> None:
    """Replay sample + enforce fail removal + bind parent hash when git blob exists."""
    removed = entry["removed_sample_fails"]
    removed_keys = {
        pair_undirected_key(str(r["head"]).strip(), str(r["tail"]).strip()) for r in removed
    }
    accepted_keys = {pair_undirected_key(p.head, p.tail) for p in accepted}
    fail_keys: Set[Tuple[str, str]] = set()
    for i, row in enumerate(entry["sample_verdicts"]):
        if str(row["verdict"]).strip().lower() != "fail":
            continue
        key = pair_undirected_key(str(row["head"]).strip(), str(row["tail"]).strip())
        fail_keys.add(key)
        if key not in removed_keys:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}] sample_verdicts[{i}] fail "
                f"{key} missing from removed_sample_fails"
            )
        if key in accepted_keys:
            raise ProjectAntonymsError(
                f"{path}: batches[{batch_id!r}] fail pair {key} still in accepted TSV"
            )
    if removed_keys - fail_keys:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] removed_sample_fails has pairs "
            f"not marked fail in sample_verdicts: {sorted(removed_keys - fail_keys)}"
        )

    parent: List[Tuple[str, str]] = [(p.head, p.tail) for p in accepted]
    parent.extend((str(r["head"]).strip(), str(r["tail"]).strip()) for r in removed)
    parent_n = int(entry["sample_parent_n"])
    if len(parent) != parent_n:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] reconstructed parent size "
            f"{len(parent)} != sample_parent_n={parent_n}"
        )
    parent_keys = {pair_undirected_key(h, t) for h, t in parent}
    if len(parent_keys) != parent_n:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] reconstructed parent has duplicates"
        )

    expected_hash = str(entry["sample_parent_tsv_sha256"]).strip().lower()
    commit = str(entry["sample_parent_commit"]).strip().lower()
    blob = _read_git_blob(commit, "data/syn_ant/project_antonyms.tsv")
    if blob is None:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] cannot read git blob "
            f"{commit}:data/syn_ant/project_antonyms.tsv to verify "
            f"sample_parent_tsv_sha256"
        )
    got_hash = hashlib.sha256(blob).hexdigest()
    if got_hash != expected_hash:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] sample_parent_tsv_sha256 mismatch: "
            f"meta={expected_hash} git={got_hash}"
        )
    git_keys = {pair_undirected_key(h, t) for h, t in _tsv_pair_rows(blob)}
    if git_keys != parent_keys:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] reconstructed parent set != "
            f"git TSV at sample_parent_commit"
        )

    sampled = sample_pairs(parent, seed=int(entry["sample_seed"]))
    expected = [
        (str(v["head"]).strip(), str(v["tail"]).strip()) for v in entry["sample_verdicts"]
    ]
    if sampled != expected:
        raise ProjectAntonymsError(
            f"{path}: batches[{batch_id!r}] sample replay mismatch "
            f"(seed={entry['sample_seed']}, parent_n={parent_n})"
        )


def load_meta(path: Path | str = DEFAULT_META) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise ProjectAntonymsError(f"missing project antonyms meta: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProjectAntonymsError(f"invalid meta JSON: {p}: {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectAntonymsError(f"meta root must be object: {p}")
    batches = data.get("batches")
    if batches is None:
        data["batches"] = {}
    elif not isinstance(batches, dict):
        raise ProjectAntonymsError(f"meta.batches must be object: {p}")
    return data


def save_meta(data: dict[str, Any], path: Path | str = DEFAULT_META) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_project_antonyms_tsv(
    path: Path | str = DEFAULT_TSV,
    *,
    meta: Optional[dict[str, Any]] = None,
    membership: Optional[Set[str]] = None,
    syn_pairs: Optional[Set[Tuple[str, str]]] = None,
    require_file: bool = True,
) -> List[ProjectAntPair]:
    """Fail-closed parse + validate authoritative list."""
    p = Path(path)
    if not p.is_file():
        if require_file:
            raise ProjectAntonymsError(f"missing project antonyms TSV: {p}")
        return []
    text = p.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        raise ProjectAntonymsError(f"TSV must be UTF-8 without BOM: {p}")
    lines = text.splitlines()
    if not lines:
        raise ProjectAntonymsError(f"empty TSV (need header): {p}")
    reader = csv.reader(lines, delimiter="\t")
    try:
        header = tuple(next(reader))
    except StopIteration as exc:
        raise ProjectAntonymsError(f"empty TSV (need header): {p}") from exc
    if header != TSV_HEADER:
        raise ProjectAntonymsError(
            f"bad TSV header {header!r}; expected {TSV_HEADER!r}: {p}"
        )

    meta = meta if meta is not None else load_meta(DEFAULT_META if p == DEFAULT_TSV else p.with_suffix(".meta.json"))
    batches = meta.get("batches") or {}
    syn_pairs = syn_pairs or set()
    out: List[ProjectAntPair] = []
    seen: Set[Tuple[str, str]] = set()
    per_head: Dict[str, int] = {}
    validated_batches: Set[str] = set()

    for lineno, row in enumerate(reader, start=2):
        if not row or all(not c.strip() for c in row):
            continue
        if len(row) != 4:
            raise ProjectAntonymsError(f"{p}:{lineno}: expected 4 columns, got {len(row)}")
        head_raw, tail_raw, rtype, batch_id = (c.strip() for c in row)
        if rtype != "ant":
            raise ProjectAntonymsError(f"{p}:{lineno}: relation_type must be 'ant', got {rtype!r}")
        if not batch_id or batch_id not in batches:
            raise ProjectAntonymsError(f"{p}:{lineno}: unknown or empty batch_id {batch_id!r}")
        if batch_id not in validated_batches:
            validate_batch_meta_entry(batch_id, batches[batch_id], path=p)
            validated_batches.add(batch_id)
        head = normalize_literal(head_raw)
        tail = normalize_literal(tail_raw)
        if not head or not tail:
            raise ProjectAntonymsError(f"{p}:{lineno}: invalid literal")
        if head == tail:
            raise ProjectAntonymsError(f"{p}:{lineno}: self pair")
        if membership is not None and (head not in membership or tail not in membership):
            raise ProjectAntonymsError(f"{p}:{lineno}: not in lexicon: {head}/{tail}")
        key = pair_undirected_key(head, tail)
        if key in seen:
            raise ProjectAntonymsError(f"{p}:{lineno}: duplicate/reverse of {key}")
        if key in syn_pairs:
            raise ProjectAntonymsError(f"{p}:{lineno}: syn conflict {key}")
        if per_head.get(head, 0) >= MAX_ACCEPTED_PER_HEAD:
            raise ProjectAntonymsError(f"{p}:{lineno}: accepted cap for head {head}")
        seen.add(key)
        per_head[head] = per_head.get(head, 0) + 1
        out.append(ProjectAntPair(head=head, tail=tail, batch_id=batch_id))
    for batch_id in validated_batches:
        assert_sample_replayable(batch_id, batches[batch_id], [p for p in out if p.batch_id == batch_id], path=p)
    return out


def collect_project_ant_tuples(
    db: Session,
    *,
    tsv_path: Path | str = DEFAULT_TSV,
    meta_path: Path | str = DEFAULT_META,
    syn_pairs: Optional[Set[Tuple[str, str]]] = None,
) -> List[RelationTuple]:
    """Load authoritative list into canonical RelationTuples (fail-closed).

    Pass ``syn_pairs`` from the same-round static collect when building, so fresh
    Cilin/guotong synonyms are visible before DB replacement.
    """
    membership = {c for (c,) in db.query(Word.char).distinct().all() if c}
    if syn_pairs is None:
        syn_pairs = syn_pairs_from_db(db)
    meta = load_meta(meta_path)
    pairs = parse_project_antonyms_tsv(
        tsv_path,
        meta=meta,
        membership=membership,
        syn_pairs=syn_pairs,
        require_file=True,
    )
    char_to_id = get_char_to_primary_id(db)
    out: List[RelationTuple] = []
    for pair in pairs:
        id_a = char_to_id.get(pair.head)
        id_b = char_to_id.get(pair.tail)
        if id_a is None or id_b is None:
            raise ProjectAntonymsError(
                f"literal missing primary id: {pair.head!r}/{pair.tail!r}"
            )
        row = normalize_relation_tuple(
            id_a,
            id_b,
            "ant",
            PROJECT_ANT_SCORE,
            PROJECT_ANT_SOURCE,
            None,
        )
        if row is not None:
            out.append(row)
    return out


def file_sha256(path: Path | str) -> Optional[str]:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_seed_export(path: Path | str, seeds: Sequence[str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(seeds) + ("\n" if seeds else ""), encoding="utf-8")


def write_proposals_tsv(path: Path | str, pairs: Sequence[Tuple[str, str]], *, batch_id: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = ["\t".join(TSV_HEADER)]
    for head, tail in pairs:
        lines.append(f"{head}\t{tail}\tant\t{batch_id}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


__all__ = [
    "DEFAULT_META",
    "DEFAULT_PROMPT",
    "DEFAULT_SEED_K",
    "DEFAULT_TSV",
    "FilterStats",
    "MAX_ACCEPTED_PER_HEAD",
    "MAX_PROPOSALS_PER_HEAD",
    "OK_RATE_THRESHOLD",
    "OK_RATE_THRESHOLD_CAMPAIGN",
    "ALLOWED_OK_RATE_THRESHOLDS",
    "LEGACY_BATCH_ID",
    "PROJECT_ANT_MERGE_RANK",
    "PROJECT_ANT_RUNTIME_RANK",
    "PROJECT_ANT_SCORE",
    "PROJECT_ANT_SOURCE",
    "ProjectAntPair",
    "ProjectAntonymsError",
    "TSV_HEADER",
    "assert_sample_replayable",
    "chars_with_direct_ant",
    "chars_with_syn",
    "collect_project_ant_tuples",
    "export_seed_literals",
    "file_sha256",
    "filter_proposals",
    "load_meta",
    "ok_rate",
    "pair_undirected_key",
    "parse_ok_rate_threshold",
    "parse_project_antonyms_tsv",
    "passes_quality_gate",
    "sample_pairs",
    "sample_size_for",
    "save_meta",
    "static_ant_heads_from_port",
    "syn_pairs_from_db",
    "syn_pairs_from_tuples",
    "validate_batch_meta_entry",
    "write_proposals_tsv",
    "write_seed_export",
]
