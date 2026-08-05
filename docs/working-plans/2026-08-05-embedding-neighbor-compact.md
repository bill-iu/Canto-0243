# 語意鄰居真緊湊（P2）— 研究＋設計草案

> 狀態：grill 中（P2 主路徑已選；schema／讀路徑未實作）  
> 日期：2026-08-05  
> 相關：`2026-08-05-embedding-topk-semantic-bake.md`、ADR-0047（音素 j2＋關係體積）、CONTEXT § **真緊湊（存儲）**／**語意鄰居緊湊載體**

## 何謂「真緊湊」

### 定義（一句）

**權威載體上可觀測位元組（表＋必備索引，或等價單檔 blob）比冗餘正規形少一個數量級，語意與查詢契約不變。**

### 算／唔算

| 算真緊湊 | 唔算 |
|---|---|
| 改存法：百萬 edge row → CSR／per-head 列表編碼 | 只 `gzip` 全庫（221MB→55MB，仍 ≫ 舊渠道 15MB） |
| 去掉雙向 B-tree 對語意邊嘅必然性 | 只縮短 `source` 字串、score 仍每行 REAL＋全表 index |
| 開庫／渠道指紋拒絕舊膨脹形 | 查詢時 LIMIT 截斷當「細咗」 |
| 雙端（或單端 decode）語意等價 | runtime 載 bge 現場算 |

### 可驗證指標（建議閘）

對照 **bake 前** public 渠道（`lyrics.db.gz` ~15MB）與 **edge 表形**（relations 相關 `dbstat` ~200MB）：

| 指標 | edge 表形（而家） | P2 目標（草案） |
|---|---|---|
| `word_relations`+其 index（dbstat） | ~202 MB | embedding 部分 **≤15 MB** 未壓／**≤8 MB** zlib 級 |
| 全庫 plain | ~221 MB | **≤55 MB**（理想 **≤45 MB**，接近舊 40MB + 鄰居） |
| 全庫 gzip-6 | ~55 MB | **≤20 MB**（對齊舊 ~15MB 量級） |
| 語意 | 1.13M undirected 鄰＋score | 等價集合（允許 score u16 量化誤差） |
| 抽樣 | 「開心」鄰仍合理；cilin syn 排序仍優先 | 同左 |

**本機實測編碼原型（2026-08-05，未入庫）：**

| 格式 | 大小 |
|---|---|
| CSR 無向（min-id 側 half-edge 1.13M）raw | **7.94 MB** |
| 同上 zlib/gzip-6 | **4.35 MB** |
| CSR 雙向（查 head 直接）raw | **14.87 MB** |
| 同上 zlib | **8.52 MB** |

→ 相對 relations 相關 **~200MB**，**已達一個數量級** → 滿足「真緊湊」數字門檻。

---

## 音素 j2 對照（紀律可抄、單元不同）

| | 音素 j2 | 語意鄰居 e1（P2） |
|---|---|---|
| 編碼單位 | 一詞條內 phoneme token 列 | **一頭字面**嘅鄰居 id＋score 列 |
| 閉集 | 韻／聲母 vocab | word_id 開集（id 已係整數） |
| 版本鍵 | `phoneme_vocab_version=j2.v1` | `embedding_nbr_version=e1.v1` |
| 開庫 | 拒 JSON 舊形；PWA purge 重下 | 拒「只得 edge 表、無 e1 載體」或雙寫過渡 |
| 讀路徑 | decode → token 比對 | decode → `RelationPoolItem[]` semantic |

---

## P2 存法候選

### E1 — 單 blob 表（推 v1）

```text
lexicon_meta:
  embedding_nbr_version = e1.v1
  embedding_nbr_model   = bge-m3-fp32-onnx-v1

embedding_nbr_blob:   -- 單列或 key-value
  key = 'csr_u32'
  blob = ENBR header | head_ids[] | indptr[] | neighbor_ids[] | score_u16[]
```

- score_u16：線性映射 cosine ∈ [0.50, 1.0] → 0..65535（或存 milli 0..1000 於 u16）
- **雙向 CSR** 較易實作 pool（任意 seed O(log n)+slice）；體積 ~15MB raw / ~8.5MB z
- **無向 half + 查詢時補鏡** 更細但實作易漏

### E2 — 每 head 一列 TEXT／BLOB

```text
embedding_nbr(head_id PRIMARY KEY, payload BLOB or TEXT)
-- TEXT 示例: "id:milli,id:milli,..."  （似 phoneme 定界，但 id 開集）
```

- 優點：SQL 按 head 點查、唔使載全圖  
- 缺點：165k 行＋PK index；總體積通常 **大於** 單 CSR blob（每行開銷）

### E3 — 渠道靜態檔（非 SQLite）

- `embedding-nbr-index.bin` 隨 **詞庫關係包** 下載  
- 主 `lyrics.db` 回到 ~40MB  
- 要接就緒閘第二階段（已有 **詞庫關係包** 概念）

**v1 推薦：E1 雙向 CSR 入關係包（或核心旁路單表）＋ meta 指紋；E3 若關係包管線更順可等價。**

---

## 唔做（已否）

- 長期保留 1.13M 行 `word_relations` + 雙向 type index 當 A 權威  
- 只 gzip 當 N1 完成  
- cosine → ant  
- 為緊湊砍 S4 覆蓋（可另開「降 K」微調，唔當真緊湊）

---

## 遷移／雙寫

1. Bake 繼續可產 edge 表（開發方便）或直出 CSR。  
2. Release：`embedding_cosine` **edge 列清出交貨庫**；只留 e1 載體。  
3. Runtime pool：`fetchDbRelations` 後 **merge decode(e1)**；source 仍 `embedding_cosine` rank 60。  
4. 舊渠道無 e1 → 行為＝無 A 邊（靜態詞林 fallback），或 gate 要求升級包。

---

## 實作 checklist（未開工）

- [ ] 定 E1 vs E3（關係包內 blob vs 主 db 表）  
- [ ] `encode_nbr_csr` / `decode_nbr_for_seed` 雙端（py + ts）  
- [ ] bake 寫 e1 + meta；可選 `--no-edge-table`  
- [ ] pool builder 接 decode  
- [ ] 開庫／gate：meta 版本  
- [ ] 量度：dbstat + gzip vs 指標表  
- [ ] 抽樣「開心」+ 長尾字  
- [ ] ADR（若 E1 成 release 契約：難逆＋意外＋ trade-off → 值得）

---

## 下一步 grill

1. 載體落點：**主 db 單表 blob** vs **關係包獨立檔**  
2. 雙向 CSR vs 無向 + 鏡射  
3. 過渡期是否雙寫 edge（方便 debug）  
