# 0243 離線押韻字典 - 專案總覽

**版本日期**：2026-06-11  
**開發者**：Wizgo  
**目標**：提供一個可離線使用的粵語押韻搜尋工具，支援 0243 / 02493 編碼、粵拼、等號韻與相關詞查詢。

---

## 1. 專案簡介

這個專案是一個以 FastAPI 為後端、SQLite 為資料庫、純 HTML + JavaScript 為前端的離線式粵語字詞查詢工具。它的核心用途是協助使用者在填詞與創作時，快速找出同韻、同碼或相近發音的詞語。

### 目前已完成的重點功能

- [x] 支援 0243 與 02493 兩種模式（m1 / m2）
- [x] 支援漢字、數字編碼、粵拼與混合查詢
- [x] 支援等號韻查詢，例如 `香港=`
- [x] 支援位置指定的聲母 / 韻母比對
- [x] 對罕見字、混合字串與特殊查詢提供精確匹配處理
- [x] 點擊查詢結果後會直接回到同一套搜尋結果流程
- [x] 顯示同碼 / 同韻相關結果，並改善排序與可讀性
- [x] 將目前查詢狀態同步到瀏覽器 URL，支援返回／前進與分享
- [x] 提供回歸測試，提升搜尋行為穩定性
- [x] 新增獨立「近義/反義詞查找」模式（mode=syn）：前端按鈕 + 近義 / 反義 / 語意相關 UI；後端使用預先計算的 `word_relations` + static thesaurus fallback；embedding 僅限 ingest 階段，不會在 runtime 載入 ML 模型。

---

## 2. 專案結構

```text
0243_lyrics_tool/
├── app/
│   ├── database.py
│   ├── models/
│   │   └── word.py
│   ├── routers/
│   │   └── word.py
│   └── schemas/
│       └── word_schema.py
├── frontend/
│   └── index.html
├── data/
│   ├── antonym/
│   ├── cilin/
│   │   └── new_cilin.txt   # 繁體詞林（fetch_cilin_data.py 產生）
│   └── thesaurus/
├── fetch_cilin_data.py
├── alembic/
│   └── versions/
├── import_data.py
├── generate_relationships.py
├── ingest_syn_ant.py
├── ingest/
│   ├── syn_ant_manifest.py
│   ├── syn_ant_sources.py
│   ├── syn_ant_normalize.py
│   └── syn_ant_merge.py
├── data/syn_ant/
│   ├── sources.yaml
│   ├── fixtures/
│   └── raw/          # optional local-only raw files (.gitignore)
├── init_db.py
├── main.py
├── reset_db.py
├── start.sh
├── utils.py
├── requirements.txt
└── README.md
```

---

## 3. 快速開始

### 啟動服務

```bash
./start.sh
```

若要直接查看前端頁面，可開啟：

```text
frontend/index.html
```

後端 API 可透過以下網址使用：

```text
http://127.0.0.1:8000/docs
```

### 主要搜尋範例

```text
GET /words/search/?q=23就&mode=m2
GET /words/search/?q=2=我3&mode=m1
GET /words/search/?q=23=你4&mode=m1
GET /words/search/?q=23你=4&mode=m1
GET /words/search/?q=23=我&mode=m1
GET /words/search/?q=香港=
```

---

## 4. 開發與資料庫操作

### 初始化資料庫

```bash
python init_db.py
```

### 重置資料庫

```bash
python reset_db.py
```

### 執行回歸測試

```bash
python -m unittest -v tests.test_word_detail
python -m unittest -v tests.test_utils
python -m unittest -v tests.test_syn_ant_ingest
```

---

### 資料準備與關係生成（Ingest / Dev-only）

本專案已依照「使用者不該需要安裝整個 ML 套件」的原則進行調整：

- **一般使用者 / 部署**：
  ```bash
  pip install -r requirements.txt
  python main.py
  ```
  只會安裝輕量 runtime 依賴，**不需要** `sentence-transformers` / torch。

- **資料準備 / 關係生成（maintainer 使用）**：
  ```bash
  pip install -r requirements-dev.txt
  python generate_relationships.py          # 產生同義/反義/語意關係（存入 word_relations 表）
  # 或（推薦 v2 可插拔 ingest）
  python ingest_syn_ant.py report
  python ingest_syn_ant.py normalize --source current_static
  python ingest_syn_ant.py build-relations
  # 或
  python import_data.py
  python backfill_embeddings.py             # （選用，僅當還需要 embedding 欄位時）
  ```

`generate_relationships.py` 會優先使用 high-precision static thesaurus（cilin / antisem / guotong），並可用 `--include-embedding` 明確啟用 embedding 輔助發現 `semantic_related`。產生的關係之後在 syn 模式（近義/反義查找）中會透過純 SQL 查詢。

### 同義詞詞林（Cilin）資料準備

`data/cilin/new_cilin.txt` 由 [liao961120/cilin](https://github.com/liao961120/cilin) 套件 API 匯出，使用 `Cilin(trad=True)` 確保繁體中文：

```bash
pip install -r requirements-dev.txt   # 含 cilin、opencc-python-reimplemented
python fetch_cilin_data.py            # 寫入 data/cilin/new_cilin.txt（約 23k 行）
python ingest_syn_ant.py normalize --source current_static
python ingest_syn_ant.py build-relations
```

`build-relations` 對 SQLite 使用 `INSERT OR IGNORE ... SELECT JOIN` 批次寫入，避免大量 staging 資料觸發 variable limit。

### 近義/反義 Ingest v2（`ingest_syn_ant.py`）

授權分級 + 可插拔 parser + staging（`syn_ant_edges`）→ merge 到 `word_relations`：

```bash
pip install -r requirements-dev.txt   # 需要 pyyaml（manifest）
python ingest_syn_ant.py report
python ingest_syn_ant.py normalize --source current_static
python ingest_syn_ant.py build-relations
```

可選第三方 raw 檔請放在 `data/syn_ant/raw/`（**勿 commit 授權不明詞庫**）。manifest 定義於 `data/syn_ant/sources.yaml`：

| Source ID | 授權 | 預設啟用 | 說明 |
|-----------|------|----------|------|
| `current_static` | bundled | 是 | 專案內 cilin / antisem / guotong |
| `cow` | CC-BY | 否 | Chinese Open Wordnet（本地放置） |
| `relation_pairs` | research | 否 | TSV pairs fixture |
| `hit_cilin` / `antisem_extended` | unclear | 否 | 僅 maintainer 本地匯入 |

詳細說明請參考 `generate_relationships.py` 檔案開頭的 docstring 與 `WORKLOG.md` 最新條目。

如果使用 PostgreSQL 正式環境，請執行 Alembic migration 建立搜尋索引與 `word_relations` 表：

```bash
alembic upgrade head
```

### 資料來源總覽

以下整理**目前已 ingest 或 bundled** 的資料，以及**尚未進庫**時可參考的外部詞典。詞庫與注入政策（P0–P4 路線圖）見 `CONTEXT.md` § 詞庫與注入；**P1** 起將以 `LexiconPort` / `Static0243Lexicon` 統一收錄門檻。

#### `words` 表（詞條 · 粵拼 · 0243 碼）

| 階段 | 本機路徑 | 上游／說明 | Ingest 指令 |
|------|----------|------------|-------------|
| 0243 編碼詞表 | `data/raw/0243_dict_1to5digits.json` | 專案內 bundled 0243 鍵盤編碼詞表（1–5 碼） | — |
| 補粵拼 | `data/raw/merged_0243_with_jyutping.json` | 由 `add_jyutping_to_0243.py` 以 **pycantonese** / **pyjyutping** 對上表逐條補音 | `python add_jyutping_to_0243.py` |
| 清洗後匯入 | `data/raw/clean/*.json` | 上述 pipeline 產物（每檔為 `{char, jyutping, code}` 陣列） | `python import_data.py` |

> **注意**：`words` 表內容取決於 maintainer 是否已執行上述腳本；repo 內未必包含完整 raw JSON（可能僅有本地 `lyrics.db`）。

#### `word_relations` 表（近義 · 反義 · 語意相關）

預設經 `ingest_syn_ant.py`（`current_static`）或 `generate_relationships.py` 寫入；manifest 見 `data/syn_ant/sources.yaml`。

| Source ID | 本機路徑 | 上游／說明 | 預設啟用 |
|-----------|----------|------------|----------|
| `cilin` | `data/cilin/new_cilin.txt` | [liao961120/cilin](https://github.com/liao961120/cilin)（`fetch_cilin_data.py`，繁體） | ✅（`current_static`） |
| `guotong` | `data/thesaurus/dict_synonym.txt`<br>`data/thesaurus/dict_antonym.txt` | [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary)（簡體 raw → `convert_guodict.py` OpenCC 轉繁） | ✅ |
| `antisem` | `data/antonym/antisem.txt` | 專案 bundled 反義詞表（ingest 標記 `source=antisem`） | ✅ |
| `compound_antonyms` | `data/syn_ant/compound_antonyms.txt` | 專案 curated 雙字反義複合詞（`ingest_syn_ant.py build-relations`） | ✅ |
| `cow` | `data/syn_ant/raw/cow/cow.txt` | Chinese Open Wordnet（CC-BY；需自行放置 raw） | ❌ |
| `relation_pairs` | `data/syn_ant/raw/pairs/relations.tsv` | 研究用 TSV pairs | ❌ |
| `hit_cilin` | `data/syn_ant/raw/hit_cilin/new_cilin.txt` | HIT Cilin Extended（授權不明；僅本地） | ❌ |
| `antisem_extended` | `data/syn_ant/raw/antisem/antisem.txt` | 擴充 antisem（授權不明；僅本地） | ❌ |
| `embedding_cosine` | — | `generate_relationships.py --include-embedding`（dev-only MiniLM） | 選用 |

上述 cilin / guotong / antisem 檔案在 **runtime** 亦會由 static thesaurus 載入，作 `word_relations` 的即時 fallback（見 `app/thesaurus/static_index.py`）。

#### Runtime 補字（尚未視為正式詞庫 ingest）

| 機制 | 說明 |
|------|------|
| `_ensure` + pycantonese | 查詢字面不在 DB 時：**單字**仍用 pycantonese 過渡猜讀；**多字（len≥2）** 僅 `Static0243Lexicon`（`data/raw/clean`）命中才可注入（P1）。 |

#### 計畫中（尚未 ingest，P2+）

| 來源 | 連結 | 用途 |
|------|------|------|
| rime-cantonese-upstream | [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) | 單字 `char.csv`、詞級 `word.csv` 等（CC BY 4.0） |
| essay-cantonese | [rime/rime-cantonese essay-cantonese.txt](https://raw.githubusercontent.com/rime/rime-cantonese/refs/heads/main/essay-cantonese.txt) | 語料頻次，僅排序（P3） |

#### 資料庫找不到時可參考（尚未 ingest）

以下外部粵語詞典**尚未**納入本專案 ingest pipeline；若 `words` 表查無該詞，可人工查閱或作日後 Lexicon 候選：

| 名稱 | 連結 |
|------|------|
| words.hk 粵典詞表 | https://words.hk/faiman/analysis/wordslist/ |
| cantonese.org CC-Canto | https://cantonese.org/download.html |
| kaifangcidian.com 粵語詞典 | https://kaifangcidian.com/xiazai/ |

---

## 5. 環境設定

1. 安裝依賴：
   ```bash
   pip install -r requirements.txt
   ```
2. 如需使用自訂資料庫位址，可建立 `.env` 並設定 `DATABASE_URL`。
3. 依賴安裝完成後即可啟動服務。`pycantonese` / `pyjyutping` 用於資料庫沒有該字詞時的過渡期粵拼注入（正式詞庫來源見上文 **§ 資料來源總覽**）；既有資料查詢不會依賴 ML 套件。

---

## 6. 目前狀態

目前專案已具備可用的搜尋流程與前端互動體驗，包含統一結果頁、相關詞排序、URL 狀態同步與精確字查詢修復。後續可繼續擴充為更完整的押韻詞庫與使用者體驗工具。

## 7. Performance Rule (Non-negotiable) — 瞬間搜尋速度基本規則

**瞬間搜尋速度是本專案的不可協商基本規則之一**（non-negotiable）。所有搜尋（含 m1/m2 純漢字、混合「門0」「好23」、wildcard、syn 近義/反義等）在 preload 完成後**必須感覺 instant**（目標端到端 <0.2s，常見 case 否則 <0.5s）。

### 命名慣例（Naming Conventions）— 硬性規定

**禁止在任何函數、變數、識別項或新程式碼中使用 "hanzi"。**  
這是粵語專案（Cantonese lyrics tool），"hanzi" 為國語用語。日後新增與中文字符（漢字）相關的邏輯時，**必須**使用以下名稱之一：
- **"canto"**（推薦用於與粵語發音/字符相關的脈絡）
- **"chars"**（推薦用於字面字符資料、遮罩位置、literal positions 等；專案內已部分採用）

違反本規定不得合併。所有新貢獻（含註解與文件）都必須遵守。

### 必須涵蓋的關鍵測試案例（每次變更都需驗證）
- 純漢字：「事業」（m1/m2 模式下**嚴格只輸出 query 自己擁有的 0243 codes**，正確 tier 排序，無無關 code 污染如 "0尊"）。
- 混合 literal+digit：「門0」「好23」（literal 優先，預期詞如「門前」「門童」「門鈴」「門庭」等出現在頂部；正確性 + 速度同等重要）。
- Wildcard：「_識_」「好_」。
- Syn 模式：「快樂」（兩欄近義/反義，無分數，preload 後 instant，可點擊連鎖）。
- 其他常見：純數字、= 韻、粵拼片段、load more 邊界。

### Enforcement 流程（每次修改 / 新增功能都必須遵守）
任何 code/frontend/資料/模式變更（含未來擴充），開發者**必須**在提交前執行以下步驟並記錄：
1. 對上述關鍵 case 進行 before/after 計時（瀏覽器 DevTools Network 面板、console.time 包 fetch、或 `python -c 'import time, requests; ...'`）。
2. 比對結果集與排序（dump 前 20-30 筆，確保內容、jyut header 順序、strict per-code 行為、literal priority、syn two-col 完全一致；不得因加速而改變結果）。
3. 執行 `python -m pytest tests/` 確認全綠。
4. 更新 WORKLOG.md：記錄變更摘要、關鍵 case timing 數據、結果無退化證明。
5. 若新功能「必然」會影響速度（極少見），必須先在 plan 討論、調整目標、同步更新本節說明。

違反本規則的變更不得合併。**「在不影響搜尋結果的情況下保持最快速度」是每次迭代的硬性 gate**。

歷史優化基礎（length 索引、strict codes、preload matrix、no DB regex、mem cache、caps + selective query、warmup 等）必須被保留或強化；新 cache 層（server in-mem word meta + server result + frontend JS）是達成「永遠 instant」的核心手段。

（本規則直接回應 2026 年需求：「將瞬間搜尋速度寫入README.md作為基本規則之一，每次修改/新增功能都必須確保在不影響搜尋結果的情況下保持最快速度」。）
