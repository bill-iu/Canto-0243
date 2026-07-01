#!/usr/bin/env python3
"""
generate_relationships.py

用途：
  在「ingest / 資料準備」階段，由 maintainer 執行，用來預先生成 words 之間的
  同義 (syn) / 反義 (ant) / 語意相關 (semantic_related) 關係，並存入
  word_relations 表。

  這樣 runtime（一般使用者執行服務查詢時）就可以用純 SQL 取得這些關係，
  完全不需要載入 sentence-transformers / torch 等重型 ML 套件。

核心原則：
  - 優先使用高品質的 static thesaurus（cilin、antisem、guotong）。
  - embedding 只是「可選」的輔助發現工具（只在 dev 環境執行本 script 時才需要）。
  - 產生的關係會標記 source，方便之後審計或過濾。
  - 新詞經 `python -m ingest build-db` 或關係補錄寫入 **詞條庫** 後，再跑本 script 產生關係（或本 script 支援自動處理新詞）。

使用方式：
  1. 安裝 dev 依賴（只有這時候才需要 ML 套件）：
       pip install -r requirements-dev.txt

  2. 執行（本地 SQLite）：
       python scripts/legacy/generate_relationships.py

  3. 正式環境（Postgres）：
       ENV=prod python scripts/legacy/generate_relationships.py

  選項：
    python scripts/legacy/generate_relationships.py --limit 500     # 只處理前 500 個詞（測試用）
    python scripts/legacy/generate_relationships.py --include-embedding   # 明確啟用 embedding 輔助（預設不載入 ML）

注意（redesign 後）：
  - **這是本專案中唯一合法載入 MiniLM / sentence-transformers 的地方**。
  - 只有安裝 requirements-dev.txt 並明確使用 --include-embedding 時才會觸發模型。
  - 正常 runtime（只裝 requirements.txt）啟動 server 時，**絕對不會** 載入模型，也不會印載入訊息。
  - 執行完後，syn/ant 搜尋完全依賴預先計算的 word_relations + static thesaurus（純 SQL + 輕量 static）。
  - 一般使用者只要 pip install -r requirements.txt 就能跑完整服務，無 ML 依賴。
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text, tuple_

# Proactively reduce noise from HF Hub when loading the model during ingest.
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from app.database import SessionLocal, IS_POSTGRES
from app.models.word import Word, WordRelation
from app.domain.relations.canonical import canonical_relation_dict, relation_storage_key
from app.thesaurus.static_index import (
    ensure_thesaurus_loaded,
    get_antonyms,
    get_synonyms,
)


BATCH_SIZE = 2000
PRINT_EVERY = 200


def get_or_create_char_to_id(db: Session) -> Dict[str, int]:
    """建立 char -> id 的對照表（假設 char 在本專案中作為主要識別，同一 char 可能有多個 code，但關係以 char 為主）。"""
    rows = db.query(Word.id, Word.char).all()
    char_to_ids: Dict[str, List[int]] = {}
    for wid, ch in rows:
        char_to_ids.setdefault(ch, []).append(wid)
    # 為了簡單，我們取每個 char 的第一個 id（或之後可擴充成多對多）
    # 在本專案中，同一 char 不同 code 的情況存在，但 syn/ant 通常以字面為主。
    return {ch: ids[0] for ch, ids in char_to_ids.items()}


def load_all_chars(db: Session) -> List[str]:
    """取得目前資料庫中所有不重複的字（用於 embedding 輔助時建立矩陣）。"""
    rows = db.query(Word.char).distinct().all()
    return [r[0] for r in rows if r[0]]


def insert_relations_batch(db: Session, relations: List[dict]):
    """批次 insert，canonical 排序 + (word_id, related_id, relation_type) 去重。"""
    if not relations:
        return 0

    deduped = {}
    for rel in relations:
        canon = canonical_relation_dict(rel)
        key = relation_storage_key(canon["word_id"], canon["related_id"], canon["relation_type"])
        deduped[key] = canon

    keys = list(deduped.keys())
    existing = set()
    if keys:
        existing = set(
            db.query(WordRelation.word_id, WordRelation.related_id, WordRelation.relation_type)
            .filter(tuple_(WordRelation.word_id, WordRelation.related_id, WordRelation.relation_type).in_(keys))
            .all()
        )

    to_insert = [
        WordRelation(
            word_id=rel["word_id"],
            related_id=rel["related_id"],
            relation_type=rel["relation_type"],
            score=rel.get("score"),
            source=rel.get("source"),
        )
        for key, rel in deduped.items()
        if key not in existing
    ]
    db.add_all(to_insert)
    return len(to_insert)


def generate_from_static(db: Session, char_to_id: Dict[str, int], limit: Optional[int] = None) -> int:
    """
    使用 static thesaurus（cilin / guotong / antisem）產生高品質 syn / ant 關係。
    這是主要、推薦的來源。
    """
    print("📚 正在從 static thesaurus 產生關係（cilin / guotong / antisem）...")

    chars = list(char_to_id.keys())
    if limit:
        chars = chars[:limit]

    total_inserted = 0
    processed = 0
    pending: List[dict] = []

    for ch in chars:
        processed += 1
        if ch not in char_to_id:
            continue
        wid = char_to_id[ch]

        # Synonyms
        try:
            syns = get_synonyms(ch)
        except Exception:
            syns = []

        for s in syns:
            if s == ch or s not in char_to_id:
                continue
            rid = char_to_id[s]
            w, r = (wid, rid) if wid <= rid else (rid, wid)
            rel = {
                "word_id": w,
                "related_id": r,
                "relation_type": "syn",
                "score": None,
                "source": "static_thesaurus",
            }
            pending.append(rel)

        # Antonyms
        try:
            ants = get_antonyms(ch)
        except Exception:
            ants = []

        for a in ants:
            if a == ch or a not in char_to_id:
                continue
            rid = char_to_id[a]
            w, r = (wid, rid) if wid <= rid else (rid, wid)
            rel = {
                "word_id": w,
                "related_id": r,
                "relation_type": "ant",
                "score": None,
                "source": "static_thesaurus",
            }
            pending.append(rel)

        if processed % PRINT_EVERY == 0:
            total_inserted += insert_relations_batch(db, pending)
            pending = []
            db.commit()
            print(f"  static 處理進度：{processed}/{len(chars)}，目前累計插入 {total_inserted} 筆關係...")

    total_inserted += insert_relations_batch(db, pending)
    db.commit()
    print(f"✅ Static thesaurus 完成，累計插入 {total_inserted} 筆關係。")
    return total_inserted


def generate_from_embedding(db: Session, char_to_id: Dict[str, int], limit: Optional[int] = None) -> int:
    """
    （可選）使用 sentence-transformers 計算 embedding，找出語意相近的詞，
    加入為 'semantic_related'（不會污染 'syn'/'ant'）。
    只有在 dev 環境安裝了 sentence-transformers 時才會執行。

    IMPORTANT: This is the *only* supported entry point that is allowed to
    load the MiniLM model. Calling this function will internally enable the
    ingest-only flag so that get_text_embedding() is permitted to load it.
    """
    print("🧠 嘗試使用 embedding 進行語意相關發現（semantic_related）...")

    # Explicitly unlock model loading for this run only.
    # This must be done before any import or call that could trigger the loader.
    try:
        from app.utils.embedding import enable_embedding_model_for_ingest
        enable_embedding_model_for_ingest()
    except Exception:
        pass

    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        print("  ⚠️  sentence-transformers 或 numpy 未安裝，跳過 embedding 輔助發現。")
        print("     如需此功能，請執行：pip install -r requirements-dev.txt")
        return 0

    chars = list(char_to_id.keys())
    if limit:
        chars = chars[:limit]

    print("  正在載入 embedding 模型（第一次會下載，較慢）...")
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    # 為所有候選字計算 embedding（或只算本次 batch）
    print("  正在為候選字計算 embeddings ...")
    embeddings = {}
    for i, ch in enumerate(chars):
        try:
            emb = model.encode(ch, normalize_embeddings=True)
            embeddings[ch] = emb
        except Exception as e:  # P1 fix
            print(f"    計算「{ch}」embedding 失敗: {type(e).__name__}: {e}")
        if (i + 1) % 500 == 0:
            print(f"    已計算 {i+1}/{len(chars)} 個字的 embedding...")

    if not embeddings:
        return 0

    # 建立矩陣方便計算
    char_list = list(embeddings.keys())
    mat = np.stack([embeddings[c] for c in char_list])

    total_added = 0
    processed = 0

    for ch in char_list:
        processed += 1
        if ch not in char_to_id:
            continue
        wid = char_to_id[ch]
        qv = embeddings[ch]

        # cosine 相似度
        sims = mat @ qv
        # 取 top 結果，排除自己與已經是 syn/ant 的（這裡簡化：只加 semantic_related）
        order = np.argsort(sims)[::-1]

        added_for_this = 0
        for idx in order:
            if added_for_this >= 5:   # 每字最多加 5 個 semantic_related（可調）
                break
            c2 = char_list[idx]
            if c2 == ch or c2 not in char_to_id:
                continue
            s = float(sims[idx])
            if s < 0.65:               # 保守 threshold（只加明顯相關的）
                continue

            rid = char_to_id[c2]
            w, r = (wid, rid) if wid <= rid else (rid, wid)
            rel = {
                "word_id": w,
                "related_id": r,
                "relation_type": "semantic_related",
                "score": round(s, 4),
                "source": "embedding_cosine",
            }
            total_added += insert_relations_batch(db, [rel])
            added_for_this += 1

        if processed % PRINT_EVERY == 0:
            db.commit()
            print(f"  embedding 處理進度：{processed}/{len(char_list)}，目前累計新增 semantic_related {total_added} 筆...")

    db.commit()
    print(f"✅ Embedding 輔助發現完成，累計新增 {total_added} 筆 semantic_related 關係。")
    return total_added


def main(limit: Optional[int] = None, include_embedding: bool = False):
    print("🚀 啟動 generate_relationships.py（ingest 階段關係產生器）")
    print(f"資料庫類型: {'PostgreSQL' if IS_POSTGRES else 'SQLite'}")
    print(f"ENV: {os.getenv('ENV', 'local')}")
    print()

    # 自動載入 static thesaurus（輕量，無副作用）
    try:
        ensure_thesaurus_loaded(force=True)
    except Exception as e:  # P1 fix: include exception type
        print(f"⚠️  載入 static thesaurus 時發生問題（將繼續以可用資料為主）：{type(e).__name__}: {e}")

    db = SessionLocal()
    try:
        char_to_id = get_or_create_char_to_id(db)
        print(f"資料庫中共有 {len(char_to_id)} 個不同字元。")

        # 1. Static thesaurus（主要、高品質來源）
        inserted_static = generate_from_static(db, char_to_id, limit=limit)

        # 2. （可選）Embedding 輔助。必須明確指定 --include-embedding。
        inserted_emb = generate_from_embedding(db, char_to_id, limit=limit) if include_embedding else 0

        print("\n" + "=" * 60)
        print("🎉 關係生成完成！")
        print(f"Static 來源貢獻：{inserted_static} 筆")
        print(f"Embedding 輔助貢獻：{inserted_emb} 筆")
        print("=" * 60)

        # 簡單統計
        syn_count = db.query(WordRelation).filter(WordRelation.relation_type == "syn").count()
        ant_count = db.query(WordRelation).filter(WordRelation.relation_type == "ant").count()
        sem_count = db.query(WordRelation).filter(WordRelation.relation_type == "semantic_related").count()
        print(f"\n目前資料庫關係統計：")
        print(f"  syn                : {syn_count}")
        print(f"  ant                : {ant_count}")
        print(f"  semantic_related   : {sem_count}")
        print(f"  總計               : {syn_count + ant_count + sem_count}")

    finally:
        db.close()

    print("\n提示：")
    print("  - 之後可重新執行本 script 來更新/補充關係（會自動去重）。")
    print("  - 一般使用者只要 `pip install -r requirements.txt` 就能使用這些關係，無需 ML 套件。")
    print("  - 如需 v2 可插拔 ingest，請改用 `python -m ingest normalize` + `build-relations`。")
    print("  - 如需只處理部分資料測試：python scripts/legacy/generate_relationships.py --limit 200")


if __name__ == "__main__":
    # 簡單支援 --limit / --include-embedding
    limit = None
    include_embedding = False
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg.startswith("--limit="):
                try:
                    limit = int(arg.split("=", 1)[1])
                except:
                    pass
            elif arg == "--limit" and len(sys.argv) > sys.argv.index(arg) + 1:
                try:
                    limit = int(sys.argv[sys.argv.index(arg) + 1])
                except:
                    pass
            elif arg == "--include-embedding":
                include_embedding = True

    main(limit=limit, include_embedding=include_embedding)
