# Canto-0243

<p align="center">
  <b>繁體中文</b> · <a href="docs/README.zh-Hans.md">简体中文</a> · <a href="docs/README.en.md">English</a>
</p>

填粵語歌詞，通常一係就「唔知有咩字」，一係就要喺**同音、押韻、近義**之間快速換字，又要對準 0243 與粵拼讀音。傳統做法係喺詞典、韻書、近義表之間搵嚟搵去，手動試「呢個位可唔可以換另一個字」——慢，而且容易漏咗好多可以用嘅字。[0243.hk](https://0243.hk) 已經算係近年最好用嘅粵語填詞查找網站，但係偶爾都會 502 Bad Gateway 上唔到；或者喺搵字嘅時候無限輪迴 load 唔到；又或者你想搵某個字但係佢冇嗰個功能——呢啲時候就會拖慢你嘅進度。

**Canto-0243**（**ONE·搵·韻**）係我用幾個唔同AI AGENT(Cursor, Codex, Grok Build, Github Copilot）開發嘅一個離線粵語填詞查找工作台：用 **0243／02493 數字碼**、**粵拼**、**韻母／聲母規則**與 **近義／反義關係**，喺幾秒內列出符合條件嘅**詞條**。例如打 `23就` 搵同調又同「就」同韻嘅尾字；打 `香港=` 搵同「香港」同韻嘅候選詞；打 `~開心` 或切換**近反義模式**搵近義/反義詞；打 `~~`／`!!` 搵填詞常用嘅二字近義／反義複合詞。套件解壓即用，所有詞庫與近反義資料都儲存喺本地環境，唔使連上網。

**授權**：整包（程式、`lyrics.db`、`words-lexicon.json`）依 [Canto-0243 License](LICENSE)（CC BY-NC-SA 4.0 + 附加條款；**開源**）。第三方上游資料見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。  
**技術棧**：FastAPI · SQLAlchemy · SQLite（離線單機）· 純 HTML/JS 前端  
**領域詞彙**：見 [`CONTEXT.md`](CONTEXT.md) · 貢獻指南 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)

---

## 最新版本

<!-- words-count:zh-Hant -->
目前總詞條列數：**125,244**（`lyrics.db` · `words` 表）
<!-- /words-count:zh-Hant -->

官方離線資料包：**[Canto-0243 v1.0.3](https://github.com/bill-iu/Canto-0243/releases/tag/v1.0.3)**（`canto-0243-portable.zip`、`canto-0243-portable-macos-x86_64.tar.gz`、`lyrics.db`、`words-lexicon.json`；Apple Silicon arm64 過渡期暫不提供）。問題與建議歡迎 [GitHub Issues](https://github.com/bill-iu/Canto-0243/issues)。

---

## 功能

* **0243／02493 編碼搜尋**：**0243模式** `mode=m1`（0243 等價變體）與 **02493模式** `mode=m2`（02493 碼、分清二聲）。
* **多種查詢語法**：純漢字 · 純數字 · **粵拼查詢** · **加號錨**（`23+好=`）· **韻／聲錨**（`就=`）· **串列韻／聲錨** · **四字部分韻／聲錨**（`窮?潦倒=`）· **前綴通配等號** · 整詞等號／碼夾。
* **近反義**：**近反義模式** `mode=syn` 全欄 UI（不收粵拼）；或在 0243搜尋模式下 `~詞`／`!詞`、反義複合 `!!`、近義複合 `~~`。
* **詞庫與收錄**：**詞庫埠** raw lookup + **收錄決策**；多字詞級標音或音節拼接讀音。
* **近反義資料**：**靜態詞林埠**（cilin／國語辭典近義／反義語料）；runtime 與 ingest 共用同一規則。
* **結果排序**：同 match tier 內 **純漢字** → **essay 詞頻** → **curated** → **pron_rank** → 字面（詳見 [`CONTEXT.md`](CONTEXT.md) § 搜尋結果排序）。

---

## 快速開始

### 1. 下載與安裝（一般使用者）

完整離線體驗請用官方 portable 套件，**毋須** clone 源碼或自行灌庫。

1. 從 [GitHub Releases](https://github.com/bill-iu/Canto-0243/releases) 下載 **`canto-0243-portable.zip`**（Windows）與 **`canto-0243-portable-macos-x86_64.tar.gz`**（Intel Mac）；建議對照 [`Canto-0243 v1.0.3`](https://github.com/bill-iu/Canto-0243/releases/tag/v1.0.3)。
2. 解壓縮整個資料夾（例如 `canto-0243-portable`）或 tar 內容。
3. 依平台啟動：
   * **Windows**：解壓後雙擊 **`START.bat`**（無需安裝 Python）。
   * **macOS（Intel x86_64）**：解壓 tar 後進入 `canto-0243-portable/`，雙擊 **`Canto-0243.command`**（會開 Terminal）。若被攔截：**右鍵→打開** → 確認；若只見「惡意軟件」對話框：按 **完成** → **系統設定→隱私與保安** → **強制開啟**（Canto-0243）→ 再雙擊。
   * **macOS（Apple Silicon）**：arm64 tar 過渡期**暫不提供**。
   * **Linux**：`chmod +x START.sh && ./START.sh`（須本機 Python 3.10+）。

**需求**：Windows／macOS **免安裝**（套件已內建 Python）；Linux 仍須 Python 3.10+。

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
* **串列韻／聲錨**：連續碼逐格約束；`{碼}{字}=` 韻、`{碼}={字}` 聲（如 `04困=49倒=`）；**四字部分韻／聲錨**用 `?` 標通配格（如 `窮?潦倒=` 第 2 格任意）。
* **前綴通配等號**：`?{詞≥2}=` 首音節通配＋整段韻模板（如 `?香港=`、`?困潦倒=`）；聲母對稱 `?={詞≥2}`（如 `?=困潦倒`）。
* **數字 + 尾字**：`23就`（尾字同「就」同韻）、`23@就`（尾字字面固定）、`23+就`（加長位置；輸入 `*` 等同 `+`）。
* **等號錨點**：`=` 在錨字**後**比韻母（`就=`、`?+就=`）、在錨字**前**比聲母（`?=就`）；整詞 `香港=`、碼夾 `2=我3`。
* **粵拼錨**：缺字查詢內用粵拼取代漢字參考字（`?syut?` 中格音節、`23o` 碼後**末格**韻母、`3hon4`／`3$漢4` 首格音節等）；**唔係**整段粵拼查詢；**近反義模式**唔收。
* **同音節疊字**：`$$`（鏡像 `~~` 語法）；**同音異讀**：`33/34` 等碼位模板。
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

**隨 repo 已有**（第 1 層，見「資料來源」）：essay 詞頻、curated 常用詞、反義／近義複合列表，以及 bundled 詞林 cilin。**單字 rime `char.csv` 與 guotong 詞典（`dict_synonym`／`dict_antonym`）不在 git**——clone 後請先跑 `python scripts/bootstrap_data.py`（第 2 層）。

---

## Maintainer：重建詞條庫與近反義

產物均為本地／gitignore，**勿** commit。詳見 [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)。

```bash
pip install -r requirements-dev.txt
python scripts/bootstrap_data.py
# 全量重建詞條庫（lexicon + build-word-relations + bridge／manual；見 data/lexicon/sources.yaml）：
python -m ingest build-db
# 只重建靜態近反義關係（cilin + guotong + compound_ant）：
python -m ingest build-word-relations
python -m ingest report
```

`word_relations` 以較小 `word_id` 在前儲存無向邊；唯一鍵 `(word_id, related_id, relation_type)`。`build-word-relations` 於記憶體組裝後按 2000 列一批 bulk insert（衝突自動丟棄）。

可選近反義來源（預設關閉）見 `data/syn_ant/sources.yaml`。

### 官方資料 Release

再分發前核對 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。**勿**將大檔 commit 入 git。  
**分渠道發佈**（發佈主理／發佈補件角色）、**詞庫發佈** checklist 見 [docs/release.md](docs/release.md)（[ADR-0018](docs/adr/0018-split-channel-release.md)）。

| 資產 | 用途 |
|------|------|
| `lyrics.db` | 完整**詞條庫**（`words` + `word_relations`） |
| `canto-0243-portable.zip` | Windows 免安裝套件（內建 venv + `START.bat`） |
| `canto-0243-portable-macos-x86_64.tar.gz` | macOS 免安裝資料夾 + **`Canto-0243.command`**（Intel；現行渠道） |
| `canto-0243-portable-macos-arm64.tar.gz` | macOS 免安裝（Apple Silicon；過渡期暫不提供） |
| `words-lexicon.json` | **詞級標音**副件 |

```powershell
# Windows 全量（建置 + 上傳 Release）:
powershell -ExecutionPolicy Bypass -File scripts/release-windows-local.ps1 -Tag vX.Y.Z -Upload
```

```bash
# 發佈補件（現行：macOS 腳本；須 lyrics.db 對齊 Release；gh auth 須對 upstream 有 write）
git fetch origin && git checkout main && git merge origin/main
bash scripts/release-macos-local.sh --tag vX.Y.Z --test   # 本機 smoke（首次會下載建置用 CPython 至 .build-python/）
GH_REPO=bill-iu/Canto-0243 bash scripts/release-macos-local.sh --tag vX.Y.Z --arch x86_64 --upload --tar-only
```

手動取得建置用 Python：`bash scripts/fetch-macos-build-python.sh`（僅 x86_64；Apple CLT 內建 Python 不足以產出可搬移 venv）。詳見 [docs/release.md](docs/release.md)。

---

## 查詢語法速查

與 App「搜尋教學」可點擊例子一致。音節格位由左至右數第 1、2、3…格。

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

**標點等價**（查詢分派自動正規化）：全形 `？` 與 `?` 等價；全形 `～`／`！` 與 `~`／`!` 等價；`~~`／`!!` 與 `～～`／`！！` 及混合寫法（如 `~～`）等價。

### 缺字查詢（遮罩）

用 `?`／`_`／`%` 表該格任意字。首格字面可省略 `+`（`香??` 等同 `+香??`）。

| 輸入範例 | 說明 |
|----------|------|
| `香??` | 三字，第 1 格字面「香」 |
| `?你?` / `?+你?` | 三字，第 2 格字面「你」 |
| `_識_` | 三字，第 2 格字面「識」 |
| `3_` | 二字：第 1 格同碼 `3`，第 2 格任意 |
| `23?` | 三字：第 1–2 格碼 `23`，第 3 格任意 |
| `門0` | 二字：第 1 格字面「門」＋尾碼 `0`（normalize 為 `+門0`） |

### 加號錨（`+`）

`+` 連接**碼**同**錨字**，標明錨字喺邊一格。

| 寫法 | 該格約束 |
|------|----------|
| `錨字`（無 `=`） | 字面固定係錨字 |
| `錨字=` | 同錨字**韻母** |
| `+=錨字` | 同錨字**聲母** |

輸入 `*`／`＊` 等同 `+`（normalize 為 `+`）。

| 輸入範例 | 詞長 | 說明 |
|----------|------|------|
| `23+好` | 3 | 碼 `23` + 第 3 格字面「好」 |
| `23+好=` | 3 | 碼 `23` + 第 3 格同「好」韻 |
| `23+=好` | 3 | 碼 `23` + 第 3 格同「好」聲 |
| `2+好3` | 3 | 第 2 格字面「好」，首尾碼 `2`／`3` |
| `2+好=3` | 3 | 第 2 格同「好」韻，首尾碼 `2`／`3` |
| `+門0`（`門0`） | 2 | 第 1 格字面「門」+ 尾碼 `0` |
| `+門=0` | 2 | 第 1 格同「門」韻 + 尾碼 `0` |

> 二字 `23o`（末格韻母）≠ 三字 `23+o`（多一槽）；見下方粵拼錨。

### 韻／聲錨（`=`）

`字=` 比韻母；`=字` 比聲母。錨字唔一定要出現喺結果字面。

| 輸入範例 | 說明 |
|----------|------|
| `就=` | 單字，同「就」韻 |
| `?+就=` | 二字，尾格同「就」韻 |
| `?+港=?` | 三字，中格同「港」韻（`?港=?` 等價） |
| `=就` | 單字，同「就」聲 |
| `?=就` | 二字，尾格同「就」聲 |
| `香=?` / `+香=?` | 二字，首格同「香」韻 |

### 串列韻／聲錨

連續數字：每位一音節碼。`{碼}{字}=` 比韻；`{碼}={字}` 比聲。`=` 永遠喺參考字右側。

| 輸入範例 | 說明 |
|----------|------|
| `4困=` | 一字，同「困」韻 |
| `04困=` | 二字，第 2 格同「困」韻 |
| `23就=` | 二字，碼 `23` + 尾格同「就」韻 |
| `04困=49倒=` | 四字，第 2／4 格韻錨 |
| `04=困49=倒` | 四字，第 2／4 格聲錨 |
| `?3人=?` | 三字，中格碼 `3` + 尾格同「人」韻 |
| `?4困=4潦=9倒=` | 四字，第 1 格通配 + 其餘韻錨 |

**唔同整詞等號**：`04困=49倒=` 只約束錨格韻母；`0449窮困潦倒=` 要求四字**整詞**韻母 tuple 一致。

### 四字部分韻／聲錨

四字骨架內，`?` 標**邊一格唔限制**；其餘漢字格逐格比該字韻母或聲母（結果唔使同骨架逐字相等）。

| 輸入範例 | 說明 |
|----------|------|
| `窮?潦倒=` | 第 **2** 格任意；窮／潦／倒 各比韻 |
| `窮困?倒=` | 第 3 格任意 |
| `窮困潦=?` | 第 4 格任意 |
| `=窮?潦倒` | 第 2 格任意；窮／潦／倒 各比聲 |
| `=窮困?倒` | 第 3 格任意 |
| `=窮困潦?` | 第 4 格任意 |

### 前綴通配等號

首音節**完全**通配（聲、韻、碼皆不限），其餘音節逐格同參考模板。

| 輸入範例 | 說明 |
|----------|------|
| `?香港=` | 第 1 格任意，第 2–3 格同「香港」韻 |
| `?困潦倒=` | 第 1 格任意，第 2–4 格同「困潦倒」韻（須尾 `=`） |
| `?=困潦倒` | 第 1 格任意，第 2–4 格同「困潦倒」聲 |

### 通配碼錨

首格 `?` 通配 + 連續碼 + 尾參考字（韻）。加長一槽用 `+`。

| 輸入範例 | 說明 |
|----------|------|
| `?30人` | 三字，碼 `30` + 尾格同「人」韻 |
| `?30+人` | 四字，首格任意 + 碼 `30` + 尾格同「人」韻 |

### 粵拼錨

缺字族內用拉丁粵拼取代漢字參考字；**唔係**整段粵拼查詢。**近反義模式**唔收。

| 輸入範例 | 說明 |
|----------|------|
| `?+yut?`（`?yut?`） | 三字，中格韻母 `yut` |
| `?+syut?`（`?syut?`） | 三字，中格音節 `syut` |
| `?+hon`（`?hon`） | 二字，末格音節 `hon` |
| `3hon4` | 二字，碼 `34`，首格音節 `hon` |
| `3$漢4` | 同上（漢字音節錨 `$漢` ≡ `hon`） |
| `3?hon4` | 三字，中格音節 `hon` |
| `23o` | 二字，碼 `23`，末格韻母 `o` |
| `23+o` | 三字，碼 `23` + 末格韻母 `o`（比 `23o` 多一槽） |
| `3h4` | 二字，碼 `34`，首格聲母 `h` |
| `23ngo` | 二字，碼 `23`，末格音節 `ngo` |
| `23ei0` | 三字，碼 `230`，中格韻母 `ei` |

### 整詞等號／碼夾

| 輸入範例 | 說明 |
|----------|------|
| `香港=` | 二字，整詞同「香港」韻 |
| `大蛋糕=` | 三字，整詞同「大蛋糕」韻 |
| `34英皇=` | 五字，前碼 `34` + 整詞同「英皇」韻 |
| `=香港` | 二字，整詞同「香港」聲 |
| `2我=3` | 二字，碼 `23`，首格同「我」韻 |
| `2=我3` | 二字，碼 `23`，首格同「我」聲 |

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

### 同音節疊字（`$$`）

| 輸入範例 | 說明 |
|----------|------|
| `$$` | 二字同音節疊字（如慢慢、識食；聲調不限） |
| `33$$` | 33 同音＋同音節疊字 |
| `$$你` | 疊字，尾字同「你」同韻 |

### 同音異讀（`code/code`）

| 輸入範例 | 說明 |
|----------|------|
| `33/34` | 同字面兩讀音：左模板 `33`、右模板 `34`（如今晚） |
| `?3/?4` | 只約束第 2 字碼；`?` 通配 |

```http
GET /words/search/?q=你好&mode=m1
GET /words/search/?q=23就&mode=m1
GET /words/search/?q=23就=&mode=m1
GET /words/search/?q=04困=49倒=&mode=m1
GET /words/search/?q=?香港=&mode=m1
GET /words/search/?q=香港=&mode=m1
GET /words/search/?q=2=我3&mode=m1
GET /words/search/?q=nei%20hou&mode=m1
GET /words/search/?q=?syut?&mode=m1
GET /words/search/?q=23o&mode=m1
GET /words/search/?q=3hon4&mode=m1
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
├── frontend/               # index.html（查韻首屏；含關係補錄分頁）
├── portable/               # START.bat · START.sh · env.portable
├── data/                   # 見「資料來源」三層模型
├── ingest/                 # python -m ingest
├── scripts/                # bootstrap · build-portable · ingest
├── tests/
├── docs/                   # CONTRIBUTING · README.en · README.zh-Hans · release
├── main.py · start.sh      # 開發入口
├── README.md               # 繁中（GitHub 首頁）
├── LICENSE · THIRD_PARTY_NOTICES.md
├── CONTEXT.md · WORKLOG.md · AGENTS.md · skills-lock.json
└── requirements*.txt
```

### 資料來源與授權

再分發前請核對 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。收錄與排序見 [`CONTEXT.md`](CONTEXT.md) § 詞庫與排序。

| 層級 | 說明 | 例子 |
|------|------|------|
| **1 · 隨 repo** | clone 即有 | `data/essay/`、`data/lexicon/`、`data/syn_ant/`、bundled cilin／thesaurus |
| **2 · bootstrap** | `python scripts/bootstrap_data.py` | rime `char.csv`、guotong 詞典（近義／反義） |
| **3 · maintainer 自建** | gitignore；整包授權見 [LICENSE](LICENSE) | `lyrics.db`、詞級標音 JSON |

近義／反義靜態來源：`data/syn_ant/sources.yaml`（**cilin**、**guotong** `dict_antonym`、**compound_ant** 列表）。`python -m ingest build-db` 熱路徑跑 **`build-word-relations`**（唔再經 staging／逐批查重）。詳表見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

---

## 測試

目前 **565** 個 unittest。

```bash
python -m unittest discover -s tests -q
```

關鍵回歸：純漢字 strict code、wildcard、`mode=syn`、等號／碼夾、粵拼、粵拼錨、`$`／`$$`、`code/code`、`~~`／`!!` 複合詞。

---

## 依賴

| 層 | 檔案 | 用途 |
|----|------|------|
| Runtime | `requirements.txt` | FastAPI + SQLAlchemy + SQLite |
| Ingest / dev | `requirements-dev.txt` | ingest 與 legacy 腳本 |
| PostgreSQL（凍結） | `requirements-postgres.txt` | 實驗用 |

---

## Canto-0243 授權與使用

你可以使用本工具做任何你想做的事，包括協助粵語填詞、查韻、換字，以及作為**商業創作**（例如歌曲、劇本、已發表歌詞）嘅一部分——前提係遵守下方限制：

* **不可以**將本工具重新打包、轉售，或作為競爭性產品單獨發布。
* **不可以**將本工具提供為**付費 API**、訂閱或按量計費嘅查詢／推理服務（免費自架或免費公開存取另論，但仍須遵守署名等條款）。
* 任何公開發布嘅 fork、改進或衍生版本須**沿用同一授權**（或實質等同條款），並在合理顯眼位置保留 **Canto-0243** 名稱。若你營運公開網站、網頁 app 或 API（包括免費），須顯示例如「Powered by Canto-0243」並連結官方 repo。
* 若你營運**商業軟件**或**付費推理服務**，希望將本工具整合入產品，請先與版權人聯絡或於官方 repo 開 Issue 商議書面授權。

除上述條款外，本授權在實務上等同 [Creative Commons Attribution-NonCommercial-ShareAlike 4.0（CC BY-NC-SA 4.0）](https://creativecommons.org/licenses/by-nc-sa/4.0/) 加上附加限制。完整法律文本見 [`LICENSE`](LICENSE)。

請在任何未來 fork 或發布中保留 **Canto-0243** 名稱！

---

## 致謝與第三方授權

### 專案致謝

本專案喺作者幾乎零程式背景嘅起步階段，得益於 **[ivorhoulker](https://github.com/ivorhoulker)** 做我嘅Advisor：喺設計同實行上俾咗好多意見同指導，並且提出許多寶貴嘅修改建議。冇呢啲協助，**Canto-0243** 唔會出現。

亦要多謝 **「0243理論」發明人黃志華老師**，奠定粵語填詞數碼化嘅理論基礎。多謝 [0243.hk](https://0243.hk) 開發者 **Daniel Tam** 先生開發呢個網站，解決咗好多人嘅填詞問題，並啟發作者開發本工具。

### 資料與語料致謝

Canto-0243 整合多個開源詞典、語料與近反義資源。我們明確感謝以下團隊與專案（再分發前請閱讀各上游完整條款；授權總表見 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)）：

* **Rime 粵語（單字讀音 `char.csv`、essay 詞頻）**：來自 [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) 與 [rime/rime-cantonese](https://github.com/rime/rime-cantonese)，採用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。去畀佢哋一個 star！
* **詞林同義詞（Cilin）**：經 [yaleimeng/Final_word_Similarity](https://github.com/yaleimeng/Final_word_Similarity)／[liao961120/cilin](https://github.com/liao961120/cilin) 匯出，採用 **MIT** 授權。
* **國語辭典近義／反義（guotong）**：來自 [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary)（`dict_synonym.txt`、`dict_antonym.txt`），採用 [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE)；專案**反義詞主來源**。
* **words.hk 粵典詞表**：來自 [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/)，**公有領域**（致謝 [words.hk](https://words.hk/)）。
* **多字詞級標音上游**（maintainer 自建 `lyrics.db` 時）：[words.hk 粵典詞表](https://words.hk/faiman/analysis/wordslist/)（公有領域）、[開放詞典 · 粵語詞典](https://kaifangcidian.com/xiazai/)（[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)）、Rime 單字讀音與 maintainer curated（見 `data/lexicon/sources.yaml`）。

使用上述資料建構或再分發詞庫時，你同意遵守各自授權；部分來源含**非商業**或**署名**要求。可選近反義來源（如 COW）預設關閉，見 `data/syn_ant/sources.yaml`。

---

## 相關文件

| 文件 | 內容 |
|------|------|
| [`README.md`](README.md) | 本文件（繁體中文，GitHub 首頁） |
| [`docs/README.zh-Hans.md`](docs/README.zh-Hans.md) | 简体中文说明（书面语） |
| [`docs/README.en.md`](docs/README.en.md) | English documentation |
| [`LICENSE`](LICENSE) | Canto-0243 License（程式與詞條庫交付） |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | 第三方資料授權 |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | 貢獻與 PR · 源碼根目錄約定 |
| [`CONTEXT.md`](CONTEXT.md) | 領域詞彙表 |
| [`WORKLOG.md`](WORKLOG.md) | 變更紀錄 |
| [`AGENTS.md`](AGENTS.md) | Agent 協作指引 |

---

**最後更新**：2026-07-02（guotong 反義、build-word-relations 重構）
