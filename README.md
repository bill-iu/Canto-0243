# Canto-0243

<p align="center">
  <b>繁體中文</b> · <a href="docs/README.zh-Hans.md">简体中文</a> · <a href="docs/README.en.md">English</a>
</p>

填粵語歌詞，通常一係就「唔知有咩字」，一係就要喺**同音、押韻、近義**之間快速換字，又要對準 0243 與粵拼讀音。傳統做法係喺詞典、韻書、近義表之間搵嚟搵去，手動試「呢個位可唔可以換另一個字」——慢，而且容易漏咗好多可以用嘅字。[0243.hk](https://0243.hk) 已經算係近年最好用嘅粵語填詞查找網站，但係偶爾都會 502 Bad Gateway 上唔到；或者喺搵字嘅時候無限輪迴 load 唔到；又或者你想搵某個字但係佢冇嗰個功能——呢啲時候就會拖慢你嘅進度。

**Canto-0243**（**ONE·搵·韻**）係我用幾個唔同AI AGENT(Cursor, Codex, Grok Build, Github Copilot）開發嘅一個離線粵語填詞查找工作台：用 **394052／02493 數字碼**、**粵拼**、**韻母／聲母規則**與 **近義／反義關係**，喺幾秒內列出符合條件嘅**詞條**。頂欄 **0243搜尋模式** 有三檔：**0243模式**（鬆）、**02493模式**（緊）、**394052模式**（矩陣，三聲 `4`／五聲 `5` 分明）。例如打 `23就` 搵同調又同「就」同韻嘅尾字；打 `香港=` 搵同「香港」同韻嘅候選詞；打 `ZP` 會自動切換 394052模式做平仄串列；打 `~開心` 或切換**近反義模式**搵近義/反義詞；打 `~~`／`!!` 搵填詞常用嘅二字近義／反義複合詞。套件解壓即用，所有詞庫與近反義資料都儲存喺本地環境，唔使連上網。

**授權**：整包（程式、`lyrics.db`、`words-lexicon.json`）依 [Canto-0243 License](LICENSE)（CC BY-NC-SA 4.0 + 附加條款；**開源**）。第三方上游資料見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。  
**技術棧**：FastAPI · SQLAlchemy · SQLite（離線單機）· PWA 前端（Service Worker / Web App Manifest；Vite + 純 HTML/JS，離線資料庫以 OPFS / wa-sqlite 提供）  
**領域詞彙**：見 [`CONTEXT.md`](CONTEXT.md) · 貢獻指南 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)

---

## 最新版本

<!-- version:zh-Hant -->
目前版本：**v1.0.6**
<!-- /version:zh-Hant -->

<!-- words-count:zh-Hant -->
目前總詞條列數：**468,438**（`lyrics.db` · `words` 表）
<!-- /words-count:zh-Hant -->

**立即開始使用（兩種方式，同等重要）**

**Canto-0243 手機版**（瀏覽器直接開啟，無需安裝，支援「加到主畫面」，完全離線）  
👉 https://bill-iu.github.io/Canto-0243/

**離線portable版本**（Windows / macOS 免安裝，解壓即用）  
下載最新版：[canto-0243-portable.zip](https://github.com/bill-iu/Canto-0243/releases) / macOS tar  
完整 Releases 與詞庫檔請到 [GitHub Releases](https://github.com/bill-iu/Canto-0243/releases)

問題與建議歡迎 [GitHub Issues](https://github.com/bill-iu/Canto-0243/issues)。

---

## 功能

* **0243搜尋三檔**：**0243模式** `mode=m1`（基本四聲）· **02493模式** `mode=m2`（分清廣東話一聲和二聲）· **394052模式** `mode=m3`（分清廣東話六聲）。
* **多種查詢語法**：純漢字 · 純數字 · **粵拼查詢** · **平仄串列**（`PZ`／`ZP`，自動切 m3）· **加號錨**（`23+好=`）· **韻／聲錨**（`就=`）· **串列韻／聲錨** · **四字部分韻／聲錨**（`窮?潦倒=`）· **前綴通配等號** · 整詞等號／碼夾。
* **近反義**：**近反義模式** `mode=syn` 全欄 UI（不收粵拼）；或在 0243搜尋三檔下 `~詞`／`!詞`、反義複合 `!!`、近義複合 `~~`（會記住離開近反義前嘅搜尋檔）。

---

## 快速開始

**選一種開始使用**：

- **Canto-0243 手機版**：直接開啟 https://bill-iu.github.io/Canto-0243/ ，加到主畫面後完全離線可用。頂欄有「搜尋教學」。

- **離線portable版本**：從 [Releases](https://github.com/bill-iu/Canto-0243/releases) 下載解壓。Windows 雙擊 `Canto-0243.exe`（或 `START.bat`）；macOS 雙擊 `Canto-0243.command`。

開發者 clone 需準備 `lyrics.db`（詳見 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)）。

---

## 常用語法範例

| 輸入範例 | 說明 |
|----------|------|
| `就` | 查呢個字嘅所有讀音 |
| `你好` | 查呢個詞語 |
| `23` | 找同音字（0243模式） |
| `45` | 三／五聲分明（394052模式） |
| `PZ` | 平仄串列 |
| `就=` | 同「就」韻 |
| `23就` | 碼 + 尾字同韻 |
| `香??` | 缺字查詢 |
| `香港=` | 整詞同韻 |
| `?+就=` | 尾格同韻 |
| `~開心` | 近義詞 |
| `!!` / `~~` | 反義／近義複合詞 |

完整例子與所有語法，請在 App 內點擊頂欄「搜尋教學」查看。

---

## 維護者提示

詞庫重建、發佈等詳見 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) 及 [`docs/release.md`](docs/release.md)。

---

## 關於開發者

**Bill IU（姚程馭）** — 演員，粵語音樂劇填詞人，超級業餘的程式設計師。

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
* **words.hk 粵典詞表**：來自 [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/)，採用**非商業開放授權**（詳見 [words.hk /hoifong](https://words.hk/base/hoifong/)）。
* **多字詞級標音上游**（maintainer 自建 `lyrics.db` 時）：[words.hk 粵典詞表](https://words.hk/faiman/analysis/wordslist/)（非商業開放授權）、[開放詞典 · 粵語詞典](https://kaifangcidian.com/xiazai/)（[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)）、Rime 粵語詞典補缺來源（[CC BY 4.0](https://github.com/rime/rime-cantonese/blob/main/LICENSE-CC-BY)）、[HSK 3.0 word list](https://github.com/elkmovie/hsk30)（MIT）以及 maintainer curated 詞庫來源。

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

**最後更新**：2026-07-08（v1.0.6：394052 詞庫碼、三檔搜尋模式與搜尋教學更新）
