import json
from typing import List, Optional, Tuple

TONE_MAP = {1: "3", 2: "9", 3: "4", 4: "0", 5: "4", 6: "2"}
VOWELS = "aeiou"
M1_MAPPING = {"5": "4", "4": "5", "6": "2", "2": "6", "9": "3", "3": "9"}


def get_0243_code(jyutping: str) -> str:
    """根據 jyutping 產生 0243 code"""
    if not jyutping:
        return ""

    syllables = jyutping.strip().split()
    return "".join(TONE_MAP.get(int(syl[-1]), "?") if syl and syl[-1].isdigit() else "?" for syl in syllables)


from jyutping_table import JYUTPING_TABLE, SPECIAL_CASES  # noqa: E402,F401


def split_jyutping(jyutping: str) -> Tuple[str, str, str]:
    """將 jyutping 拆分成 initials, finals, tones 三個 list"""
    if not isinstance(jyutping, str) or not jyutping.strip():
        return "[]", "[]", "[]"

    initials_list: List[str] = []
    finals_list: List[str] = []
    tones_list: List[int] = []

    for syllable_text in jyutping.strip().split():
        tone = None
        syllable = syllable_text
        for index in range(len(syllable_text) - 1, -1, -1):
            if syllable_text[index].isdigit():
                tone = int(syllable_text[index])
                syllable = syllable_text[:index]
                break

        if syllable in {"m", "ng"}:
            initials_list.append(syllable)
            finals_list.append("")
            tones_list.append(tone)
            continue

        split_pos = next((pos for pos, char in enumerate(syllable) if char in VOWELS), -1)
        initial = syllable[:split_pos] if split_pos != -1 else syllable
        final = syllable[split_pos:] if split_pos != -1 else ""

        initials_list.append(initial)
        finals_list.append(final)
        tones_list.append(tone)

    return json.dumps(initials_list), json.dumps(finals_list), json.dumps(tones_list)


def get_code_variants(code: str, mode: str = "m2") -> List[str]:
    """生成 m1 / m2 的 code 等價變體"""
    if not code or not code.isdigit():
        return [code]

    variants = {code}

    if mode == "m1":
        for old, new in M1_MAPPING.items():
            if old in code:
                variants.add(code.replace(old, new))

        for index, digit in enumerate(code):
            if digit in M1_MAPPING:
                variants.add(code[:index] + M1_MAPPING[digit] + code[index + 1:])

    return sorted(variants)


# ==================== Vector Embedding（語義相似度排序優化， ingest-only） ====================
# 重要 redesign（回應使用者要求「完全不載入 MiniLM 仍能使用功能」）：
# - 在**正常 runtime**（只裝 requirements.txt）下，**永遠不會** 載入 paraphrase-multilingual-MiniLM-L12-v2。
# - get_text_embedding 在沒有 sentence-transformers 的環境下會**安靜地** 永遠 return []，不會啟動任何背景 thread，也不會印任何載入訊息。
# - 模型只會在明確的 ingest 腳本（generate_relationships.py，使用 requirements-dev.txt）中被載入，用來預先產生 word_relations 裡的 semantic_related 記錄。
# - Syn mode 已經完全依賴 precomputed word_relations + static thesaurus，不再需要 runtime embedding。
# - 任何剩餘的 semantic re-rank 路徑都必須先檢查 is_ready()，否則直接跳過。

_embedding_model = None
_embedding_load_started = False
_embedding_available = None   # 三態：None=尚未檢查, True=可用, False=不可用（永久）

# Hard guard: embedding model loading is ONLY permitted during explicit ingest
# (generate_relationships.py). Normal server startup must never load it.
_ingest_mode_embedding = False

def _check_embedding_available():
    """只在第一次真正需要時檢查一次 sentence-transformers 是否存在。
    Even if the package is importable, we refuse to load the model unless
    we are explicitly in ingest mode (set by generate_relationships.py).
    """
    global _embedding_available
    if _embedding_available is not None:
        return _embedding_available
    if not _ingest_mode_embedding:
        _embedding_available = False
        return False
    try:
        import sentence_transformers  # noqa
        _embedding_available = True
    except ImportError:
        _embedding_available = False
    return _embedding_available

def _load_embedding_model_in_background():
    """Background loader. 只在 ingest 情境下才會被呼叫。"""
    global _embedding_model, _embedding_load_started
    try:
        import os
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        from sentence_transformers import SentenceTransformer
        # 只有在 ingest 時才印這個訊息（正常 runtime 不應該走到這裡）
        print("[embedding] 正在背景載入 paraphrase-multilingual-MiniLM-L12-v2 ... (首次會較久，之後快)")
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        _embedding_model = model
        get_text_embedding._model = model
        print("[embedding] Vector embedding model 已就緒（僅供 ingest 使用）。")
    except Exception as e:
        print(f"[embedding] 載入模型失敗（{e}）")
    finally:
        _embedding_load_started = False

def get_text_embedding(text: str) -> list[float]:
    """
    產生文字的 vector embedding。

    **Strict runtime policy (final redesign)**:
    - This function will **NEVER** cause the MiniLM model to be loaded during normal
      server startup (`python main.py`, uvicorn, etc.), even if sentence-transformers
      is importable in the current Python environment.
    - Model loading is **only** allowed when `_ingest_mode_embedding` is True
      (set exclusively by generate_relationships.py before it needs embeddings).
    - In all other cases it returns [] silently. No threads, no HF warnings,
      no "正在背景載入" messages.
    - Syn/ant and all core dictionary features are fully independent of this model
      thanks to precomputed word_relations + static thesaurus.
    """
    if not text or not text.strip():
        return []

    if not _check_embedding_available():
        # Normal runtime or ingest not explicitly enabled: silent no-op.
        return []

    global _embedding_model, _embedding_load_started

    if _embedding_model is None:
        if not _embedding_load_started:
            _embedding_load_started = True
            import threading
            threading.Thread(target=_load_embedding_model_in_background, daemon=True).start()
        return []

    try:
        emb = _embedding_model.encode(text, normalize_embeddings=True)
        return emb.tolist()
    except Exception as e:  # P1 fix: include exception type for better diagnostics
        print(f"[embedding] 無法產生 embedding（{type(e).__name__}: {e}）")
        return []

def is_embedding_model_ready() -> bool:
    """回傳目前 vector embedding 模型是否已經載入完畢。
    在純 runtime 環境下永遠回傳 False。
    """
    global _embedding_model
    return _embedding_model is not None

# 相容舊的 hasattr / is_ready 檢查
get_text_embedding._model = None
get_text_embedding.is_ready = is_embedding_model_ready


def enable_embedding_model_for_ingest() -> None:
    """
    Call this **only** from ingest-time scripts (e.g. generate_relationships.py)
    when you have installed the dev dependencies and explicitly want to load
    the MiniLM model to compute fresh embeddings for relation discovery.

    After calling this, subsequent calls to get_text_embedding() may load the model
    (in a background thread) and you will see the loading message.

    Normal server processes must never call this.
    """
    global _ingest_mode_embedding
    _ingest_mode_embedding = True
    # Proactively reduce HF noise for ingest runs
    import os
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """計算兩個向量的 cosine similarity（純 Python 實作，供 SQLite 端 semantic re-rank 使用）。

    若環境有 numpy 會自動加速，否則使用純 Python fallback。
    回傳值範圍約 [-1, 1]，1 表示完全相同方向。
    """
    if not a or not b or len(a) != len(b):
        return 0.0
    try:
        import numpy as np
        va = np.array(a, dtype=float)
        vb = np.array(b, dtype=float)
        denom = np.linalg.norm(va) * np.linalg.norm(vb)
        if denom == 0:
            return 0.0
        return float(np.dot(va, vb) / denom)
    except Exception:
        # 純 Python fallback
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        denom = norm_a * norm_b
        if denom == 0:
            return 0.0
        return dot / denom


# ==================== Synonym / Antonym index & thesaurus (for mode='syn') ====================
# Runtime uses static dictionaries + precomputed word_relations. Embedding helpers are ingest-only.

import os

# Public version of the old private _load_json_list (moved from routers/word.py for preload sharing)
def load_json_list(value: Optional[object]) -> List[object]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


# --- Embedding matrix for fast vectorized syn/ant (top-k cosine / low-sim) ---
_syn_chars: List[str] = []
_syn_emb_mat = None  # numpy.ndarray (N, 384) float32, row-normalized; or None if unavailable

def set_synonym_index(chars: List[str], mat) -> None:
    """Set global preloaded synonym index (called from main preload daemon)."""
    global _syn_chars, _syn_emb_mat
    _syn_chars = list(chars) if chars else []
    _syn_emb_mat = mat

def get_synonym_index() -> Tuple[List[str], Optional[object]]:
    """Return (chars, emb_mat) for handle_syn_ant_search. mat may be None."""
    return _syn_chars, _syn_emb_mat


# --- Light parsers for vendor static data (cilin for syn groups, antisem/guotong for ant) ---
# All pure stdlib, small memory, graceful if files missing (utf-8 then gbk fallback).

_cilin_syns: dict = {}   # word -> list of curated synonyms from same Cilin group
_ant_dict: dict = {}     # word -> list of antonyms (priority: ChineseAntiword antisem.txt)
_syn_dict: dict = {}     # word -> list of synonyms (guotong thesaurus)

def load_cilin_index(path: str = "data/cilin/new_cilin.txt") -> None:
    """Parse Cilin V3 style: lines like 'Aa01A01 人民 民 国民 ...' (group code + space words).
    Build bidirectional within-group links (exclude self).
    """
    global _cilin_syns
    if not os.path.exists(path):
        return
    groups = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    groups.append(parts[1:])  # skip code, take words
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="gbk") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        groups.append(parts[1:])
        except Exception:
            return
    except Exception:
        return

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
    """Parse antisem.txt style: '快乐:悲伤;伤心;难过' or 'word ant1 ant2' lines."""
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
            # make bidirectional for antonym pairs/lists
            for ant in ants:
                if ant not in d:
                    d[ant] = []
                if left not in d[ant]:
                    d[ant].append(left)
    _ant_dict = d

def load_thesaurus_dicts(syn_path: str = "data/thesaurus/dict_synonym.txt",
                         ant_path: str = "data/thesaurus/dict_antonym.txt") -> None:
    """Parse guotong style simple pair/list files into _syn_dict / _ant_dict (supplement)."""
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
            # Robust guotong parse:
            # - Handle "CODE= word1 word2 ..." for synonym groups (skip code part)
            # - Normalize "A——B", "A—B", "A B" separators
            # - For both syn and ant, make relations bidirectional (pairs and groups are mutual)
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
    # Dedup
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
    a = list(_ant_dict.get(q, []))  # priority antisem then thesaurus
    if q in a:
        a.remove(q)
    return a[:12]  # reasonable cap

_thesaurus_loaded = False

def ensure_thesaurus_loaded(force: bool = False) -> None:
    """Load static syn/ant dictionaries once per process."""
    global _thesaurus_loaded
    if _thesaurus_loaded and not force:
        return
    load_cilin_index()
    load_antonym_dict()
    load_thesaurus_dicts()
    _thesaurus_loaded = True


# ==================== In-memory Word Cache for Instant Mask/Hybrid/Wildcard Paths ====================
# === Naming Convention (enforced) ===
# 禁止使用 "hanzi"。處理粵語字符相關邏輯時必須使用 "canto" 或 "chars"。
# 詳見 README.md「命名慣例」小節與 WORKLOG.md 最新條目。
# Never introduce identifiers or functions named with "hanzi". Use "canto" or "chars".
# Preloaded at startup (daemon in main.py, mirroring syn matrix preload) for zero-cost .all() on length=N
# + pre-parsed finals/code (no json.loads in hot query loops) + O(1) char meta for ref lookups (last_ch, literal canto in "門0").
# Short N (lyrics words) dominate; full short-length buckets kept in RAM (~50-150MB acceptable).
# Fallback to DB if cache empty (e.g. early query before preload or test in-mem DB).
# _ensure after insert calls update so new injected words (rare) participate immediately.
# No DB regex anywhere; all position/code/final matching stays in Python (per prior rule).
# Reuses load_json_list for parse-once at preload time.

_length_buckets: dict = {}   # int length -> list[dict] with pre-parsed 'finals':list, 'code':str etc.
_char_meta: dict = {}        # char -> list[dict], preserving multiple pronunciations/codes.
_bucket_entry_index: dict = {}  # length -> {(char, code, jyutping): index}

def _entry_key(entry: dict) -> tuple:
    return (entry.get("char") or "", entry.get("code") or "", entry.get("jyutping") or "")

def populate_word_cache_from_rows(rows: list) -> int:
    """Populate from pre-fetched rows (caller does the SELECT to avoid cycles).
    rows items: dict-like or tuple (char, code, jyutping, finals, initials, length).
    Parses finals/initials ONCE here. Returns count of entries added.
    Safe to call multiple times (idempotent per char; later wins for updates).
    """
    global _length_buckets, _char_meta, _bucket_entry_index
    added = 0
    for r in rows or []:
        if isinstance(r, (list, tuple)):
            char, code, jyut, finals_raw, inits_raw, length = r[0], r[1], r[2], r[3], r[4], r[5]
        else:
            # Support sqlalchemy Row (attr + index), dict, and plain objects
            def _g(obj, k, default=""):
                try:
                    if hasattr(obj, "get"):
                        return obj.get(k, default)
                    return getattr(obj, k, default)
                except Exception:
                    try:
                        return obj[k] if k in obj else default  # last resort for mapping-like
                    except Exception:
                        return default
            char = _g(r, "char", None)
            code = _g(r, "code", "")
            jyut = _g(r, "jyutping", "")
            finals_raw = _g(r, "finals", None)
            inits_raw = _g(r, "initials", None)
            length = _g(r, "length", None)
            if length is None and char:
                length = len(char)
        if not char:
            continue
        finals = load_json_list(finals_raw)
        inits = load_json_list(inits_raw)
        length = int(length) if length is not None else len(char or "")
        entry = {
            "char": char,
            "code": code or "",
            "jyutping": jyut or "",
            "finals": finals,
            "initials": inits,
            "length": length,
        }
        # bucket (O(1) dedup via index map), preserving same char with multiple readings.
        bucket = _length_buckets.setdefault(length, [])
        idx_map = _bucket_entry_index.setdefault(length, {})
        key = _entry_key(entry)
        if key in idx_map:
            bucket[idx_map[key]] = entry
        else:
            idx_map[key] = len(bucket)
            bucket.append(entry)
        metas = _char_meta.setdefault(char, [])
        for idx, existing in enumerate(metas):
            if _entry_key(existing) == key:
                metas[idx] = entry
                break
        else:
            metas.append(entry)
        added += 1
    return added

def get_words_for_length(n: int) -> list:
    """Return pre-parsed entries for exact length (mask/hybrid use). Empty list if not populated."""
    return _length_buckets.get(int(n) if n else 0, []) or []

def get_char_meta(ch: str):
    """Fast lookup for a single char's first pre-parsed reading. None if unknown."""
    if not ch:
        return None
    metas = _char_meta.get(ch) or []
    return metas[0] if metas else None

def get_char_metas(ch: str) -> list:
    """Return all pre-parsed readings for a char, preserving multiple codes/jyutpings."""
    if not ch:
        return []
    return list(_char_meta.get(ch) or [])

def update_word_in_cache(char: str, code: str = "", jyutping: str = "", finals: object = None, initials: object = None, length: int = None):
    """Called by _ensure after successful insert of a new canto word so it participates in future mask etc without restart.
    Accepts raw (json str or list) for finals/initials.
    """
    global _length_buckets, _char_meta, _bucket_entry_index
    if not char:
        return
    f = load_json_list(finals)
    i = load_json_list(initials)
    ln = int(length) if length is not None else len(char)
    entry = {
        "char": char,
        "code": code or "",
        "jyutping": jyutping or "",
        "finals": f,
        "initials": i,
        "length": ln,
    }
    bucket = _length_buckets.setdefault(ln, [])
    idx_map = _bucket_entry_index.setdefault(ln, {})
    key = _entry_key(entry)
    if key in idx_map:
        bucket[idx_map[key]] = entry
    else:
        idx_map[key] = len(bucket)
        bucket.append(entry)
    metas = _char_meta.setdefault(char, [])
    for idx, existing in enumerate(metas):
        if _entry_key(existing) == key:
            metas[idx] = entry
            break
    else:
        metas.append(entry)

def get_word_cache_stats() -> dict:
    """Debug/helper: sizes and max length present."""
    lens = sorted(_length_buckets.keys())
    total = sum(len(v) for v in _length_buckets.values())
    return {
        "total_entries": total,
        "lengths": lens,
        "max_length": max(lens) if lens else 0,
        "meta_size": len(_char_meta),
    }


# ==================== Embedding readiness helper ====================
def is_embedding_model_ready() -> bool:
    """回傳目前 vector embedding 模型是否已經載入完畢。
    載入期間 semantic re-rank 與 syn vector 會自動 fallback，不影響基本功能。
    """
    global _embedding_model
    return _embedding_model is not None

# 讓舊的 `hasattr(get_text_embedding, "_model")` 檢查繼續有效
get_text_embedding._model = None
get_text_embedding.is_ready = is_embedding_model_ready