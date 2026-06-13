import os
from typing import Iterator, List, Tuple

from app.domain.relations.valid_term import normalize_literal

_cilin_syns: dict = {}
_ant_dict: dict = {}
_syn_dict: dict = {}
_thesaurus_loaded = False

_syn_chars: List[str] = []
_syn_emb_mat = None


def set_synonym_index(chars: List[str], mat) -> None:
    global _syn_chars, _syn_emb_mat
    _syn_chars = list(chars) if chars else []
    _syn_emb_mat = mat


def get_synonym_index() -> Tuple[List[str], object]:
    return _syn_chars, _syn_emb_mat


def iter_antonym_edges() -> Iterator[Tuple[str, str]]:
    for ch, ants in _ant_dict.items():
        for ant in ants or []:
            yield ch, ant


def iter_literal_heads() -> Iterator[str]:
    seen = set(_cilin_syns.keys()) | set(_syn_dict.keys()) | set(_ant_dict.keys())
    return iter(sorted(seen))


def get_guotong_synonyms(word: str) -> List[str]:
    return _syn_dict.get(word, []) if word else []


def _literal_tokens_from_parts(parts: List[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for raw in parts:
        t = normalize_literal(raw)
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def load_cilin_index(path: str = "data/cilin/new_cilin.txt") -> None:
    global _cilin_syns
    if not os.path.exists(path):
        return
    groups = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="gbk") as f:
                lines = f.readlines()
        except Exception:
            return
    except Exception:
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        code = parts[0]
        if not code.endswith("=") or len(code) < 8:
            continue
        words = _literal_tokens_from_parts(parts[1:])
        if len(words) < 2:
            continue
        groups.append(words)

    word_to_group = {}
    for g in groups:
        for w in g:
            if w:
                word_to_group.setdefault(w, []).append(g)

    out = {}
    for w, gs in word_to_group.items():
        syns = set()
        for g in gs:
            for x in g:
                if x and x != w:
                    syns.add(x)
        if syns:
            out[w] = sorted(syns)
    _cilin_syns = out


def get_cilin_synonyms(word: str) -> List[str]:
    return _cilin_syns.get(word, []) if word else []


def load_antonym_dict(path: str = "data/antonym/antisem.txt") -> None:
    global _ant_dict
    if not os.path.exists(path):
        return
    d = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="gbk") as f:
                lines = f.readlines()
        except Exception:
            return
    except Exception:
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line and " " not in line:
            continue
        if ":" in line:
            left, right = line.split(":", 1)
            ants = [x.strip() for x in right.replace("；", ";").split(";") if x.strip()]
        else:
            parts = line.split()
            if len(parts) < 2:
                continue
            left, ants = parts[0], parts[1:]
        head = normalize_literal(left)
        if not head:
            continue
        tail_list = _literal_tokens_from_parts(ants)
        if not tail_list:
            continue
        d[head] = tail_list
        for ant in tail_list:
            if ant not in d:
                d[ant] = []
            if head not in d[ant]:
                d[ant].append(head)
    _ant_dict = d


def load_thesaurus_dicts(
    syn_path: str = "data/thesaurus/dict_synonym.txt",
    ant_path: str = "data/thesaurus/dict_antonym.txt",
) -> None:
    global _syn_dict, _ant_dict
    for p, target in [(syn_path, _syn_dict), (ant_path, _ant_dict)]:
        if not os.path.exists(p):
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            try:
                with open(p, "r", encoding="gbk") as f:
                    lines = f.readlines()
            except Exception:
                continue
        except Exception:
            continue
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                line = line.split("=", 1)[1]
            parts = [x.strip() for x in line.replace("——", " ").replace("—", " ").replace("–", " ").split() if x.strip()]
            words = _literal_tokens_from_parts(parts)
            if len(words) < 2:
                continue
            if target is _syn_dict:
                for w in words:
                    for other in words:
                        if other != w:
                            _syn_dict.setdefault(w, []).append(other)
            else:
                for w in words:
                    for other in words:
                        if other != w:
                            _ant_dict.setdefault(w, []).append(other)
    for dd in (_syn_dict, _ant_dict):
        for k in list(dd.keys()):
            dd[k] = sorted(set(dd[k]))


def get_synonyms(q: str) -> List[str]:
    if not q:
        return []
    ensure_thesaurus_loaded()
    s = set(get_cilin_synonyms(q))
    s.update(_syn_dict.get(q, []))
    if q in s:
        s.remove(q)
    return sorted(s)


def get_antonyms(q: str) -> List[str]:
    if not q:
        return []
    ensure_thesaurus_loaded()
    a = list(_ant_dict.get(q, []))
    if q in a:
        a.remove(q)
    return a[:12]


def ensure_thesaurus_loaded(force: bool = False) -> None:
    global _thesaurus_loaded
    if _thesaurus_loaded and not force:
        return
    load_cilin_index()
    load_antonym_dict()
    load_thesaurus_dicts()
    _thesaurus_loaded = True


def mark_thesaurus_loaded() -> None:
    """Mark indexes as loaded without loading bundled defaults (custom path ingest)."""
    global _thesaurus_loaded
    _thesaurus_loaded = True


def reset_static_indexes_for_tests() -> None:
    """Clear in-memory static thesaurus indexes (tests only)."""
    global _cilin_syns, _ant_dict, _syn_dict, _thesaurus_loaded, _syn_chars, _syn_emb_mat
    _cilin_syns = {}
    _ant_dict = {}
    _syn_dict = {}
    _thesaurus_loaded = False
    _syn_chars = []
    _syn_emb_mat = None
