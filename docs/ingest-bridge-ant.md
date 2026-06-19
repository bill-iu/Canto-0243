# 近義橋反義維護

領域詞彙：[CONTEXT.md](../CONTEXT.md) § **近義橋反義**、**近義橋重跑**、**發佈主理**、**發佈詞庫快照**。

**執行者**：**發佈主理**（納入 **詞庫發佈**；貢獻者 PR 唔包含此步）。**發佈補件**唔參與。

## 何時全量重跑

- 近義橋品質閘門（橋接語意門檻、借入上限、多橋合併）變更後
- 其他 ingest 已更新近義／反義池，需以新池重算 `ant_syn_bridge`

## 全量重跑

前置：`build-relations` 等上游 ingest 已完成；`lyrics.db` 在 repo 根目錄。

```bash
python -m ingest expand-antonyms-syn-bridge --fresh
```

| 預設 | 說明 |
|------|------|
| `--fresh` | 清 checkpoint，由 offset 0 開始 |
| `--replace-relations` | 先刪 `source=ant_syn_bridge` 列再寫入 |
| `--chunk-size 200` | 分批 insert；每批後刷新 ant 快照 |
| `--min-bridge-cosine 0.80` | 橋接語意門檻 |
| `--max-bridged-ants-per-head 30` | 橋接借入上限 |

**唔好**手動刪 `data/locks/*.lock` 恢復進度；中斷後重新執行同一命令（無 `--fresh`）會自動 resume checkpoint。要從頭再跑才加 `--fresh`。

可選覆寫（對照 outlier 時）：

```bash
python -m ingest expand-antonyms-syn-bridge --fresh \
  --min-bridge-cosine 0.85 --max-bridged-ants-per-head 20
```

## 驗收（發佈主理）

### 1. 列數與 checkpoint

跑畢後終端 `expand-antonyms-syn-bridge stats` 的 `inserted` 應與 checkpoint 累計一致：

```bash
python -m ingest report
```

輸出含 `ant_syn_bridge ant rows: N`。對照 `data/locks/expand-antonyms-syn-bridge.checkpoint.json` 的 `inserted_cumulative`（`offset` 應等於 `total_targets`）。

### 2. 抽樣語意（5 字）

從 DB 取 5 個僅經橋接補反義的字面（示例查詢）：

```bash
python -c "from app.database import SessionLocal; from app.models.word import Word, WordRelation; \
from sqlalchemy import and_; \
db=SessionLocal(); \
rows=db.query(Word.char).join(WordRelation, WordRelation.word_id==Word.id).filter(\
WordRelation.source=='ant_syn_bridge', WordRelation.relation_type=='ant').distinct().limit(5).all(); \
print([r[0] for r in rows]); db.close()"
```

在查韻介面對每字執行 `字面!`，確認反義含 `ant_syn_bridge` 來源且語意合理（無明顯 hub 噪音 outlier）。

### 3. 詞庫發佈

驗收通過後，依 [release.md](release.md) § 步驟 3 上傳 **發佈詞庫快照**（`lyrics.db`、`words-lexicon.json`）。
