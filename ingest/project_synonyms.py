"""專案自建近義：清單 loader／直連 syn 鄰接／ingest tuples（CONTEXT § 專案自建近義*）。"""
from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.domain.relations.bulk_insert import RelationTuple, normalize_relation_tuple
from app.domain.relations.char_index import get_char_to_primary_id
from app.domain.relations.valid_term import is_valid_term, normalize_literal
from app.models.word import Word
from app.thesaurus.static_index import (
    get_cilin_synonyms,
    get_guotong_synonyms,
    load_cilin_index,
    load_thesaurus_dicts,
)
from ingest.project_antonyms import pair_undirected_key

ROOT = Path(__file__).resolve().parents[1]
PROJECT_DIR = ROOT / "data" / "syn_ant" / "project"
DEFAULT_TSV = PROJECT_DIR / "project_synonyms.tsv"
DEFAULT_META = PROJECT_DIR / "project_synonyms.meta.json"
DEFAULT_PROMPT = PROJECT_DIR / "project-synonyms-prompt.txt"
DEFAULT_NO_NATURAL_TSV = PROJECT_DIR / "project_no_natural_synonyms.tsv"
DEFAULT_ADEQUATE_TSV = PROJECT_DIR / "project_adequate_existing.tsv"
DEFAULT_DB = ROOT / "client" / "public" / "lyrics.db"

NO_NATURAL_REASONS = frozenset(
    {
        "function_word",
        "proper_name_or_deixis",
        "polysemous_no_stable_sense",
        "other_documented",
        "cultural_no_binary",
        "no_stable_near_synonym",
    }
)

PROJECT_SYN_SOURCE = "project_syn"
PROJECT_SYN_SCORE = 0.85
TSV_HEADER = ("head", "tail", "relation_type", "batch_id")
MAX_PROPOSALS_PER_HEAD = 3
MAX_ACCEPTED_PER_HEAD = 5
SPARSE_LT = 2


class ProjectSynonymsError(ValueError):
    """Fail-closed validation / load error."""


@dataclass(frozen=True, slots=True)
class ProjectSynPair:
    head: str
    tail: str
    batch_id: str
    relation_type: str = "syn"

    def canonical_key(self) -> Tuple[str, str]:
        return pair_undirected_key(self.head, self.tail)


def file_sha256(path: Path | str) -> Optional[str]:
    p = Path(path)
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_meta(path: Path | str = DEFAULT_META) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        return {"batches": {}}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ProjectSynonymsError(f"meta must be object: {p}")
    data.setdefault("batches", {})
    return data


def save_meta(data: dict[str, Any], path: Path | str = DEFAULT_META) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_empty_list(
    tsv_path: Path | str = DEFAULT_TSV,
    meta_path: Path | str = DEFAULT_META,
) -> None:
    """Create header-only TSV + empty batches meta if missing."""
    tsv = Path(tsv_path)
    meta = Path(meta_path)
    tsv.parent.mkdir(parents=True, exist_ok=True)
    if not tsv.is_file():
        tsv.write_text("\t".join(TSV_HEADER) + "\n", encoding="utf-8")
    if not meta.is_file():
        save_meta({"batches": {}, "note": "專案自建近義清單；batches 於首批入帳時寫入"}, meta)


def parse_project_synonyms_tsv(
    path: Path | str = DEFAULT_TSV,
    *,
    meta: Optional[dict[str, Any]] = None,
    membership: Optional[Set[str]] = None,
    ant_pairs: Optional[Set[Tuple[str, str]]] = None,
    require_file: bool = True,
) -> List[ProjectSynPair]:
    """Fail-closed parse. Soft-overlap upstream syn OK；與直連 ant 硬拒。"""
    p = Path(path)
    if not p.is_file():
        if require_file:
            raise ProjectSynonymsError(f"missing project synonyms TSV: {p}")
        return []
    text = p.read_text(encoding="utf-8")
    if text.startswith("\ufeff"):
        raise ProjectSynonymsError(f"TSV must be UTF-8 without BOM: {p}")
    lines = text.splitlines()
    if not lines:
        raise ProjectSynonymsError(f"empty TSV (need header): {p}")
    reader = csv.reader(lines, delimiter="\t")
    try:
        header = tuple(next(reader))
    except StopIteration as exc:
        raise ProjectSynonymsError(f"empty TSV (need header): {p}") from exc
    if header != TSV_HEADER:
        raise ProjectSynonymsError(
            f"bad TSV header {header!r}; expected {TSV_HEADER!r}: {p}"
        )

    meta = meta if meta is not None else load_meta(
        DEFAULT_META if p == DEFAULT_TSV else p.with_suffix(".meta.json")
    )
    batches = meta.get("batches") or {}
    ant_pairs = ant_pairs or set()
    out: List[ProjectSynPair] = []
    seen: Set[Tuple[str, str]] = set()
    per_head: Dict[str, int] = {}

    for lineno, row in enumerate(reader, start=2):
        if not row or all(not c.strip() for c in row):
            continue
        if len(row) != 4:
            raise ProjectSynonymsError(f"{p}:{lineno}: expected 4 columns, got {len(row)}")
        head_raw, tail_raw, rtype, batch_id = (c.strip() for c in row)
        if rtype != "syn":
            raise ProjectSynonymsError(
                f"{p}:{lineno}: relation_type must be 'syn', got {rtype!r}"
            )
        if not batch_id or batch_id not in batches:
            raise ProjectSynonymsError(f"{p}:{lineno}: unknown or empty batch_id {batch_id!r}")
        head = normalize_literal(head_raw)
        tail = normalize_literal(tail_raw)
        if not head or not tail:
            raise ProjectSynonymsError(f"{p}:{lineno}: invalid literal")
        if head == tail:
            raise ProjectSynonymsError(f"{p}:{lineno}: self pair")
        if membership is not None and (head not in membership or tail not in membership):
            raise ProjectSynonymsError(f"{p}:{lineno}: not in lexicon: {head}/{tail}")
        key = pair_undirected_key(head, tail)
        if key in seen:
            raise ProjectSynonymsError(f"{p}:{lineno}: duplicate/reverse of {key}")
        if key in ant_pairs:
            raise ProjectSynonymsError(f"{p}:{lineno}: ant conflict {key}")
        if per_head.get(head, 0) >= MAX_ACCEPTED_PER_HEAD:
            raise ProjectSynonymsError(f"{p}:{lineno}: accepted cap for head {head}")
        seen.add(key)
        per_head[head] = per_head.get(head, 0) + 1
        out.append(ProjectSynPair(head=head, tail=tail, batch_id=batch_id))
    return out


def ant_pairs_from_db(db: Session) -> Set[Tuple[str, str]]:
    from sqlalchemy.orm import aliased

    from app.models.word import WordRelation

    w_head = aliased(Word)
    w_tail = aliased(Word)
    rows = (
        db.query(w_head.char, w_tail.char)
        .select_from(WordRelation)
        .join(w_head, WordRelation.word_id == w_head.id)
        .join(w_tail, WordRelation.related_id == w_tail.id)
        .filter(WordRelation.relation_type == "ant")
        .all()
    )
    out: Set[Tuple[str, str]] = set()
    for a, b in rows:
        na = normalize_literal(a) if a else None
        nb = normalize_literal(b) if b else None
        if na and nb and na != nb:
            out.add(pair_undirected_key(na, nb))
    return out


def collect_project_syn_tuples(
    db: Session,
    *,
    tsv_path: Path | str = DEFAULT_TSV,
    meta_path: Path | str = DEFAULT_META,
    ant_pairs: Optional[Set[Tuple[str, str]]] = None,
) -> List[RelationTuple]:
    """Load authoritative syn list; missing file → empty (create via ensure_empty_list)."""
    p = Path(tsv_path)
    if not p.is_file():
        return []
    membership = {c for (c,) in db.query(Word.char).distinct().all() if c}
    if ant_pairs is None:
        ant_pairs = ant_pairs_from_db(db)
    meta = load_meta(meta_path)
    pairs = parse_project_synonyms_tsv(
        tsv_path,
        meta=meta,
        membership=membership,
        ant_pairs=ant_pairs,
        require_file=True,
    )
    char_to_id = get_char_to_primary_id(db)
    out: List[RelationTuple] = []
    for pair in pairs:
        id_a = char_to_id.get(pair.head)
        id_b = char_to_id.get(pair.tail)
        if id_a is None or id_b is None:
            raise ProjectSynonymsError(
                f"literal missing primary id: {pair.head!r}/{pair.tail!r}"
            )
        row = normalize_relation_tuple(
            id_a,
            id_b,
            "syn",
            PROJECT_SYN_SCORE,
            PROJECT_SYN_SOURCE,
            None,
        )
        if row is not None:
            out.append(row)
    return out


def load_lexicon_literals(db_path: Path | str = DEFAULT_DB) -> Set[str]:
    con = sqlite3.connect(str(db_path))
    rows = con.execute("SELECT DISTINCT char FROM words").fetchall()
    con.close()
    out: Set[str] = set()
    for (raw,) in rows:
        lit = normalize_literal(raw) if raw else None
        if lit:
            out.add(lit)
    return out


def build_direct_syn_adj(
    *,
    db_path: Path | str = DEFAULT_DB,
    lex: Optional[Set[str]] = None,
) -> Dict[str, Set[str]]:
    """直連近義鄰接：DB syn ∪ cilin ∪ guotong（兩端 ∈ lex）。"""
    db_path = Path(db_path)
    if lex is None:
        lex = load_lexicon_literals(db_path)
    adj: Dict[str, Set[str]] = defaultdict(set)
    con = sqlite3.connect(str(db_path))
    rows = con.execute(
        """
        SELECT a.char, b.char
        FROM word_relations r
        JOIN words a ON a.id = r.word_id
        JOIN words b ON b.id = r.related_id
        WHERE r.relation_type = 'syn'
        """
    ).fetchall()
    con.close()
    for raw_a, raw_b in rows:
        a = normalize_literal(raw_a) if raw_a else None
        b = normalize_literal(raw_b) if raw_b else None
        if not a or not b or a == b or a not in lex or b not in lex:
            continue
        adj[a].add(b)
        adj[b].add(a)

    load_cilin_index(str(ROOT / "data" / "cilin" / "new_cilin.txt"))
    load_thesaurus_dicts(
        syn_path=str(ROOT / "data" / "thesaurus" / "dict_synonym.txt"),
        ant_path=str(ROOT / "data" / "thesaurus" / "dict_antonym.txt"),
    )
    for head in lex:
        for getter in (get_cilin_synonyms, get_guotong_synonyms):
            for raw in getter(head) or []:
                tail = normalize_literal(raw)
                if not tail or tail == head or tail not in lex:
                    continue
                adj[head].add(tail)
                adj[tail].add(head)
    return adj


def direct_syn_tail_count(adj: Dict[str, Set[str]], head: str) -> int:
    return len(adj.get(head, ()))


def project_syn_heads_from_tsv(path: Path | str = DEFAULT_TSV) -> Set[str]:
    """Heads already covered by project_syn list (exclude from freeze slide)."""
    p = Path(path)
    if not p.is_file():
        return set()
    covered: Set[str] = set()
    for pair in parse_project_synonyms_tsv(p, require_file=True):
        covered.add(pair.head)
        covered.add(pair.tail)
    return covered


def load_ledger_heads(path: Path | str) -> Set[str]:
    """Load head column from head\\treason|note\\tbatch_id ledgers."""
    p = Path(path)
    if not p.is_file():
        return set()
    out: Set[str] = set()
    for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines()):
        if i == 0 or not ln.strip():
            continue
        parts = ln.split("\t")
        if not parts:
            continue
        lit = normalize_literal(parts[0])
        if lit:
            out.add(lit)
    return out


def write_no_natural_synonyms(
    rows: List[Tuple[str, str, str]],
    path: Path | str = DEFAULT_NO_NATURAL_TSV,
    *,
    merge: bool = True,
) -> None:
    """rows: (head, reason, batch_id). merge=True 保留他批列（同 head 以新列蓋）。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    by: Dict[str, Tuple[str, str, str]] = {}
    if merge and p.is_file():
        for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines()):
            if i == 0 or not ln.strip():
                continue
            parts = ln.split("\t")
            if len(parts) >= 3:
                h = normalize_literal(parts[0])
                if h:
                    by[h] = (h, parts[1], parts[2])
    for head, reason, batch_id in rows:
        if reason not in NO_NATURAL_REASONS:
            raise ProjectSynonymsError(f"bad no_natural reason: {reason!r}")
        h = normalize_literal(head)
        if not h:
            raise ProjectSynonymsError(f"invalid no_natural head: {head!r}")
        by[h] = (h, reason, batch_id)
    lines = ["head\treason\tbatch_id"]
    for h, reason, batch_id in by.values():
        lines.append(f"{h}\t{reason}\t{batch_id}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_adequate_existing(
    rows: List[Tuple[str, str, str]],
    path: Path | str = DEFAULT_ADEQUATE_TSV,
    *,
    merge: bool = True,
) -> None:
    """rows: (head, note, batch_id). merge=True 保留他批列。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    by: Dict[str, Tuple[str, str, str]] = {}
    if merge and p.is_file():
        for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines()):
            if i == 0 or not ln.strip():
                continue
            parts = ln.split("\t")
            if len(parts) >= 3:
                h = normalize_literal(parts[0])
                if h:
                    by[h] = (h, parts[1], parts[2])
            elif len(parts) == 2:
                h = normalize_literal(parts[0])
                if h:
                    by[h] = (h, parts[1], "")
    for head, note, batch_id in rows:
        h = normalize_literal(head)
        if not h:
            raise ProjectSynonymsError(f"invalid adequate head: {head!r}")
        note = (note or "").strip() or "adequate_existing"
        by[h] = (h, note, batch_id)
    lines = ["head\tnote\tbatch_id"]
    for h, note, batch_id in by.values():
        lines.append(f"{h}\t{note}\t{batch_id}")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_synonym_pairs(
    pairs: List[Tuple[str, str]],
    *,
    batch_id: str,
    tsv_path: Path | str = DEFAULT_TSV,
    meta_path: Path | str = DEFAULT_META,
) -> None:
    p = Path(tsv_path)
    ensure_empty_list(p, meta_path)
    text = p.read_text(encoding="utf-8")
    if batch_id in text:
        raise ProjectSynonymsError(f"batch {batch_id} already in {p}")
    if not text.endswith("\n"):
        text += "\n"
    for head, tail in pairs:
        h = normalize_literal(head)
        t = normalize_literal(tail)
        if not h or not t:
            raise ProjectSynonymsError(f"invalid pair {head!r}/{tail!r}")
        text += f"{h}\t{t}\tsyn\t{batch_id}\n"
    p.write_text(text, encoding="utf-8")


__all__ = [
    "DEFAULT_ADEQUATE_TSV",
    "DEFAULT_NO_NATURAL_TSV",
    "DEFAULT_DB",
    "DEFAULT_META",
    "DEFAULT_PROMPT",
    "DEFAULT_TSV",
    "MAX_ACCEPTED_PER_HEAD",
    "MAX_PROPOSALS_PER_HEAD",
    "NO_NATURAL_REASONS",
    "PROJECT_DIR",
    "PROJECT_SYN_SCORE",
    "PROJECT_SYN_SOURCE",
    "ProjectSynPair",
    "ProjectSynonymsError",
    "SPARSE_LT",
    "TSV_HEADER",
    "ant_pairs_from_db",
    "append_synonym_pairs",
    "build_direct_syn_adj",
    "collect_project_syn_tuples",
    "direct_syn_tail_count",
    "ensure_empty_list",
    "file_sha256",
    "load_ledger_heads",
    "load_lexicon_literals",
    "load_meta",
    "parse_project_synonyms_tsv",
    "project_syn_heads_from_tsv",
    "save_meta",
    "write_adequate_existing",
    "write_no_natural_synonyms",
]
