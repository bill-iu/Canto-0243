import json
from typing import List, Tuple

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


# ==================== Vector Embedding（語義相似度排序優化，同時支援 Postgres 與 SQLite） ====================
# 使用 sentence-transformers 多語言模型產生 embedding
# - Postgres 端：存入 pgvector Vector 欄位，可用原生 cosine_distance 在 DB 排序
# - SQLite 端（本地開發）：存入 JSON 文字，搜尋時用 Python cosine re-rank 候選結果
# 兩個版本的 semantic 排序行為一致（只是實作差異）
#
# 重要：模型載入現在是「背景非阻塞」的。
# - 第一次呼叫 get_text_embedding 會立即觸發背景 thread 去載入，不會 block 當前請求。
# - 載入期間所有呼叫都回傳 []，呼叫端（m1/m2 semantic re-rank、syn mode）會自動 graceful fallback。
# - 載入完成後，全域可用，後續請求自動獲得語義功能。
# 這樣可以達到「一開啟後端就可以用」（基本搜尋、static thesaurus 立即可用），embedding 幾秒後在背景 ready。

_embedding_model = None
_embedding_load_started = False

def _load_embedding_model_in_background():
    """Background loader. Never blocks request threads."""
    global _embedding_model, _embedding_load_started
    try:
        import os
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        from sentence_transformers import SentenceTransformer
        print("[embedding] 正在背景載入 paraphrase-multilingual-MiniLM-L12-v2 ... (首次會較久，之後快)")
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        _embedding_model = model
        # 相容舊的 hasattr 檢查
        get_text_embedding._model = model
        print("[embedding] Vector embedding model 已就緒，semantic 功能啟用。")
    except Exception as e:
        print(f"[embedding] 載入模型失敗（{e}），semantic 相關功能將停用（仍可正常使用基本搜尋與 static thesaurus）")
    finally:
        _embedding_load_started = False

def get_text_embedding(text: str) -> list[float]:
    """產生文字的 vector embedding（用於 semantic similarity 排序優化）。

    預設模型：paraphrase-multilingual-MiniLM-L12-v2（384 dim，多語言，適合中文/粵語）
    - 模型載入改為背景 thread，不阻塞任何 API 請求。
    - 載入完成前會回傳 []，呼叫端自動退回傳統/靜態結果。
    - 想「一開啟就可用」：後端啟動後立即可搜，embedding 功能在背景 warm up。
    """
    if not text or not text.strip():
        return []
    global _embedding_model, _embedding_load_started

    if _embedding_model is None:
        # 尚未載入 → 觸發背景載入（只觸發一次）
        if not _embedding_load_started:
            _embedding_load_started = True
            import threading
            threading.Thread(target=_load_embedding_model_in_background, daemon=True).start()
        # 立即回傳空，讓呼叫端 fallback（不會卡住 UI）
        return []

    try:
        emb = _embedding_model.encode(text, normalize_embeddings=True)
        return emb.tolist()
    except Exception as e:
        print(f"[embedding] 無法產生 embedding（{e}），semantic sorting 將退回傳統模式")
        return []


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
# Preloaded at startup (daemon in main.py) for instant <0.1s vectorized lookup + static curated data.
# Reuses existing numpy + get_text_embedding model. Small vendor txts from the 4 GitHubs preferred.
# near-synonym (5th) is optional and handled with try/except in the router handle.

import os
import json
from typing import List, Tuple, Optional

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
            # Accept "w1 w2", "w1——w2", "w1 w2 w3" etc.
            parts = [x.strip() for x in line.replace("——", " ").replace("—", " ").split() if x.strip()]
            if len(parts) >= 2:
                w = parts[0]
                others = parts[1:]
                if target is _syn_dict:
                    _syn_dict.setdefault(w, []).extend(others)
                else:
                    _ant_dict.setdefault(w, []).extend(others)
    # Dedup
    for dd in (_syn_dict, _ant_dict):
        for k in list(dd.keys()):
            dd[k] = sorted(set(dd[k]))

def get_synonyms(q: str) -> List[str]:
    if not q:
        return []
    s = set(get_cilin_synonyms(q))
    s.update(_syn_dict.get(q, []))
    if q in s:
        s.remove(q)
    return sorted(s)

def get_antonyms(q: str) -> List[str]:
    if not q:
        return []
    a = list(_ant_dict.get(q, []))  # priority antisem then thesaurus
    if q in a:
        a.remove(q)
    return a[:12]  # reasonable cap

# Auto-attempt light loads at import time (non-fatal; full preload daemon will call again safely)
try:
    load_cilin_index()
    load_antonym_dict()
    load_thesaurus_dicts()
except Exception:
    pass


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
_char_meta: dict = {}        # char -> minimal dict for fast ref (finals list, code, length, jyutping)

def populate_word_cache_from_rows(rows: list) -> int:
    """Populate from pre-fetched rows (caller does the SELECT to avoid cycles).
    rows items: dict-like or tuple (char, code, jyutping, finals, initials, length).
    Parses finals/initials ONCE here. Returns count of entries added.
    Safe to call multiple times (idempotent per char; later wins for updates).
    """
    global _length_buckets, _char_meta
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
        # bucket
        _length_buckets.setdefault(length, [])
        # avoid dups in bucket (by char)
        if not any(e["char"] == char for e in _length_buckets[length]):
            _length_buckets[length].append(entry)
        # meta (latest wins)
        _char_meta[char] = entry
        added += 1
    return added

def get_words_for_length(n: int) -> list:
    """Return pre-parsed entries for exact length (mask/hybrid use). Empty list if not populated."""
    return _length_buckets.get(int(n) if n else 0, []) or []

def get_char_meta(ch: str):
    """Fast lookup for a single char's pre-parsed finals/code etc. None if unknown (caller falls back to DB/ensure)."""
    if not ch:
        return None
    return _char_meta.get(ch)

def update_word_in_cache(char: str, code: str = "", jyutping: str = "", finals: object = None, initials: object = None, length: int = None):
    """Called by _ensure after successful insert of a new canto word so it participates in future mask etc without restart.
    Accepts raw (json str or list) for finals/initials.
    """
    global _length_buckets, _char_meta
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
    _length_buckets.setdefault(ln, [])
    # replace or append
    for idx, e in enumerate(_length_buckets[ln]):
        if e["char"] == char:
            _length_buckets[ln][idx] = entry
            break
    else:
        _length_buckets[ln].append(entry)
    _char_meta[char] = entry

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