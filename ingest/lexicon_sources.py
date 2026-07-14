"""Lexicon ingest from SSOT raw files."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.lexicon.candidates import LexiconCandidate
from app.utils.jyutping_codec import get_0243_code
from app.utils.trad_chinese import to_traditional
from ingest.lexicon_candidate_normalizer import LexiconCandidateNormalizer
from ingest.lexicon_validate import normalize_lexicon_candidate
from ingest.lexicon_raw_paths import ROOT, resolve_lexicon_raw_path
from ingest.syn_ant_manifest import resolve_source_path

_SOURCE_RIME = "rime"
_CJK = re.compile(r"[\u4e00-\u9fff]")
_NORMALIZER = LexiconCandidateNormalizer()
_CJK_WORD = re.compile(r"[\u3400-\u9fff]+")
_CJK_ONLY = re.compile(r"^[\u3400-\u9fff]+$")
_JYUTPING_TOKEN = re.compile(r"^[a-z]+\d$", re.IGNORECASE)
_HSK_NOISE = re.compile(r"(?:\d+|[一二三四五六七八九十]+)[级級][词詞][汇彙]表$")
_PHRASE_ORG_PLACE_SUFFIXES = frozenset(
    {
        "中學",
        "小學",
        "幼稚園",
        "幼兒園",
        "學校",
        "大學",
        "醫院",
        "診所",
        "總站",
        "車站",
        "分行",
        "銀行",
        "大廈",
        "商店",
        "百貨",
        "超市",
        "藥店",
        "藥房",
        "酒家",
        "實業",
        "市場",
        "商行",
        "便利店",
        "餐館",
        "酒樓",
        "酒店",
        "商場",
        "廣場",
        "體育館",
        "羽毛球館",
        "中心",
        "公司",
        "委員會",
        "聯合會",
        "基金會",
        "管理局",
        "辦公室",
        "共和國",
        "自治縣",
        "自治州",
        "行政區",
    }
)
_RIME_UPSTREAM_WORD_FILES = (
    "word.csv",
    "fixed_expressions.csv",
    "phrase_fragment.csv",
    "onomatopoeia.csv",
    "trending.csv",
)
_RIME_PHRASE_STAT_KEYS = (
    "body_rows",
    "accepted",
    "accepted_8_char_allowlisted",
    "duplicate_literal",
    "missing_jyutping",
    "invalid_reading",
    "rejected_short",
    "rejected_long",
    "rejected_mixed",
    "rejected_place_or_org",
    "rejected_literal",
    "rejected_8_char_needs_review",
)


def ingest_rime_char_csv(path: Path | str) -> list[LexiconCandidate]:
    csv_path = Path(path)
    out: list[LexiconCandidate] = []
    seen: set[tuple[str, str]] = set()
    if not csv_path.is_file():
        return out
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            char = str(row.get("char") or "").strip()
            jyutping = str(row.get("jyutping") or "").strip()
            if not char or not jyutping or not _CJK.search(char) or len(char) != 1:
                continue
            code = get_0243_code(jyutping) or ""
            if not code:
                continue
            key = (char, jyutping)
            if key in seen:
                continue
            seen.add(key)
            out.append(
                LexiconCandidate(char=char, jyutping=jyutping, code=code, sources=(_SOURCE_RIME,))
            )
    return out


def ingest_lexicon_json(path: Path | str, *, source_id: str) -> list[LexiconCandidate]:
    json_path = Path(path)
    if not json_path.is_file():
        return []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    out: list[LexiconCandidate] = []
    seen: set[tuple[str, str]] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        char = str(item.get("char") or "").strip()
        jyutping = str(item.get("jyutping") or "").strip()
        code = str(item.get("code") or "").strip() or None
        if not char or not jyutping or not _CJK.search(char):
            continue
        candidate = _NORMALIZER.normalize_candidate(char, jyutping, source_id=source_id, code=code)
        if not candidate:
            continue
        key = (candidate.char, candidate.jyutping)
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)
    return out


def _append_candidate(
    out: list[LexiconCandidate],
    seen: set[tuple[str, str]],
    *,
    char: str,
    jyutping: str,
    source_id: str,
) -> None:
    if not char or not jyutping or not _CJK.search(char):
        return
    # HK orthography: 覈→核 (rime words.yaml over-uses 覈)
    char = to_traditional(char)
    candidate = _NORMALIZER.normalize_candidate(char, jyutping, source_id=source_id)
    if not candidate:
        return
    key = (candidate.char, candidate.jyutping)
    if key in seen:
        return
    seen.add(key)
    out.append(candidate)


def _full_pycantonese_reading(text: str) -> Optional[str]:
    try:
        import pycantonese
    except ImportError:
        return None

    try:
        pairs = pycantonese.characters_to_jyutping(text)
    except Exception:
        return None
    if not pairs:
        return None
    if len(pairs) == 1 and pairs[0][0] == text and pairs[0][1]:
        return str(pairs[0][1]).strip() or None
    if "".join(str(p[0]) for p in pairs) != text:
        return None
    if any(not p[1] for p in pairs):
        return None
    return " ".join(str(p[1]).strip() for p in pairs if p[1])


def _full_pyjyutping_reading(text: str) -> Optional[str]:
    try:
        from pyjyutping import jyutping
    except Exception:
        return None
    try:
        reading = jyutping.convert(text)
    except Exception:
        return None
    reading = str(reading or "").strip()
    return reading or None


def resolve_generated_jyutping(text: str) -> Optional[str]:
    """Maintainer import helper: pycantonese first, pyjyutping fallback."""
    return _full_pycantonese_reading(text) or _full_pyjyutping_reading(text)


def empty_rime_phrase_stats() -> dict[str, int]:
    return {key: 0 for key in _RIME_PHRASE_STAT_KEYS}


def _bump(stats: dict[str, int] | None, key: str) -> None:
    if stats is not None:
        stats[key] = int(stats.get(key, 0)) + 1


def _load_phrase_line_set(path: Path | str | None) -> set[str]:
    if not path:
        return set()
    allow_path = Path(path)
    if not allow_path.is_file():
        return set()
    try:
        lines = allow_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return set()
    return {
        to_traditional(line.strip())
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    }


def _load_phrase_allowlist(path: Path | str | None) -> set[str]:
    return _load_phrase_line_set(path)


def _load_phrase_reject_suffixes(path: Path | str | None) -> frozenset[str]:
    extra = _load_phrase_line_set(path)
    return frozenset(_PHRASE_ORG_PLACE_SUFFIXES | extra)


def _load_phrase_reject_literals(path: Path | str | None) -> frozenset[str]:
    return frozenset(_load_phrase_line_set(path))


def _looks_like_phrase_place_or_org(literal: str, reject_suffixes: frozenset[str]) -> bool:
    if any(literal.endswith(suffix) for suffix in reject_suffixes):
        return True
    # ponytail: ≥4 字且「路」結尾先拒（保留「套路」「出路」等二字詞）
    return len(literal) >= 4 and literal.endswith("路")


def _rime_phrase_rejection(
    literal: str,
    allowlist_8: set[str],
    reject_suffixes: frozenset[str],
    reject_literals: frozenset[str] | None = None,
) -> str | None:
    if not _CJK_ONLY.match(literal):
        return "rejected_mixed"
    length = len(literal)
    if length < 2:
        return "rejected_short"
    if length > 8:
        return "rejected_long"
    if reject_literals and literal in reject_literals:
        return "rejected_literal"
    if _looks_like_phrase_place_or_org(literal, reject_suffixes):
        return "rejected_place_or_org"
    if length == 8 and literal not in allowlist_8:
        return "rejected_8_char_needs_review"
    return None


def ingest_hsk30_wordlist(path: Path | str, *, source_id: str) -> list[LexiconCandidate]:
    txt_path = Path(path)
    if not txt_path.is_file():
        return []
    try:
        text = txt_path.read_text(encoding="utf-8")
    except OSError:
        return []

    out: list[LexiconCandidate] = []
    seen_words: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    for match in _CJK_WORD.finditer(text):
        literal = to_traditional(match.group(0).strip())
        if len(literal) < 2 or _HSK_NOISE.search(literal):
            continue
        if literal in seen_words:
            continue
        seen_words.add(literal)
        jyutping = resolve_generated_jyutping(literal)
        if not jyutping:
            continue
        _append_candidate(out, seen_pairs, char=literal, jyutping=jyutping, source_id=source_id)
    return out


def ingest_rime_words_yaml(path: Path | str, *, source_id: str) -> list[LexiconCandidate]:
    yaml_path = Path(path)
    if not yaml_path.is_file():
        return []
    try:
        text = yaml_path.read_text(encoding="utf-8-sig")
    except OSError:
        return []

    out: list[LexiconCandidate] = []
    seen: set[tuple[str, str]] = set()
    in_body = False
    for raw in text.splitlines():
        line = raw.strip()
        if not in_body:
            if line == "...":
                in_body = True
            continue
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        char = parts[0].strip()
        jyutping = parts[1].strip()
        _append_candidate(out, seen, char=char, jyutping=jyutping, source_id=source_id)
    return out


def ingest_rime_upstream_csvs(
    word_csv_path: Path | str,
    *,
    source_id: str,
) -> list[LexiconCandidate]:
    """Read the upstream lexical categories; proper_nouns.csv is intentionally excluded."""
    root = Path(word_csv_path).parent
    out: list[LexiconCandidate] = []
    seen: set[tuple[str, str]] = set()
    for name in _RIME_UPSTREAM_WORD_FILES:
        path = root / name
        if not path.is_file():
            continue
        try:
            with path.open(encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    literal = str(row.get("char") or "").strip()
                    if _looks_like_phrase_place_or_org(
                        literal, _PHRASE_ORG_PLACE_SUFFIXES
                    ):
                        continue
                    _append_candidate(
                        out,
                        seen,
                        char=literal,
                        jyutping=str(row.get("jyutping") or "").strip(),
                        source_id=source_id,
                    )
        except OSError:
            continue
    return out


def ingest_rime_phrase_yaml(
    path: Path | str,
    *,
    source_id: str,
    allowlist_path: Path | str | None = None,
    reject_suffixes_path: Path | str | None = None,
    reject_literals_path: Path | str | None = None,
    stats: dict[str, int] | None = None,
) -> list[LexiconCandidate]:
    yaml_path = Path(path)
    if not yaml_path.is_file():
        return []
    try:
        text = yaml_path.read_text(encoding="utf-8-sig")
    except OSError:
        return []

    allowlist_8 = _load_phrase_allowlist(allowlist_path)
    reject_suffixes = _load_phrase_reject_suffixes(reject_suffixes_path)
    reject_literals = _load_phrase_reject_literals(reject_literals_path)
    out: list[LexiconCandidate] = []
    seen_literals: set[str] = set()
    seen_pairs: set[tuple[str, str]] = set()
    in_body = False
    for raw in text.splitlines():
        line = raw.strip()
        if not in_body:
            if line == "...":
                in_body = True
            continue
        if not line or line.startswith("#"):
            continue
        _bump(stats, "body_rows")
        literal = to_traditional(line.split("\t", 1)[0].strip())
        if literal in seen_literals:
            _bump(stats, "duplicate_literal")
            continue
        seen_literals.add(literal)
        rejection = _rime_phrase_rejection(
            literal, allowlist_8, reject_suffixes, reject_literals
        )
        if rejection:
            _bump(stats, rejection)
            continue
        jyutping = resolve_generated_jyutping(literal)
        if not jyutping:
            _bump(stats, "missing_jyutping")
            continue
        before = len(out)
        _append_candidate(out, seen_pairs, char=literal, jyutping=jyutping, source_id=source_id)
        if len(out) == before:
            _bump(stats, "invalid_reading")
            continue
        _bump(stats, "accepted")
        if len(literal) == 8:
            _bump(stats, "accepted_8_char_allowlisted")
    return out


def ingest_words_hk_wordslist(path: Path | str, *, source_id: str) -> list[LexiconCandidate]:
    json_path = Path(path)
    if not json_path.is_file():
        return []
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return ingest_lexicon_json(json_path, source_id=source_id)
    if not isinstance(data, dict):
        return []
    out: list[LexiconCandidate] = []
    seen: set[tuple[str, str]] = set()
    for char, readings in data.items():
        literal = str(char or "").strip()
        if not literal:
            continue
        if not isinstance(readings, list):
            continue
        if not _CJK.search(literal) and not re.search(r"[A-Za-z0-9]", literal):
            continue
        for raw_jy in readings:
            jyutping = str(raw_jy or "").strip()
            if not jyutping and re.search(r"[A-Za-z0-9]", literal) and _CJK.search(literal):
                jyutping = str(_generate_mixed_literal_jyutping(literal) or "").strip()
            candidate = _NORMALIZER.normalize_candidate(literal, jyutping, source_id=source_id)
            if not candidate:
                continue
            key = (candidate.char, candidate.jyutping)
            if key in seen:
                continue
            seen.add(key)
            out.append(candidate)
    return out


def _candidates_from_kaifang_array(arr: list, *, source_id: str) -> list[LexiconCandidate]:
    out: list[LexiconCandidate] = []
    seen: set[tuple[str, str]] = set()
    i = 0
    while i < len(arr):
        char = str(arr[i] or "").strip()
        i += 1
        if not char or not _CJK.search(char):
            continue
        syllables: list[str] = []
        while len(syllables) < len(char) and i < len(arr):
            token = str(arr[i] or "").strip()
            if _JYUTPING_TOKEN.match(token):
                syllables.append(token)
                i += 1
            else:
                break
        if len(syllables) != len(char):
            continue
        jyutping = " ".join(syllables)
        if len(char) == 1 and i < len(arr):
            gloss = str(arr[i] or "").strip()
            if gloss and not _JYUTPING_TOKEN.match(gloss):
                i += 1
        _append_candidate(out, seen, char=char, jyutping=jyutping, source_id=source_id)
    return out


def ingest_kaifang_txt(path: Path | str, *, source_id: str) -> list[LexiconCandidate]:
    txt_path = Path(path)
    if not txt_path.is_file():
        return []
    try:
        text = txt_path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("["):
            continue
        try:
            arr = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(arr, list):
            return _candidates_from_kaifang_array(arr, source_id=source_id)
    return []


def ingest_source(src: Dict[str, Any]) -> list[LexiconCandidate]:
    parser = str(src.get("parser") or "")
    source_id = str(src.get("id") or "")
    if parser == "rime_char":
        path = resolve_source_path(src) or Path("")
        return ingest_rime_char_csv(path)
    if parser == "words_hk_wordslist":
        path = resolve_lexicon_raw_path(src) or Path("")
        return ingest_words_hk_wordslist(path, source_id=source_id)
    if parser == "kaifang_txt":
        path = resolve_lexicon_raw_path(src) or Path("")
        return ingest_kaifang_txt(path, source_id=source_id)
    if parser == "lexicon_json":
        path = resolve_lexicon_raw_path(src) or resolve_source_path(src) or Path("")
        return ingest_lexicon_json(path, source_id=source_id)
    if parser == "hsk30_wordlist":
        path = resolve_lexicon_raw_path(src) or Path("")
        return ingest_hsk30_wordlist(path, source_id=source_id)
    if parser == "rime_words_yaml":
        path = resolve_lexicon_raw_path(src) or Path("")
        return ingest_rime_words_yaml(path, source_id=source_id)
    if parser == "rime_upstream_csv":
        path = resolve_lexicon_raw_path(src) or Path("")
        return ingest_rime_upstream_csvs(path, source_id=source_id)
    if parser == "rime_phrase_yaml":
        path = resolve_lexicon_raw_path(src) or Path("")
        allowlist_raw = src.get("allowlist_path") or ""
        allowlist_path = Path(allowlist_raw) if allowlist_raw else None
        if allowlist_path and not allowlist_path.is_absolute():
            allowlist_path = ROOT / allowlist_path
        reject_raw = src.get("reject_suffixes_path") or ""
        reject_path = Path(reject_raw) if reject_raw else None
        if reject_path and not reject_path.is_absolute():
            reject_path = ROOT / reject_path
        lit_raw = src.get("reject_literals_path") or ""
        lit_path = Path(lit_raw) if lit_raw else None
        if lit_path and not lit_path.is_absolute():
            lit_path = ROOT / lit_path
        return ingest_rime_phrase_yaml(
            path,
            source_id=source_id,
            allowlist_path=allowlist_path,
            reject_suffixes_path=reject_path,
            reject_literals_path=lit_path,
        )
    return []
