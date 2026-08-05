# 語意鄰居真緊湊（P2 / E1c）

> 狀態：**E1c 已實作**（CSR bin + strip edges + 雙端 pool）  
> 日期：2026-08-05  
> 相關：bake 計劃、ADR-0047、CONTEXT § **真緊湊**／**語意鄰居緊湊載體**

## 已拍板

| # | 決策 |
|---|---|
| 主路徑 | **P2 真緊湊** |
| 落點 | **E1c**：`client/public/embedding-nbr.bin`（關係包資產）+ meta 指紋 |
| 主 `lyrics.db` | **唔**長期存 `embedding_cosine` edge 行 |
| 格式 | 雙向 CSR `e1.v1`（`ENBR` magic） |
| Runtime | PWA：`ensureStaticRelationIndexes` fetch bin；Desktop：loader 讀 public／cache |

## 真緊湊定義（摘要）

權威載體位元組（表+索引或等價 blob）比冗餘 edge 表 **少一個數量級**；只 gzip 唔算。

## 實測（strip 後 VACUUM）

| 指標 | edge 表形 | E1c 後 |
|---|---|---|
| `lyrics.db` | ~221 MB | **~40.1 MB** |
| db gzip-6 | ~55 MB | **~14.6 MB** |
| embedding edges in db | 1,129,483 | **0** |
| `embedding-nbr.bin` | — | **14.87 MB**（雙向 CSR） |
| heads / dir-edges | — | 165,034 / 2,258,966 |

## 重用閘（char_id_fingerprint）

meta 欄位 `char_id_fingerprint` = sha256(sorted `char\\tprimary_id` lines)。

| 狀態 | 含義 |
|---|---|
| **match** | 可直接套同一 bin（唔使重算） |
| **mismatch** | words id 變咗 — **禁止**盲 copy；重 bake |
| **missing_fp** | 舊 meta — `stamp-embedding-nbr-fp` 或重 bake |

```bash
python -m ingest stamp-embedding-nbr-fp   # 替現有 meta 補指紋（bin 唔變）
python -m ingest check-embedding-nbr-fp   # 查可唔可以重用
# build-db seal 會自動 check；有 bin 但 mismatch/missing_fp → fail
```

## 命令

```bash
# 從已有 embedding_cosine 邊導出 bin 並 strip（已跑過）
env -u PYTHONPATH python -m ingest export-embedding-nbr

# 全量 bake：預設寫 bin、唔寫 edge、strip（含 fingerprint）
env -u PYTHONPATH PYTHONUNBUFFERED=1 .venv-embed-bake/Scripts/python.exe -m ingest bake-embedding-topk --skip-encode
```

## 程式

| 檔 | 角色 |
|---|---|
| `app/domain/lexicon/embedding_nbr_codec.py` | encode/decode CSR |
| `app/domain/relation_pool/embedding_nbr.py` | Desktop loader + pool items |
| `client/src/db/embedding-nbr.ts` | PWA decode |
| `client/src/db/init.ts` | fetch bin with static indexes |
| `client/src/db/relation-pool/builder.ts` | merge nbr into pool |
| `ingest/bake_embedding_topk.py` | bake + export_nbr_from_existing_edges |
| `tests/test_embedding_nbr_codec.py` | roundtrip |

## 交付注意

- `embedding-nbr.bin` / `.meta.json` 隨 public 渠道發佈（可後載；現同 static 索引一齊 fetch）
- 大 bin 唔必 commit git（若超 repo 限）；發佈流水線 copy 即可
- 舊 PWA 無 bin → semantic 空，syn/ant 仍靠 cilin／靜態
