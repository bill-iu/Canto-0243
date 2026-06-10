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

def get_text_embedding(text: str) -> list[float]:
    """產生文字的 vector embedding（用於 semantic similarity 排序優化）。

    預設模型：paraphrase-multilingual-MiniLM-L12-v2（384 dim，多語言，適合中文/粵語）
    - 安裝 `sentence-transformers` 後即可使用（pip install sentence-transformers）。
    - 模型第一次載入會下載並佔用記憶體/時間，建議在 import_data 時 batch 預算。
    - 若未安裝或失敗，回傳 []，呼叫端應退回傳統排序（不會中斷）。
    """
    if not text or not text.strip():
        return []
    try:
        from sentence_transformers import SentenceTransformer
        # 全域 cache，避免重複載入模型
        if not hasattr(get_text_embedding, "_model"):
            get_text_embedding._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        model = get_text_embedding._model
        emb = model.encode(text, normalize_embeddings=True)
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