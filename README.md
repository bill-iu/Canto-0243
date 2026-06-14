# Canto-0243

填粵語歌詞，通常一係就「唔知有咩字」，一係就要喺**同音、押韻、近義**之間快速換字，又要對準 0243 與粵拼讀音。傳統做法係在詞典、韻書、近義表之間搵嚟搵去，手動試「呢個位可唔可以換另一個字」——慢，而且容易漏咗好多可以用嘅字。[0243.hk](https://0243.hk) 已經算係近年最好用嘅粵語填詞查找網站，但係偶爾都會 502 Bad Gateway 上唔到；或者喺搵字嘅時候無限輪迴 load 唔到；又或者你想搵某個字但係佢冇嗰個功能——呢啲時候就會拖慢你嘅進度。

**Canto-0243**（**ONE·搵·韻**）係我利用唔同嘅AGENT開發嘅一個離線粵語填詞查找工作台：依 **0243／02493 數字碼**、**粵拼**、**韻母／聲母規則**與 **近義／反義關係**，幫你在幾秒內列出可替換嘅**詞條**。打 `23就` 搵同調又同「就」同韻嘅尾字；打 `香港=` 搵同「香港」同韻嘅候選詞；打 `~開心` 或切換**近反義模式**搵近義/反義詞；打 `~~`／`!!` 搵填詞常用嘅二字近義／反義複合詞。套件解壓即用，詞庫與近反義資料都在本地環境，唔使常駐雲端。

**授權**：程式碼依 [Canto-0243 License](LICENSE)（CC BY-NC-SA 4.0 + 附加條款；**非 OSI 開源**）。第三方資料見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。  
**技術棧**：FastAPI · SQLAlchemy · SQLite（離線單機）· 純 HTML/JS 前端  
**領域詞彙**：見 [`CONTEXT.md`](CONTEXT.md) · 貢獻指南 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)

---

## 最新版本

官方離線資料包：**[v1.0.2-data](https://github.com/ICE-U-code/Canto-0243/releases/tag/v1.0.2-data)**（`canto-0243-portable.zip`、macOS `tar.gz`、`lyrics.db`、`words-lexicon.json`）。問題與建議歡迎 [GitHub Issues](https://github.com/ICE-U-code/Canto-0243/issues)。

---

## 功能

* **0243／02493 編碼搜尋**：**0243模式** `mode=m1`（0243 等價變體）與 **02493模式** `mode=m2`（含 9 鍵聲調、分清二聲）。
* **多種查詢語法**：純漢字 · 純數字（分頁 + 總數 header）· **粵拼查詢**（`syut`／`nei hou`／`ming4 baak6`）· 混合碼字（`23就`）· wildcard（`3_`、`23?`）· 等號韻／聲（`香港=`、`2=我3`）· 韻／聲錨（`?就=`）。
* **近反義**：**近反義模式** `mode=syn` 全欄 UI（不收粵拼）；或在 0243搜尋模式下 `~詞`／`!詞`、反義複合 `!!`、近義複合 `~~`。
* **詞庫與收錄**：**詞庫埠** raw lookup + **收錄決策**；多字詞級標音或音節拼接讀音。
* **近反義資料**：**靜態詞林埠**（cilin／國語辭典近義／反義語料）；runtime 與 ingest 共用同一規則。
* **結果排序**：同 match tier 內 **純漢字** → **essay 詞頻** → **curated** → **pron_rank** → 字面（詳見 [`CONTEXT.md`](CONTEXT.md) § 搜尋結果排序）。

---

## 快速開始

### 1. 下載與安裝（一般使用者）

完整離線體驗請用官方 portable 套件，**毋須** clone 源碼或自行灌庫。

1. 從 [GitHub Releases](https://github.com/ICE-U-code/Canto-0243/releases) 下載 **`canto-0243-portable.zip`**（建議對照 [`v1.0.2-data`](https://github.com/ICE-U-code/Canto-0243/releases/tag/v1.0.2-data) 或最新 data release）。
2. 解壓縮整個資料夾（例如 `canto-0243-portable`）。
3. 依平台啟動：
   * **Windows**：雙擊 **`START.bat`**。
   * **macOS**：建議下載 `canto-0243-portable-macos.tar.gz`；解壓後雙擊 `START.command` 或執行 `./START.sh`。
   * **Linux**：`chmod +x START.sh && ./START.sh`

**需求**：Python 3.10+（已加入 PATH）。首次啟動會自動建立 venv 並安裝依賴；瀏覽器會開啟搜尋頁。

| 入口 | URL |
|------|-----|
| 前端（搜尋教學在頂欄） | http://127.0.0.1:8000/frontend/index.html |
| API 文件 | http://127.0.0.1:8000/docs |
| 健康檢查 | http://127.0.0.1:8000/ |

套件內已含 `lyrics.db` 與靜態近反義資料。疑難排解見解壓後資料夾內 `README.txt`。

### 2. 如何使用

**三種模式**（頂欄 segmented control）：

| 模式 | `mode` | 用途 |
|------|--------|------|
| **0243模式**（鬆） | `m1` | 0243 碼等價變體 |
| **02493模式**（緊） | `m2` | 02493 碼，分清二聲 |
| **近反義** | `syn` | 打漢字列出近義／反義欄（不收粵拼） |

**語法族**（皆可在 **0243搜尋模式** 使用，除非註明）：

* **字面／數字／粵拼**：直接打「你好」、`23`、`nei hou`。
* **位置與 wildcard**：`香??`、`?你?`、`3_`、`23?`。
* **數字 + 尾字**：`23就`（尾字同「就」同韻）、`23@就`（尾字字面固定）、`23*就`（加長位置）。
* **等號錨點**：`=` 在錨字**後**比韻母（`?就=`）、在錨字**前**比聲母（`?=就`）；整詞同「香港」同韻 `香港=`、碼夾 `2我=3`。
* **近反義關係查詢**：`~開心`、`!你`、`33!開心`。
* **反義複合詞**：`!!`、`33!!`、`!!你`、`33!!你`（如生死、是非）。
* **近義複合詞**：`~~`、`33~~`、`~~你`、`33~~你`（如朋友、恐懼）；**不適用近反義模式**。

App 內 **「搜尋教學」** 有完整可點擊例子；下方「查詢語法速查」與教學頁一致，供離線查閱。

### 3. 從 Git clone（開發者）

clone 源碼**不**含完整 `lyrics.db`。若要在本機跑 `python main.py`，請先從 Releases 下載 `lyrics.db` 放專案根目錄，或走下方 Maintainer 管線自建。

```bash
pip install -r requirements.txt
python main.py
```

亦可使用 `./start.sh`（建 venv 並開瀏覽器；仍須自备 `lyrics.db`）。

**隨 repo 已有**（第 1 層，見「資料來源」）：essay 詞頻、curated 常用詞、反義／近義複合列表，以及 bundled 近反義 static 檔。**單字 rime `char.csv` 與 antisem 不在 git**——clone 後請先跑 `python scripts/bootstrap_data.py`（第 2 層）。

---

## Maintainer：重建詞條庫與近反義

產物均為本地／gitignore，**勿** commit。詳見 [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)。

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
```

可選近反義來源（預設關閉）見 `data/syn_ant/sources.yaml`。

### 官方資料 Release（四件套）

再分發前核對 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。**勿**將大檔 commit 入 git。

| 資產 | 用途 |
|------|------|
| `lyrics.db` | 完整**詞條庫**（`words` + `word_relations`） |
| `canto-0243-portable.zip` | Windows 離線套件（`START.bat`） |
| `canto-0243-portable-macos.tar.gz` | macOS 離線套件（`START.command`／`START.sh`） |
| `words-lexicon.json` | **詞級標音**副件 |

```bash
python scripts/export_words_lexicon.py -o dist/words-lexicon.json
# Windows:
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
# macOS / Linux:
bash scripts/build-portable.sh
# 上傳四件套至 GitHub Release（portable 須 zip + macOS tar.gz 齊備）
```

---

## 查詢語法速查

與前端「搜尋教學」可點擊例子一致。

### 基本查詢

| 輸入範例 | 說明 |
|----------|------|
| `就` | 查呢個字嘅所有讀音 |
| `你好` | 查呢個詞語 |
| `syut` | 粵拼查詢（冇聲調） |
| `nei hou` | 粵拼查詢（冇聲調） |
| `ming4 baak6` | 粵拼查詢（有聲調） |

### 0243／02493 數字

| 輸入範例 | 說明 | 模式 |
|----------|------|------|
| `23` | 找同音字 | 0243模式 |
| `93` | 02493 增加數字 9 | 02493模式 |

### 字面位置

| 輸入範例 | 說明 |
|----------|------|
| `香??` | 三字詞，第一個字係「香」 |
| `?你?` | 三字詞，中間係「你」 |
| `23?就` | 四字詞，23＋？＋就 |

### 數字 + 尾字

| 輸入範例 | 說明 |
|----------|------|
| `23就` | 二字，23 同音，尾字同「就」同韻 |
| `23@就` | 二字，23 同音，尾字必須係「就」 |
| `23*就` | 三字，23 同音，第三個字係「就」 |
| `23*就=` | 三字，23 同音，第三個字同「就」同韻 |
| `23*=就` | 三字，23 同音，第三個字同「就」同聲 |

### 韻母錨點

| 輸入範例 | 說明 |
|----------|------|
| `香=?` | 二字，首字同「香」同韻 |
| `?就=` | 二字，尾字同「就」同韻 |
| `??就=` | 三字，尾字同「就」同韻 |

### 聲母錨點

| 輸入範例 | 說明 |
|----------|------|
| `=香?` | 二字，首字同「香」同聲 |
| `?=就` | 二字，尾字同「就」同聲 |
| `??=就` | 三字，尾字同「就」同聲 |

### 右 `=` 查韻母（整詞／碼夾）

| 輸入範例 | 說明 |
|----------|------|
| `香港=` | 二字，整詞同「香港」同韻 |
| `大蛋糕=` | 三字，整詞同「大蛋糕」同韻 |
| `34英皇=` | 五字，前碼 34＋整詞同「英皇」同韻 |
| `2我=3` | 二字，23 同音，首字同「我」同韻 |
| `23就=` | 二字，23 同音＋尾字同「就」同韻（同 `23就`） |

### 左 `=` 查聲母

| 輸入範例 | 說明 |
|----------|------|
| `=香港` | 二字，整詞同「香港」同聲 |
| `2=我3` | 二字，23 同音，首字同「我」同聲 |

### 萬用字元

| 輸入範例 | 說明 |
|----------|------|
| `3_` | 二字，首字和 3 同音，尾字不限 |
| `23?` | 三字，頭兩字 23 同音，第三個字不限 |

### 近義／反義

| 輸入範例 | 說明 |
|----------|------|
| `~開心` | 近義於「開心」 |
| `!你` | 反義於「你」（含鏡像近義） |
| `33!開心` | 33 同音＋反義於「開心」 |
| `mode=syn`＋`開心` | 近反義模式（兩欄 UI） |

### 反義複合詞

| 輸入範例 | 說明 |
|----------|------|
| `!!` | 二字反義複合（如生死、是非） |
| `33!!` | 33 同音＋反義複合 |
| `!!你` | 反義複合，尾字同「你」同韻 |
| `33!!你` | 33 同音＋反義複合＋尾字同「你」同韻 |

### 近義複合詞

| 輸入範例 | 說明 |
|----------|------|
| `~~` | 二字近義複合（如朋友、恐懼） |
| `33~~` | 33 同音＋近義複合 |
| `~~你` | 近義複合，尾字同「你」同韻 |
| `33~~你` | 33 同音＋近義複合＋尾字同「你」同韻 |

```http
GET /words/search/?q=你好&mode=m1
GET /words/search/?q=23就&mode=m1
GET /words/search/?q=香港=&mode=m1
GET /words/search/?q=2=我3&mode=m1
GET /words/search/?q=nei%20hou&mode=m1
GET /words/search/?q=!你&mode=m1
GET /words/search/?q=~~&mode=m1
GET /words/search/?q=開心&mode=syn
```

---

## 進階：架構與部署

### 架構概覽

```text
查詢字串 → query_parse（語法分類 · ParsedQuery · build_match_spec）
         → query_dispatch（優先序 registry → executors）
                ↓
    position_match · word_lookup_executor · relation_syntax_executor
    · compound_ant_executor · compound_syn_executor
                ↓
    domain/lexicon（收錄決策）· domain/thesaurus（靜態詞林）· domain/relations（近反義池／關係圖）
                ↓
         words 表 · word_cache（短詞 preload）
                ↓
         essay_sort · JSON 結果（純數字含 X-Search-Total）
```

| 層 | 路徑 | 職責 |
|----|------|------|
| 領域 | `app/domain/lexicon/` | 詞庫埠 · **收錄決策** |
| 領域 | `app/domain/thesaurus/` | **靜態詞林埠** |
| 領域 | `app/domain/relations/` | **近反義池** · **關係圖** · ranking |
| 服務 | `app/services/query_parse.py` | `parse_query` · `build_match_spec` |
| 服務 | `app/services/query_dispatch.py` | `search_words` registry |
| 服務 | `app/services/position_match.py` | 位置比對 · 等號／碼夾 |
| 服務 | `app/services/*_executor.py` | lookup · `~`/`!` · `!!` · `~~` |

設計原則：領域規則在 `app/domain/`；ingest 與 runtime 共用同一埠與池規則。

### 部署與資料庫

**產品保證路徑**：離線單機 + **SQLite**（`lyrics.db`）。新 schema 僅透過 SQLite bootstrap／`scripts/db/init_db.py` 維護。

**PostgreSQL**：凍結 scaffold，**非**主要交付目標。實驗用見 `requirements-postgres.txt` 與 [`CONTEXT.md`](CONTEXT.md) § 產品邊界。

### 專案結構

```text
Canto-0243/
├── app/                    # API · domain · services · models
├── frontend/               # index.html（查韻首屏）· relation-entry.html
├── portable/               # START.bat · START.sh · env.portable
├── data/                   # 見「資料來源」三層模型
├── ingest/                 # python -m ingest
├── scripts/                # bootstrap · build-portable · import_data
├── tests/
├── docs/                   # CONTRIBUTING · agents/
├── main.py · start.sh      # 開發入口
├── README.md · LICENSE · THIRD_PARTY_NOTICES.md
├── CONTEXT.md · WORKLOG.md · AGENTS.md · skills-lock.json
└── requirements*.txt
```

### 資料來源與授權

再分發前請核對 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。收錄與排序見 [`CONTEXT.md`](CONTEXT.md) § 詞庫與排序。

| 層級 | 說明 | 例子 |
|------|------|------|
| **1 · 隨 repo** | clone 即有 | `data/essay/`、`data/lexicon/`、`data/syn_ant/`、bundled cilin／thesaurus |
| **2 · bootstrap** | `python scripts/bootstrap_data.py` | rime `char.csv`、antisem |
| **3 · maintainer 自建** | gitignore | `lyrics.db`、詞級標音 JSON |

近義／反義預設管線：`data/syn_ant/sources.yaml`（cilin、guotong、antisem、compound 列表）。詳表見原 README 上游連結與 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

---

## 測試

目前 **225** 個 unittest。

```bash
python -m unittest discover -s tests -q
```

關鍵回歸：純漢字 strict code、wildcard、`mode=syn`、等號／碼夾、粵拼、`~~`／`!!` 複合詞。

---

## 依賴

| 層 | 檔案 | 用途 |
|----|------|------|
| Runtime | `requirements.txt` | FastAPI + SQLAlchemy + SQLite |
| Ingest / dev | `requirements-dev.txt` | ingest 與 legacy 腳本 |
| PostgreSQL（凍結） | `requirements-postgres.txt` | 實驗用 |

---

## Canto-0243 授權與使用

你可以將本工具用於任何合法用途，包括協助粵語填詞、查韻、換字，以及作為**商業創作**（例如歌曲、劇本、已發表歌詞）嘅一部分——前提係遵守下方限制同 [Canto-0243 License](LICENSE)（CC BY-NC-SA 4.0 + 附加條款；**非 OSI 開源**）。

* **唔可以**將本工具重新打包、轉售，或作為競爭性產品單獨發布。
* **唔可以**將本工具提供為**付費 API**、訂閱或按量計費嘅查詢／推理服務（免費自架或免費公開存取另論，但仍須遵守署名等條款）。
* 任何公開發布嘅 fork、改進或衍生版本須**沿用同一授權**（或實質等同條款），並在合理顯眼位置保留 **Canto-0243** 名稱。若你營運公開網站、網頁 app 或 API（包括免費），須顯示例如「Powered by Canto-0243」並連結官方 repo。
* 若你營運**商業軟件**或**付費推理服務**，希望將本工具整合入產品，請先與版權人聯絡或於官方 repo 開 Issue 商議書面授權。

除上述條款外，本授權在實務上等同 [Creative Commons Attribution-NonCommercial-ShareAlike 4.0（CC BY-NC-SA 4.0）](https://creativecommons.org/licenses/by-nc-sa/4.0/) 加上附加限制。完整法律文本見 [`LICENSE`](LICENSE)。

請在任何未來 fork 或發布中保留 **Canto-0243** 名稱。

---

## 致謝與第三方授權

### 專案致謝

本專案喺作者幾乎零程式背景嘅起步階段，得益於 **[ivorhoulker](https://github.com/ivorhoulker)** 擔任 code consultant：喺設計同實行上俾咗好多意見同指導，並且提出許多寶貴嘅修改建議。冇呢啲協助，**Canto-0243** 唔會出現。

亦要多謝 **「0243理論」發明人黃志華老師**，奠定粵語填詞數碼化嘅理論基礎。多謝 [0243.hk](https://0243.hk) 開發者 **Daniel Tam** 先生開發呢個網站，解決咗好多人嘅填詞問題，並啟發作者開發本工具。

### 資料與語料致謝

Canto-0243 整合多個開源詞典、語料與近反義資源。我們明確感謝以下團隊與專案（再分發前請閱讀各上游完整條款；授權總表見 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)）：

* **Rime 粵語（單字讀音 `char.csv`、essay 詞頻）**：來自 [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) 與 [rime/rime-cantonese](https://github.com/rime/rime-cantonese)，採用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。去畀佢哋一個 star！
* **詞林同義詞（Cilin）**：經 [yaleimeng/Final_word_Similarity](https://github.com/yaleimeng/Final_word_Similarity)／[liao961120/cilin](https://github.com/liao961120/cilin) 匯出，採用 **MIT** 授權。
* **國語辭典近義／反義（guotong）**：來自 [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary)，採用 [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE)。
* **ChineseAntiword（antisem）**：來自 [liuhuanyong/ChineseAntiword](https://github.com/liuhuanyong/ChineseAntiword)；上游**無明示授權**，本地使用須署名，再分發前請自行核對條款。
* **words.hk 粵典詞表**：來自 [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/)，**公有領域**（致謝 [words.hk](https://words.hk/)）。
* **多字詞級標音上游**（maintainer 自建 `lyrics.db` 時）：[CC-Canto](https://cantonese.org/download.html)（[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)）、[開放詞典 · 粵語詞典](https://kaifangcidian.com/xiazai/)（[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)）。

使用上述資料建構或再分發詞庫時，你同意遵守各自授權；部分來源含**非商業**或**署名**要求。可選近反義來源（如 COW）預設關閉，見 `data/syn_ant/sources.yaml`。

---

## 相關文件

| 文件 | 內容 |
|------|------|
| [`LICENSE`](LICENSE) | Canto-0243 License |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | 第三方資料授權 |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | 貢獻與 PR · 源碼根目錄約定 |
| [`CONTEXT.md`](CONTEXT.md) | 領域詞彙表 |
| [`WORKLOG.md`](WORKLOG.md) | 變更紀錄 |
| [`AGENTS.md`](AGENTS.md) | Agent 協作指引 |

---

**最後更新**：2026-06-13（README 授權與第三方致謝 · v1.0.2-data）
