# g0v/moedict.tw 引入價值與可能性

**日期**：2026-07-18  
**狀態**：**已放棄引入**（維護者 2026-07-18 確認；唔開依賴、唔匯入、唔跟進 P1 增量度量，除非另開議題）  
**對象專案**：ICE-U-code/Canto-0243（離線粵語填詞查韻；近反義經靜態詞林埠 + `word_relations`）  
**主要 URL**：[https://github.com/g0v/moedict.tw](https://github.com/g0v/moedict.tw)  
**結論摘要**：

| 引入對象 | 裁決 |
|----------|------|
| **moedict.tw 本體**（前端／Worker／線上 API／R2 字典包） | **no — 已放棄**；唔當 runtime 依賴或 fork 產品殼 |
| **經 moedict 生態取教育部《修訂本》相似詞／相反詞欄** | **研究曾判 yes-with-conditions；產品線已放棄** — 唔為 Canto 開 MOE／moedict 匯入管線 |
| **台語／客語／兩岸詞典包** | **no**（主線） |

**關聯報告**（已裁決、本篇唔重複展開）：

- [`2026-07-14-moe-revised-dict-antonym-import.md`](./2026-07-14-moe-revised-dict-antonym-import.md) — 教育部修訂本相反詞／相似詞：**yes-with-conditions**（CC BY-ND）
- [`2026-07-14-wikidata-opposite-of-zh-labels.md`](./2026-07-14-wikidata-opposite-of-zh-labels.md) — 授權對照（CC0 ≫ BY-ND）
- `CONTEXT.md` — **專案自建近義起草** _Avoid_：`COW／MOE 當自建近義源`；len4 反義計劃已否決「MOE 相反詞」當 campaign 源

---

## 1. Question / scope

評估「引入 [g0v/moedict.tw](https://github.com/g0v/moedict.tw)」對 Canto-0243 的**產品價值**與**技術／授權可能性**。常見混淆點：

1. 把 **moedict.tw** 當成「一部可直接灌入嘅詞典資料庫」；
2. 把 **線上 API**（`https://www.moedict.tw/a/…`）當成可嵌入離線 App 的主源；
3. 把 **g0v 前端殼** 與 **教育部辭典本文** 的授權混為一談。

**範圍內**：repo 角色、生態分工、授權分層、可取資料種類、與現有 guotong／cilin／project_syn·ant 的重疊／增量想像、可行性路徑。  
**範圍外**：實際下載匯入、改 Canto 程式碼、律師意見。

---

## 2. 生態地圖（必須分清）

`moedict.tw` **唔係**資料原廠，而係萌典產品線的**新前端全端**：

| 倉庫 | 角色 | 授權（程式 vs 資料） | 對 Canto 的直接意義 |
|------|------|----------------------|---------------------|
| **[g0v/moedict.tw](https://github.com/g0v/moedict.tw)** | React + TS + Vite；Cloudflare Workers；R2 上靜態資源＋字典 pack；全文 search-index | 程式 **CC0**；字典資料**唔** CC0 | **產品殼**；部署／R2／索引流程；**唔**提供粵拼／0243 |
| [g0v/moedict-webkit](https://github.com/g0v/moedict-webkit) | 舊站 moedict.org 靜態前端（**frozen**）；API 說明仍有用 | 程式 CC0；資料同下 | API 形狀文件；pack 產生已遷出 |
| [g0v/moedict-data](https://github.com/g0v/moedict-data) | 《重編國語辭典修訂本》→ 機器可讀 JSON 等 | **本文教育部 CC BY-ND 3.0 TW**；格式轉換層（kcwu）**CC0** | 真正「華語條目＋相似詞／相反詞」鏡像候選 |
| [g0v/moedict-process](https://github.com/g0v/moedict-process) | XLSX→JSON→pack；`definitions.antonyms`／`synonyms` | 同上（資料 BY-ND） | **欄位映射／管線參考**；唔宜當授權更鬆的上游 |

`moedict.tw` README 自己寫：若要跟教育部同步，應依序查 **moedict-data → moedict-process → moedict-webkit**；本 repo 負責的是 **search-index 與 R2 上載**，唔係辭典原檔生成。

線上站：[https://www.moedict.tw/](https://www.moedict.tw/) — 約 **16 萬華語**、**2 萬台語**、**1.4 萬客語**條目；國語注音／拼音；支援萬用字元與連詞跳轉。

### 2.1 語系代碼（moedict 慣例）

| 路徑前綴 | 語系 | Canto 主線是否需要 |
|----------|------|-------------------|
| `/a/` | 華語（重編國語辭典修訂本） | 僅字面近反義／lemma 參考時可能 |
| `/t/` | 台語 | 否 |
| `/h/` | 客語 | 否 |
| `/c/` | 兩岸詞典 | 否（簡繁對照另有用途，唔係 0243 核心） |
| `/raw/` `/uni/` `/pua/` | 同一華語 JSON 的編碼變體 | 開發調試用 |

---

## 3. 授權分層（紅線）

### 3.1 moedict.tw 程式

- 根目錄 **LICENSE = CC0 1.0**（專案自行撰寫的程式、腳本、整理流程）。
- **可以**讀其程式當參考、fork UI 實驗；**唔等於**可以當字典本文的授權。

### 3.2 字典本文（華語修訂本）

- **CC BY-ND 3.0 TW**（姓名標示－禁止改作）。
- 允許重製、散布、傳輸（含商用，依公眾授權下載包路徑），**不得修改著作本文**。
- g0v/moedict-data 引教育部解釋：改作限制標的係**文字資料本身**，**不限制格式轉換及後續應用**。
- 詳細合規條件、下載包欄位、「唔好 scrape 官網 FAQ」、與 `project_ant` 隔離等，**以** [`2026-07-14-moe-revised-dict-antonym-import.md`](./2026-07-14-moe-revised-dict-antonym-import.md) **為準**。

### 3.3 對 Canto 既有閘的含義

| 做法 | 可否 |
|------|------|
| 離線打包「抽出且未改寫」的相似詞／相反詞欄 + NOTICE BY-ND | 條件式可以（見 MOE 報告） |
| 把 MOE 字串 LLM 潤飾後寫入 `project_synonyms`／`project_antonyms` | **否**（CONTEXT 明文避免；ND） |
| Runtime 每次查詞打 `www.moedict.tw` API | **否**（離線產品契約；CORS 站點亦唔係 SSOT） |
| 把 moedict 整站當「第二個 Canto UI」合併 | **否**（產品目標完全不同） |

---

## 4. 技術面：moedict.tw 提供什麼、缺什麼

### 4.1 有

- **成熟查詞 UX**：自動完成、部首／分類、連詞、多語切換（華／台／客／兩岸）。
- **公開 JSON API**（CORS 開在 `www.moedict.tw`）：`/a/{詞}.json`、`/uni/{詞}` 等；heteronym 結構含注音、拼音、義項、例句、部分翻譯。
- **社群已處理格式**：pack、`search-index`、StarDict／Kindle 匯出腳本（仍受上游資料授權約束）。
- **相似詞／相反詞**（在**原始資料／process 產物**層；官方 XLSX 有「相似詞」「相反詞」欄；觀測約 **8.5k+** 列有相反詞 — 見 MOE 報告）。

### 4.2 沒有（相對 Canto）

| Canto 硬需求 | moedict |
|--------------|---------|
| 粵拼（Jyutping） | 無（國語注音／拼音；台語羅馬字、客語拼寫屬其他語） |
| **394052／0243 碼** | 無 |
| 離線 SQLite 詞庫契約／詞庫發佈閘 | 無（R2 + Worker 線上模型） |
| 填詞向「字面 ∈ 粵語詞庫」membership | 需另做交集；MOE 獨有詞大量進唔到結果 |
| 近反義池 ranking／專案自建 campaign | 無；且不能當 project 源 |
| 押韻／wildcard／等號韻 | 無 |

抽樣（`/a/大.json`、`/a/好.json`）：結構係**辭典釋義**為主；唔係「同義詞庫邊列表」。近反義要從 **XLSX 欄位或 process 後的 synonyms/antonyms** 抽，唔係假定每個 API 條目都有乾淨 graph edge。

### 4.3 若「接 API」的架構成本

- 破壞 **portable 離線** 預設。
- 更新節奏、可用性、CORS、造字 PUA／字型（`MOEDICT.woff`）變成運維面。
- 與現有 `lyrics.db` 雙源一致性難做。
- **YAGNI**：Canto 已有字面 lookup + 近反義模式；唔需要第二個線上辭典殼。

---

## 5. 產品價值評估（分場景）

### 5.1 場景 A — 補近義／反義覆蓋（最常被期待）

| 項 | 評估 |
|----|------|
| 內容質 | 教育部辭典品質高於大量雜訊 upstream；義項／多音需保留（「來往」「自然」等） |
| 相對 guotong | **同屬國語字面反義族**；未量度增量前**唔知**是否值得 BY-ND 合規成本 |
| 相對 project_syn／ant | campaign 已大規模補「過稀」頭；MOE 適合**並存只讀源**，**唔**進自建權威 |
| 粵語填詞體感 | 只對「字面已在庫」的頭有效；口語粵語反義習慣未必對齊國語書面 |

→ **有條件價值**；路徑應走 **官方 XLSX 抽出**（MOE 報告），**唔**綁 moedict.tw。

### 5.2 場景 B — 補詞庫字面／釋義

- 16 萬華語條目 vs Canto 以粵語標音詞庫為核：大量國語專名／書面詞要嘛已有、要嘛缺粵拼而**唔能直接入庫**。
- 釋義全文 BY-ND：即使「後續應用」允許，**整包釋義進 App** 的 NOTICE／UI 成本高，且**唔解決押韻**。
- → **低優先／主線 no**。

### 5.3 場景 C — 台語／客語

- 對「粵語填詞」產品**錯語種**。
- 除非另開「跨華語族語言」產品線，否則 **no**。

### 5.4 場景 D — UI／搜尋 UX 借鏡

- 萬用字元、連詞、部首瀏覽可當**靈感**（CC0 程式可讀）。
- Canto 已有 query 模式體系（0243、mask、hybrid、relation…）；**唔**值得 fork moedict.tw 前端棧（Vite+CF 與現有 portable／PWA 分叉）。
- → **參考 only，唔引入依賴**。

### 5.5 場景 E — 開發期人工查證

- 維護者用瀏覽器開 moedict 核對國語義項／反義：**零整合成本、高實用**。
- → **建議維持「人肉工具」**，唔寫進 ingest。

---

## 6. 可行性矩陣

| 方案 | 技術難度 | 授權 | 離線 | 產品增益 | 建議 |
|------|----------|------|------|----------|------|
| P0 人肉查 moedict.tw／官網 | 無 | 瀏覽 | n/a | 審稿輔助 | **做** |
| P1 官方 XLSX 抽相似詞／相反詞 → 獨立 source + NOTICE | 中 | BY-ND 條件式 | 可 | 視與 guotong 增量 | **可選**（見 MOE 報告） |
| P2 用 moedict-process 欄位映射作腳本參考 | 低 | 同上 | 可 | 加速 P1 | **可選** |
| P3 打包 moedict pack／R2 當 runtime 字典 | 高 | BY-ND + 體積 | 差／大 | 低（無粵拼） | **不做** |
| P4 runtime 打 moedict API | 低～中 | 同上 + 服務條款風險 | **否** | 低 | **不做** |
| P5 fork moedict.tw 當 Canto UI | 極高 | 程式 CC0／資料 ND | 須重做 | 錯產品 | **不做** |
| P6 MOE 當 project_syn／ant 生成源 | 中 | **違 ND／違 CONTEXT** | — | — | **禁止** |

---

## 7. Verdict

### 維護者終局（2026-07-18）：**放棄引入**

- 唔引入 moedict.tw（依賴、submodule、runtime API、R2 pack、fork UI）。  
- 唔為 Canto 開教育部／moedict 相似詞／相反詞匯入管線（P1–P6 全停）。  
- 人手瀏覽 moedict.tw 作審稿對照：**允許**，但唔寫進 ingest／SSOT。  
- 下文 §7.1–7.2 保留研究時點分析；**唔**再當待辦。

### 7.1 對「引入 https://github.com/g0v/moedict.tw」本身（研究時點）

**no**（其後升級為**已放棄**）。

理由濃縮：

1. **角色錯位**：佢係萌典**網站／Worker 產品**，唔係 Canto 需要的粵語碼位詞庫或近反義 SSOT。  
2. **資料唔在該 repo 主責**：真正有用的華語近反義欄在 **教育部下載包／moedict-data／process**；已有獨立研究裁決。  
3. **線上／R2 模型** 與 Canto **離線 SQLite** 契約衝突。  
4. **無粵拼／0243**；台客語包對主線無增益。  
5. 授權上即便程式 CC0，**字典本文 BY-ND** 仍限制「當自建源／改作後再分發」。

### 7.2 對「經萌典生態用教育部資料補近反義」（研究時點；產品已放棄）

研究曾判 **yes-with-conditions**（詳見 MOE 報告）。**產品線已決定唔做**，故唔開增量度量、format-only TSV、或 `moe_revised` source。若將來重開，須新議題 + 重審授權與 vs guotong 增量。

---

## 8. 建議下一步

**無。** 議題關閉。唔跟進 §6 可行性表中任何「可選／可選做」項。

---

## 9. 參考連結

| 項目 | URL |
|------|-----|
| moedict.tw 源碼 | https://github.com/g0v/moedict.tw |
| 線上站 | https://www.moedict.tw/ |
| 舊前端／API 說明 | https://github.com/g0v/moedict-webkit |
| 資料鏡像 | https://github.com/g0v/moedict-data |
| 處理管線 | https://github.com/g0v/moedict-process |
| 教育部公眾授權／下載 | https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/ |
| 本倉 MOE 反義研究 | [`2026-07-14-moe-revised-dict-antonym-import.md`](./2026-07-14-moe-revised-dict-antonym-import.md) |

---

*觀測基準日：2026-07-18。API 抽樣：`/a/大.json`、`/a/好.json`。本文件非法律意見。*
