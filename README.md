# Canto-0243

Canto-0243（離線粵語填詞查韻工具 · ONE·搵·韻）：依 **0243／02493 數字碼**、**粵拼**、**韻母／聲母規則** 與 **近義／反義關係**，幫創作者快速找可替換詞條。

**授權**：程式碼依 [Canto-0243 License](LICENSE)（CC BY-NC-SA 4.0 + 附加條款；**非 OSI 開源**）。第三方資料見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。  
**技術棧**：FastAPI · SQLAlchemy · SQLite（離線單機）· 純 HTML/JS 前端  
**語意與領域詞彙**：見 [`CONTEXT.md`](CONTEXT.md) · 貢獻指南 [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## 功能概覽

| 類別 | 能力 |
|------|------|
| 編碼模式 | **0243模式** `mode=m1`（0243 等價變體）· **02493模式** `mode=m2`（含 9 鍵聲調、分清二聲） |
| 查詢類型 | 純漢字 · 純數字（分頁 + 總數 header）· **粵拼查詢**（`syut`／`nei hou`／`ming4 baak6`）· 混合碼字（`23就`）· wildcard（`門0`、`_識_`）· 等號韻（`香港=`、`2=我3`）· 韻／聲錨（`?就=`） |
| 近反義 | **近反義模式** `mode=syn` 全欄 UI（不收粵拼）；或 0243／02493 模式下 `~詞` / `!詞` / `!!` 反義複合（curated 列表） |
| 詞庫 | **詞庫埠**：多字收錄靠**詞級標音**（上游詞表整理）；單字靠 rime **預設**讀音；**不**用 pycantonese 猜讀注入 |
| 排序 | 同 match tier：**純漢字** → **essay 詞頻** → **curated** → **pron_rank** → 字面（[`CONTEXT.md`](CONTEXT.md) § 搜尋結果排序） |
| Runtime | 無 ML 模型；essay 啟動載入記憶體 dict；`word_relations` + static thesaurus 純 SQL |

---

## 快速開始

### 一般使用者（推薦）

完整離線體驗（詞條搜尋 + 近反義）請用官方 portable 套件，**毋須** clone 源碼或自行灌庫。

1. 從 [GitHub Releases](https://github.com/ICE-U-code/Canto-0243/releases) 下載 **`canto-0243-portable.zip`**（見 `v1.0.0-data` 或最新 data release）。
2. 解壓縮整個資料夾（例如 `canto-0243-portable`）。
3. **Windows**：雙擊 **`START.bat`**。  
   **macOS**：建議下載 `canto-0243-portable-macos.tar.gz`（若只有 zip，解壓後雙擊 `START.command` 或執行 `./START.sh`）。  
   **Linux**：`chmod +x START.sh && ./START.sh`

**需求**：Python 3.10 或以上（已加入 PATH）。首次啟動會自動建立 venv 並安裝依賴；瀏覽器會開啟搜尋頁。

| 入口 | URL |
|------|-----|
| 前端 | http://127.0.0.1:8000/frontend/index.html |
| API 文件 | http://127.0.0.1:8000/docs |
| 健康檢查 | http://127.0.0.1:8000/ |

套件內已含 `lyrics.db` 與靜態近反義資料。疑難排解見解壓後資料夾內 `README.txt`。

#### 從 Git clone（進階／開發）

clone 源碼**不**含完整 `lyrics.db`。若要在本機跑 `python main.py`，請先從 Releases 下載 `lyrics.db` 放專案根目錄，或走下方 **Maintainer** 管線自建。

```bash
pip install -r requirements.txt
python main.py
```

亦可使用開發用 `./start.sh`（會建 venv 並開瀏覽器；仍須自备 `lyrics.db`）。

**隨 repo 已有**（第 1 層，見下方「資料來源」）：rime 單字 `char.csv`、essay 詞頻語料、curated 常用詞、反義複合列表。近反義 static thesaurus 需 `bootstrap_data.py`（第 2 層）後才有完整 runtime fallback。

### Maintainer（重建詞條庫與近反義）

產物均為本地／gitignore，**勿** commit。詳見 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
pip install -r requirements-dev.txt
python scripts/bootstrap_data.py
# 1. 自上游詞表整理多字詞級標音（見 THIRD_PARTY_NOTICES § 多字詞級標音）
# 2. 匯入 words 表：
python scripts/ingest/import_data.py
# 3. 近反義 ingest：
python -m ingest report
python -m ingest normalize --source current_static
python -m ingest build-relations
# 或（legacy）：python scripts/legacy/generate_relationships.py
```

可選近反義來源（預設關閉，如 COW）見 `data/syn_ant/sources.yaml`；需自行取得 raw 後再以 `--source` 指定。

#### 官方資料 Release（四件套）

再分發前核對 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。**勿**將大檔 commit 入 git。

| 資產 | 用途 |
|------|------|
| `lyrics.db` | 完整**詞條庫**（`words` + `word_relations`）；放專案根目錄即可搜尋＋近反義 |
| `canto-0243-portable.zip` | Windows 離線套件（解壓 → `START.bat`） |
| `canto-0243-portable-macos.tar.gz` | macOS 離線套件（解壓 → `START.command`／`START.sh`；保留執行權） |
| `words-lexicon.json` | **詞級標音**副件；可餵 `import_data.py` 或 `data/raw/clean/` 以對齊 runtime 收錄門 |

```bash
# 本地驗證通過後：
python scripts/export_words_lexicon.py -o dist/words-lexicon.json
# Windows:
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
# macOS / Linux:
bash scripts/build-portable.sh
# 上傳四件套至 GitHub Release（對應 tag；portable 必須 zip + macOS tar.gz 齊備）
```

---

## 部署與資料庫

**產品保證路徑**：離線單機 + **SQLite**（`lyrics.db` 或 `DATABASE_URL` 指向的 SQLite 檔）。新 schema 變更（欄位、索引、表）**僅**透過 SQLite bootstrap／`scripts/db/init_db.py` 維護；測試亦只覆蓋 SQLite。

**PostgreSQL**：程式中留有凍結 scaffold（`IS_POSTGRES` 分支、Alembic migration），**非**主要交付目標——無整合測試、migration 不再主動更新。若仍要實驗：

```bash
pip install -r requirements-postgres.txt
# .env.local：DATABASE_URL=postgresql://...
alembic upgrade head    # 對齊既有 migration；不保證與最新 SQLite schema 同步
python main.py          # 啟動時會 log 凍結警告
```

PG 相關 issue／PR 可 **best-effort** 合併小修，但不構成產品承諾。領域用語見 [`CONTEXT.md`](CONTEXT.md) § 產品邊界。

---

## 查詢語法速查

| 輸入範例 | 說明 |
|----------|------|
| `做到` | 純字面：列出該詞擁有的 code／粵拼 header + 同碼同韻相關詞 |
| `23` | 純 0243 碼（長度 = 碼位數；回應含 `X-Search-Total`，前端可載入更多） |
| `23就` / `23@就` | 混合：碼 + 參考字（`@` 字面錨） |
| `門0` / `好23` | wildcard：`_` 或數字碼位 + 字面 |
| `香港=` | 整詞同韻 |
| `2=我3` / `23=你4` | 碼夾參考字：左 `=` 比聲母，右 `=` 比韻母 |
| `?就=` / `香=?` | 韻／聲錨 |
| `~開心` / `33!開心` | 近義／反義（可帶碼前綴） |
| `!!` / `2!!就` | 雙字反義複合 |
| `mode=syn` + `快樂` | 近反義模式（兩欄 UI；粵拼查詢請切換 0243／02493 模式） |
| `nei hou` / `ming4 baak6` | 粵拼查詢：無調比字母、有調須完全一致 |

```http
GET /words/search/?q=23就&mode=m2
GET /words/search/?q=23=你4&mode=m1
GET /words/search/?q=香港=&mode=m1
GET /words/search/?q=快樂&mode=syn
```

---

## 架構概覽

```text
查詢字串 → QueryEngine / parse_query → handler（equals / hybrid / mask / syn …）
                ↓
         words 表（ORM + length 索引）· word_cache（短詞 preload）
                ↓
         essay_sort（純漢字 → essay → curated → pron_rank）· 結構性 tier 不變
                ↓
         JSON 結果（code / jyutping / word 列；純數字含 X-Search-Total）
```

| 模組 | 職責 |
|------|------|
| `app/services/match_spec_factory.py` | ParsedQuery → MatchSpec 正規化工廠 |
| `app/services/query_engine.py` | 查詢分派 |
| `app/services/essay_sort.py` | 統一搜尋結果排序 key |
| `app/services/position_match.py` | 位置型比對 + 等號／碼夾等號查詢 |
| `app/services/word_lookup_executor.py` | 純數字／粵拼查詢／字面 lookup |
| `app/services/jyutping_match.py` | 粵拼查詢精準音節比對 |
| `app/services/code_aware_ranker.py` | 純漢字查詢的分段 header + 同韻 tier |
| `app/services/lexicon_port.py` | 詞庫埠（收錄門檻 + 讀音） |
| `app/services/word_ensure_service.py` | 查無詞時 lexicon 注入 |
| `app/services/syn_ant_service.py` | 近反義（DB + ThesaurusPort） |
| `app/lexicon/essay_index.py` | Essay 語料 → 記憶體詞頻 dict（不寫入 DB） |
| `app/thesaurus/static_index.py` | runtime cilin / guotong / antisem |

**設計原則**：ingest 重型、runtime 輕量；regex 只在 Python 解析輸入，查詢走索引／純 SQL。

---

## 專案結構

```text
Canto-0243/
├── app/
│   ├── db/                 # connection · bootstrap · dialect
│   ├── lexicon/            # static 0243 · rime char · essay · curated
│   ├── thesaurus/          # runtime static 近反義索引
│   ├── services/           # 搜尋、排序、query engine、syn/ant
│   ├── repositories/
│   ├── routers/word.py
│   ├── models/ · schemas/
│   └── utils/              # jyutping_codec · word_cache · json_helpers
├── frontend/index.html
├── data/                   # 見下方「資料來源」三層模型
│   ├── rime/char.csv       # 隨 repo（可 bootstrap 更新）
│   ├── essay/              # essay-cantonese.txt（隨 repo）
│   ├── lexicon/            # curated_common.txt（隨 repo）
│   └── syn_ant/            # sources.yaml · compound_antonyms.txt（隨 repo）
├── ingest/                 # syn/ant v2 pipeline + CLI（python -m ingest）
├── scripts/
│   ├── fetch/              # fetch_rime_data · fetch_essay_data · fetch_cilin_data
│   ├── db/                 # init_db · reset_db
│   ├── ingest/             # import_data
│   └── legacy/             # generate_relationships · backfill_embeddings
├── tests/
├── main.py · start.sh
├── CONTEXT.md · WORKLOG.md · AGENTS.md
└── requirements.txt · requirements-dev.txt · requirements-postgres.txt
```

---

## 資料來源與授權

再分發前請核對各上游原文。完整授權表見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。收錄與排序政策見 [`CONTEXT.md`](CONTEXT.md) § 詞庫與排序。

### 三層模型

| 層級 | 說明 | 例子 |
|------|------|------|
| **1 · 隨 repo** | clone 即有；用於單字讀音、排序、curated 列表 | `data/rime/char.csv`、`data/essay/essay-cantonese.txt`、`data/lexicon/curated_common.txt`、`data/syn_ant/compound_antonyms.txt` |
| **2 · bootstrap fetch** | `python scripts/bootstrap_data.py` 下載；用於近反義 static thesaurus 等 | cilin、guotong、antisem、words.hk manifest（路徑見 THIRD_PARTY_NOTICES） |
| **3 · maintainer 自建** | gitignore；**勿** commit | `lyrics.db`、多字**詞級標音**匯入產物（`import_data.py` 輸入） |

```bash
python scripts/bootstrap_data.py              # 第 2 層：一鍵 fetch
python scripts/fetch/fetch_essay_data.py [--verify]   # 可選：更新 essay
```

### 詞庫上游（多字詞級標音）

多字**詞級標音**由 maintainer 自下列上游整理，再對照 0243 鍵盤編碼產出（第 3 層；法律細節見 THIRD_PARTY_NOTICES）。

| 上游 | 連結 | 授權 |
|------|------|------|
| words.hk 粵典詞表 | [wordslist](https://words.hk/faiman/analysis/wordslist/) | **公有領域**（致謝 [words.hk](https://words.hk/)） |
| CC-Canto | [download](https://cantonese.org/download.html) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| 開放詞典 · 粵語詞典 | [下載](https://kaifangcidian.com/xiazai/) | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |

單字讀音權威來自 rime `char.csv`（[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)，[rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream)）。Essay 詞頻與 curated 列表**僅用於排序**，不替代詞庫收錄門檻。

### 近義／反義（預設來源）

Manifest：`data/syn_ant/sources.yaml`。預設管線（`current_static`）使用下列來源；fetch 後寫入 `word_relations` 表，並作 runtime static thesaurus fallback。

| 來源 | 上游 | 授權 |
|------|------|------|
| cilin | [yaleimeng/Final_word_Similarity](https://github.com/yaleimeng/Final_word_Similarity)（[liao961120/cilin](https://github.com/liao961120/cilin) 匯出） | **MIT** |
| guotong | [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary) | [Anti-996](https://github.com/996icu/996.ICU/blob/master/LICENSE) |
| antisem | [liuhuanyong/ChineseAntiword](https://github.com/liuhuanyong/ChineseAntiword) | 無明示授權；fetch + 署名 |
| compound_antonyms | 專案 curated | 專案內容 |

**可選來源**（如 Chinese Open Wordnet／COW）見 `data/syn_ant/sources.yaml`；預設關閉，需自行取得 raw 並以 `--source` 啟用。Legacy embedding 路徑：`scripts/legacy/generate_relationships.py --include-embedding`。

---

## 測試

目前 **219** 個 unittest（含 `test_jyutping_match`、`test_search_sort` 等）。

```bash
python -m unittest discover -s tests -q
# 或分模組：
python -m unittest tests.test_word_detail tests.test_query_parser tests.test_position_match -v
python -m unittest tests.test_lexicon_ensure tests.test_rime_lexicon tests.test_essay_ranking tests.test_p4_ranking tests.test_search_sort -v
python -m unittest tests.test_syn_ant_ingest tests.test_utils -v
```

關鍵回歸案例：純漢字 strict code、`門0`／`好23`、wildcard、`mode=syn`、等號／碼夾查詢、粵拼精準查詢。

---

## 依賴

| 層 | 檔案 | 用途 |
|----|------|------|
| Runtime（SQLite） | `requirements.txt` | 離線查詢；無 torch / sentence-transformers / psycopg2 |
| Ingest / dev | `requirements-dev.txt` | cilin、opencc、ML（`scripts/ingest/import_data`、`scripts/legacy/*` 等） |
| PostgreSQL（凍結） | `requirements-postgres.txt` | `psycopg2-binary`、`alembic`；實驗用，非產品承諾 |

---

## 致謝

本專案在作者幾乎零程式背景的起步階段，得益於 **[ivorhoulker](https://github.com/ivorhoulker)** 擔任 code consultant：在設計與實作上給予大量指導，並提出許多寶貴的修改建議。沒有這些協助，**Canto-0243** 不會走到今天。

---

## 相關文件

| 文件 | 內容 |
|------|------|
| [`LICENSE`](LICENSE) | Canto-0243 License（程式碼） |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | 第三方資料授權 |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 貢獻與 PR 指南 |
| [`CONTEXT.md`](CONTEXT.md) | 領域詞彙表（查詢語法、詞庫、排序、產品邊界） |
| [`WORKLOG.md`](WORKLOG.md) | 變更紀錄與效能驗證 |
| [`AGENTS.md`](AGENTS.md) | Agent 協作指引 |

---

**最後更新**：2026-06-13
