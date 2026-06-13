import os
from typing import Iterator, List, Tuple

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
        groups.append(parts[1:])

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
        if left and ants:
            d[left] = ants
            for ant in ants:
                if ant not in d:
                    d[ant] = []
                if left not in d[ant]:
                    d[ant].append(left)
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
            if len(parts) >= 2:
                if target is _syn_dict:
                    for w in parts:
                        for other in parts:
                            if other != w:
                                _syn_dict.setdefault(w, []).append(other)
                else:
                    for w in parts:
                        for other in parts:
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
