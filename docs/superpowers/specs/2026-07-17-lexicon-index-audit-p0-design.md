# 詞庫索引量測閘（P0）設計

**日期**：2026-07-17  
**狀態**：已實作（閘 + `idx_length_finals`）  
**動機**：把「索引是否夠／可否再加」變成可重複量測閘；唔預設物化 reverse／frequency。

## 1. 問題與邊界

現行：

- 熱 SQL 已用 `idx_length_code_finals (length, code, finals)`；`length+code`／`length+code+finals` 的 EXPLAIN 已走該索引。
- 排序在 app 層（essay／ranking），**words 表無 frequency 欄**。
- Portable／PWA 正式候選多數走 word_cache／音素倒排；裸 SQL 多屬**降級路徑**。
- ADR-0047／I2 已刻意刪重複與未用單欄索引（`ingest/lexicon_indexes.py` allowlist）。

量測樣本（本機 `lyrics.db`，僅作設計依據，唔當 CI 絕對數字）：

| 查詢形 | EXPLAIN 摘要（閘前） | 備註 |
|--------|----------------------|------|
| `length+code` | SEARCH `idx_length_code_finals` | 健康 |
| `length+code+finals` | SEARCH 全複合鍵 | 健康 |
| `char=` | SEARCH `ix_words_char` | 健康 |
| relation `(word_id, type)` | covering autoindex／複合 | 健康 |
| `length+finals`（無 code） | 只 SEEK `length=?` 再濾 | equals 降級 |
| `code` only／`jyutping=` | SCAN | 非主路徑；jyutping 索引屬 ADR 禁區 |

**本 P0 要解決**：可重複索引健康閘；有條件加最少 covering／複合索引。

**不做**：

- `code_reverse`／`finals_reverse` 物化欄
- `frequency`／rank 入 `words`
- 多檔聲調物化、改 MatchSpec 語意
- 為 `jyutping` 新建 WHERE 索引（ADR-0027／0047 已否決）

## 2. 考慮方案

| 方案 | 內容 | 結論 |
|------|------|------|
| A1 | 只加 EXPLAIN＋計時閘，零新索引 | 可作最小交付，但無效能收益 |
| **A2（採用）** | 閘 + **有條件最多加 1 條**已證明有用嘅複合索引 | 量測為主、脹庫有上限 |
| A3 | 閘 + reverse 物化 | 否決（超出本週期） |

## 3. 架構

### 3.1 黃金 SQL 集（固定形狀）

**必須走指定索引（回歸紅）**

1. `WHERE length=? AND code=?` → 含 `idx_length_code_finals`
2. `WHERE length=? AND code=? AND finals=?` → 同上
3. `WHERE length=? AND finals=?` → 含 `idx_length_finals`（本週期已加）
4. `WHERE char=?` → 含 `ix_words_char`
5. `WHERE word_id=? AND relation_type=?` → SEARCH（autoindex 或 `idx_word_rel_*`），唔 SCAN 全表

**基線記錄（唔強制新索引）**

6. `WHERE code=?`（無 length）— 預期弱；唔為佢加單欄 `ix_words_code`（仍在 FORBIDDEN）

### 3.2 加索引規則（硬閘）

只允許加入新索引若**全部**成立：

1. 某**生產降級路徑**（例如 `f4_equals` cache miss：`length` + `finals=`）EXPLAIN 未能 SEEK 到 `finals`。
2. 粗計時有可重複改善（本週期：同機約 50×）。
3. 加完後 **user indexes 總體積** ≤ **I2 45MB**。
4. 本 P0 **最多一條**新索引：

   ```sql
   CREATE INDEX idx_length_finals ON words(length, finals);
   ```

5. 更新 `REQUIRED_LEXICON_INDEXES`／`REQUIRED_LEXICON_INDEX_SQL`、`app/models/word.py`、`tests/smoke/test_lexicon_indexes.py`；`finalize_lexicon_indexes` **CREATE IF NOT EXISTS** 缺嘅 required。

### 3.3 交付物

| 交付 | 說明 |
|------|------|
| Smoke | `tests/smoke/test_lexicon_indexes.py` EXPLAIN 黃金集 |
| Self-check | `scripts/lexicon_index_audit_self_check.py` |
| 政策 | `ingest/lexicon_indexes.py` allowlist + ensure |
| 索引 | `idx_length_finals`（量測通過後加入） |

### 3.4 錯誤與降級

- 閘紅 → smoke 失敗；唔自動亂加索引。
- 體積超 cap → 禁止再加。
- PWA／Portable 共用 schema；新索引經 build-db finalize／copy-db 入渠道包。

## 4. 測試

- `tests/smoke/test_lexicon_indexes.py`：allowlist、ensure、fixture EXPLAIN、可選 repo `lyrics.db` 副本 EXPLAIN。
- `scripts/lexicon_index_audit_self_check.py`：`length+finals` 必須見 `idx_length_finals`。

## 5. 驗收（本週期結果）

1. 黃金集 EXPLAIN 斷言綠。
2. **閘 + `idx_length_finals`**（非只閘）。
3. 本機 finalize 後 `lyrics.db` ≈39MB；user indexes 仍遠低於 45MB。
4. MatchSpec／查詢語意零變更。

## 6. 後續（非本 P0）

- 用戶疊加（pinned／display prefs）與詞庫 SSOT 分離  
- 雙欄 viewport 等 UX  
- 若尾錨真係 SQL 熱點再評估 reverse 欄
