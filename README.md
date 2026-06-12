# 0243 離線押韻字典

離線粵語填詞查韻工具：依 **0243／02493 數字碼**、**粵拼**、**韻母／聲母規則** 與 **近義／反義關係**，幫創作者快速找可替換詞條。

**技術棧**：FastAPI · SQLAlchemy · SQLite（可切 PostgreSQL）· 純 HTML/JS 前端  
**語意與領域詞彙**：見 [`CONTEXT.md`](CONTEXT.md)

---

## 功能概覽

| 類別 | 能力 |
|------|------|
| 編碼模式 | **鬆** `mode=m1`（0243 等價變體）· **緊** `mode=m2`（含 9 鍵聲調） |
| 查詢類型 | 純漢字 · 純數字 · 粵拼片段 · 混合碼字（`23就`）· wildcard（`門0`、`_識_`）· 等號韻（`香港=`、`2=我3`）· 韻／聲錨（`?就=`） |
| 近反義 | `mode=syn` 全欄 UI；或鬆／緊模式下 `~詞` / `!詞` / `!!` 複合反義 |
| 詞庫 | `LexiconPort`：多字走 0243 clean JSON；單字走 rime `char.csv` **預設**讀音；**不**用 pycantonese 猜讀注入 |
| 排序 | 同 match tier：**curated 常用詞** → **essay 頻次** → **pron_rank** → 字面／粵拼 |
| Runtime | 無 ML 模型；`word_relations` + static thesaurus 純 SQL；啟動 preload 詞庫／快取 |

---

## 快速開始

### 一般使用者

```bash
pip install -r requirements.txt
python fetch_rime_data.py      # 單字詞庫 → data/rime/char.csv
python fetch_essay_data.py     # 排序語料 → data/essay/essay-cantonese.txt（選用但建議）
python main.py
```

或使用一鍵腳本（會建 venv 並開瀏覽器）：

```bash
./start.sh
```

| 入口 | URL |
|------|-----|
| 前端 | http://127.0.0.1:8000/frontend/index.html |
| API 文件 | http://127.0.0.1:8000/docs |
| 健康檢查 | http://127.0.0.1:8000/ |

自訂 DB：建立 `.env`，設定 `DATABASE_URL`。正式 PostgreSQL 環境請 `alembic upgrade head`。

### Maintainer（首次灌庫）

repo 內通常**不含**完整 `data/raw/*.json` 與 `lyrics.db`，需自行準備後匯入：

```bash
pip install -r requirements-dev.txt
python import_data.py                    # data/raw/clean/*.json → words 表
python fetch_cilin_data.py               # → data/cilin/new_cilin.txt
python ingest_syn_ant.py report
python ingest_syn_ant.py normalize --source current_static
python ingest_syn_ant.py build-relations # → word_relations 表
# 或：python generate_relationships.py
```

---

## 查詢語法速查

| 輸入範例 | 說明 |
|----------|------|
| `做到` | 純字面：列出該詞擁有的 code／粵拼 header + 同碼同韻相關詞 |
| `23` | 純 0243 碼（長度 = 碼位數） |
| `23就` / `23@就` | 混合：碼 + 參考字（`@` 字面錨） |
| `門0` / `好23` | wildcard：`_` 或數字碼位 + 字面 |
| `香港=` | 整詞同韻 |
| `2=我3` / `23=你4` | 碼夾參考字：左 `=` 比聲母，右 `=` 比韻母 |
| `?就=` / `香=?` | 韻／聲錨 |
| `~開心` / `33!開心` | 近義／反義（可帶碼前綴） |
| `!!` / `2!!就` | 雙字反義複合 |
| `mode=syn` + `快樂` | 近反義模式（兩欄 UI） |

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
         LexiconPort（CompositeLexicon）· essay / curated / pron_rank 排序
                ↓
         JSON 結果（code / jyutping / word 列）
```

| 模組 | 職責 |
|------|------|
| `app/services/query_engine.py` | 查詢分派 |
| `app/services/position_match.py` | 位置型比對（mask、hybrid、韻錨） |
| `app/services/equals_query_handler.py` | 等號 framed 查詢 |
| `app/services/code_aware_ranker.py` | 純漢字結果 tier 排序 |
| `app/services/lexicon_port.py` | 詞庫埠（收錄門檻 + 讀音） |
| `app/services/word_ensure_service.py` | 查無詞時 lexicon 注入 |
| `app/services/syn_ant_service.py` | 近反義（DB + ThesaurusPort） |
| `app/thesaurus/static_index.py` | runtime cilin / guotong / antisem |

**設計原則**：ingest 重型、runtime 輕量；regex 只在 Python 解析輸入，查詢走索引／純 SQL。

---

## 專案結構

```text
0243_lyrics_tool/
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
├── data/
│   ├── raw/                # 0243_dict · clean JSON（通常本地／gitignore）
│   ├── rime/               # char.csv（fetch_rime_data.py）
│   ├── essay/              # essay-cantonese.txt（fetch_essay_data.py）
│   ├── lexicon/            # curated_common.txt
│   ├── cilin/ · thesaurus/ · antonym/
│   └── syn_ant/            # sources.yaml · compound_antonyms · raw/
├── ingest/                 # syn/ant v2 pipeline
├── tests/
├── main.py · start.sh
├── import_data.py · fetch_rime_data.py · fetch_essay_data.py · fetch_cilin_data.py
├── ingest_syn_ant.py · generate_relationships.py
├── CONTEXT.md · WORKLOG.md
└── requirements.txt · requirements-dev.txt
```

---

## 資料來源與授權

再分發或商用前請自行核對各上游原文。完整注入政策見 [`CONTEXT.md`](CONTEXT.md) § 詞庫與注入。

### 0243 主詞庫（→ `words` 表）

`data/raw/0243_dict_1to5digits.json` 與 `data/raw/clean/*.json` 由 maintainer 自下列來源整理，再對照 0243 鍵盤編碼產出。

| 上游 | 連結 | 授權 |
|------|------|------|
| words.hk 粵典詞表 | [wordslist](https://words.hk/faiman/analysis/wordslist/) · [開放資料說明](https://words.hk/base/hoifong/) | [NCODL 1.0](https://words.hk/base/hoifong/)（非商業；商用須另洽） |
| CC-Canto | [download](https://cantonese.org/download.html) · [about](https://cantonese.org/about.html) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| 開放詞典 · 粵語詞典 | [下載](https://kaifangcidian.com/xiazai/) · [版權聲明](https://kaifangcidian.com/) | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |

| 本機產物 | 路徑 | Ingest |
|----------|------|--------|
| 0243 編碼詞表 | `data/raw/0243_dict_1to5digits.json` | — |
| 清洗 JSON | `data/raw/clean/*.json` | `python import_data.py` |

### Runtime 詞庫與排序

| 資料 | 路徑 | 上游 | 授權 | 用途 |
|------|------|------|------|------|
| Rime 單字 | `data/rime/char.csv` | [rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | 單字 `_ensure`（`pron_rank=預設`） |
| 0243 clean | `data/raw/clean/*.json` | 見上表 | 見上表 | 多字 `_ensure` |
| Essay 頻次 | `data/essay/essay-cantonese.txt` | [essay-cantonese.txt](https://raw.githubusercontent.com/rime/rime-cantonese/refs/heads/main/essay-cantonese.txt) | [CC BY 4.0](https://github.com/rime/rime-cantonese/blob/main/LICENSE-CC-BY) | **僅排序** |
| Curated 常用詞 | `data/lexicon/curated_common.txt` | 專案 curated | 專案內容 | **僅排序**（優先於 essay） |

```bash
python fetch_rime_data.py [--verify]
python fetch_essay_data.py [--verify]
# curated：編輯 data/lexicon/curated_common.txt（一行一詞）
```

### 近義／反義（→ `word_relations` 表）

Manifest：`data/syn_ant/sources.yaml`

| Source | 路徑 | 上游 | 授權 | 預設 |
|--------|------|------|------|------|
| cilin | `data/cilin/new_cilin.txt` | [liao961120/cilin](https://github.com/liao961120/cilin) | 套件 MIT；詞林遵上游 | ✅ |
| guotong | `data/thesaurus/dict_*.txt` | [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary) | [Anti-996 / 996.ICU](https://github.com/996icu/996.ICU/blob/master/LICENSE) | ✅ |
| antisem | `data/antonym/antisem.txt` | bundled | 再分發前請核對 | ✅ |
| compound_antonyms | `data/syn_ant/compound_antonyms.txt` | 專案 curated | 專案內容 | ✅ |
| cow | `data/syn_ant/raw/cow/` | Chinese Open Wordnet | CC-BY | ❌ |
| embedding | — | `generate_relationships.py --include-embedding` | MiniLM 依模型授權 | 選用 |

cilin／guotong／antisem 同時作 runtime static thesaurus fallback。

---

## 測試

```bash
python -m unittest discover -s tests -q
# 或分模組：
python -m unittest tests.test_word_detail tests.test_query_parser tests.test_position_match -v
python -m unittest tests.test_lexicon_ensure tests.test_rime_lexicon tests.test_essay_ranking tests.test_p4_ranking -v
python -m unittest tests.test_syn_ant_ingest tests.test_utils -v
```

關鍵回歸案例（詳見下方效能規範）：純漢字 strict code、`門0`／`好23`、wildcard、`mode=syn`、等號／碼夾查詢。

---

## 開發規範

### 瞬間搜尋（不可協商）

preload 完成後，常見查詢端到端目標 **< 0.2s**（否則 **< 0.5s**）。**不得**為加速而改變結果集或排序語意。變更前後須比對關鍵 case 並更新 [`WORKLOG.md`](WORKLOG.md)。

```bash
python scripts/enforce_bench.py   # 本地 lyrics.db：關鍵查詢 latency + 前 5 筆 dump
```

### 命名

**禁止**在新程式碼使用 `hanzi`。與字面／粵語字符相關請用 **`canto`** 或 **`chars`**。

### 依賴分層

| 層 | 套件 |
|----|------|
| Runtime | `requirements.txt`（無 torch / sentence-transformers） |
| Ingest / dev | `requirements-dev.txt`（cilin、opencc、ML 選用） |

---

## 相關文件

| 文件 | 內容 |
|------|------|
| [`CONTEXT.md`](CONTEXT.md) | 領域語彙、等號查詢語意、詞庫 P0–P4 政策 |
| [`WORKLOG.md`](WORKLOG.md) | 變更紀錄與效能驗證 |
| [`AGENTS.md`](AGENTS.md) | Agent 協作指引 |

---

**最後更新**：2026-06-12
