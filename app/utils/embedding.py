_embedding_model = None
_embedding_load_started = False
_embedding_available = None
_ingest_mode_embedding = False


def _check_embedding_available():
    global _embedding_available
    if _embedding_available is not None:
        return _embedding_available
    if not _ingest_mode_embedding:
        _embedding_available = False
        return False
    try:
        import sentence_transformers  # noqa: F401
        _embedding_available = True
    except ImportError:
        _embedding_available = False
    return _embedding_available


def _load_embedding_model_in_background():
    global _embedding_model, _embedding_load_started
    try:
        import os
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        from sentence_transformers import SentenceTransformer
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
    if not text or not text.strip():
        return []
    if not _check_embedding_available():
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
    except Exception as e:
        print(f"[embedding] 無法產生 embedding（{type(e).__name__}: {e}）")
        return []


def is_embedding_model_ready() -> bool:
    global _embedding_model
    return _embedding_model is not None


get_text_embedding._model = None
get_text_embedding.is_ready = is_embedding_model_ready


def enable_embedding_model_for_ingest() -> None:
    global _ingest_mode_embedding
    _ingest_mode_embedding = True
    import os
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def cosine_similarity(a: list[float], b: list[float]) -> float:
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
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        denom = norm_a * norm_b
        if denom == 0:
            return 0.0
        return dot / denom
