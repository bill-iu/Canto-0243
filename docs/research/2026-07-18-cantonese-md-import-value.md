# daimaruhk/Cantonese.md 引入價值與可能性

**日期**：2026-07-18  
**對象專案**：ICE-U-code/Canto-0243（離線粵語填詞查韻；近反義經靜態詞林埠 + `word_relations`）  
**主要 URL**：[https://github.com/daimaruhk/Cantonese.md](https://github.com/daimaruhk/Cantonese.md)  
**線上站**：[https://cantonese.md/](https://cantonese.md/)  
**結論摘要**：

| 引入對象 | 裁決 |
|----------|------|
| **Cantonese.md 本體**（Next.js 站／UI／整站 fork） | **no** — 產品係歇後語瀏覽站，唔係 0243 查韻工具 |
| **歇後語正文／文化解說全文** 入 App | **no** — 超出填詞查韻範圍；體積／UI 成本與核心無關 |
| **`term`／`answer` 字面 + 粵拼** 作詞庫 SSOT 源 | **yes-with-conditions（低優先）** — 授權極鬆（**CC0**）、有粵拼、N 極小（~241 條）；須先量度「庫內缺字面／缺讀音」增量，增量不足則 **YAGNI** |
| **term↔answer 當近義／反義邊** | **no** — 歇後語前後截**唔係**同義層近義，亦唔係穩定 context-free 反義；硬灌會污染近反義池 |
| **作 LLM 訓練集／文化知識庫** | **超出 Canto 產品** — 可個人／研究用途，唔經本倉 ingest |

---

## 1. Question / scope

評估「引入 Cantonese.md」對 Canto-0243 的產品價值與技術／授權可行性。

**範圍內**：repo 角色、資料形狀、規模、授權、與現有詞庫／近反義閘的適配、可行路徑。  
**範圍外**：實際匯入、改 Canto 程式、整站 fork、律師意見。

---

## 2. 專案是什麼

官方自述：

> open-source initiative… preserving Cantonese… **human-supervised** dataset… starting with **Cantonese idioms (歇後語)**… modern UI… **statically generated**.

| 層 | 內容 |
|----|------|
| 產品 | 靜態生成的歇後語／口語文化條目瀏覽站（Next.js） |
| 資料 | `src/contents/**/*.md`；frontmatter + 正文（字面意思、引申、例子） |
| 現況規模（2026-07-18 `main` tree） | **`src/contents/idioms/` 共 241 個 `.md`**（僅 idioms 子目錄；未見 slangs 等已落地大批） |
| 願景 | 由歇後語擴到更多粵語知識；明確面向 **AI／LLM 訓練資料** 與文化保存 |

### 2.1 條目形狀（典型 frontmatter）

```yaml
id: iRNL7TmVZbOW
term: 阿茂整餅
termJyutping: aa3 mau6 zing2 beng2
answer: 冇嗰樣整嗰樣
answerJyutping: mou5 go2 joeng6 zing2 go2 joeng6
explanation: 用嚟形容人「多此一舉」…
```

- **粵拼規範**（style guide）：Jyutping only；小寫音節 + 調 1–6；空白分隔（例：`aa3 mau6 zing2 beng2`）。與 Canto 常用「無空白拼接」或詞庫 canonical 形可能需 normalize（去空白／校驗）。
- 正文另有長篇文化敘事，**唔**適合當 `words` 列欄位。

抽樣（本機 `lyrics.db` 字面命中）：`阿茂整餅`、`冇嗰樣整嗰樣`、`一個酸梅兩個核`、`光棍佬教仔`、`公用電話` 等 **已在庫**（count≥1）。說明大量「名句」可能已由 rime／words.hk／kaifang 等覆蓋；**未做全量 241 交集**，正式決策前應跑一次差分。

---

## 3. 授權

| 層 | 條款 | 對 Canto |
|----|------|----------|
| 程式（站／工具） | **MIT** | 可參考；唔需要 fork 站 |
| 資料（`src/contents/` Markdown） | **CC0 1.0**（`LICENSE-DATA`） | **極適合**再分發、改格式、過濾、嵌入；NOTICE 標示來源即可（禮貌標示 repo／站） |

與 moedict／教育部 BY-ND **對比**：Cantonese.md **資料閘幾乎無摩擦**，問題在**內容類型與規模**，唔係授權。

AI 貢獻政策：鼓勵 AI 起草，但要求人工審核、禁「AI slop」bulk；對下游意味著品質意圖高，但仍應自行抽樣校粵拼／字面。

---

## 4. 與 Canto-0243 產品面適配

| Canto 硬需求 | Cantonese.md |
|--------------|--------------|
| 字面 ∈ 詞庫 + 粵拼 + **0243 碼** | 有字面 + 粵拼；**無 0243**（可由粵拼重算） |
| 大規模收錄（十數萬詞） | **~241 歇後語條**（term+answer 至多 ~482 字面，大量重疊） |
| 近反義：同詞性、同義層、context-free 可替換 | term／answer 係**謎面—謎底**文化配對，**非**近義／反義 |
| 離線 SQLite | 可（靜態 MD 抽出即可） |
| 押韻／wildcard／句格 | 無直接增益（只係多幾個長字面若缺庫） |

`CONTEXT` 契約：

- **詞條 SSOT** 要 (字面, 粵拼)；可走 `sources.yaml` 新源。  
- **專案自建近義／反義** 要求自然近反義；歇後語配對**唔合格**。  
- 有效字面最長 12：多數歇後語截句落在範圍內；過長 answer 須截斷或拒收。

---

## 5. 價值場景

### 5.1 詞庫補洞（字面 + 粵拼）

| 項 | 評估 |
|----|------|
| 授權 | **強**（CC0） |
| 粵語本位 | **強**（粵文 + Jyutping） |
| 增量 | **疑似小**（抽樣已在庫；全量未測） |
| 工程 | 低～中：MD frontmatter → TSV → lexicon source／curated |
| 風險 | 粵拼空白格式、異體字、與現有讀音衝突 |

→ **條件式有價值**；必須先：

```text
extract (term, termJyutping), (answer, answerJyutping)
→ normalize jyutping
→ intersect vs lyrics.db / build membership
→ report: missing_literal | missing_reading | conflict
```

若 `missing_*` 極少 → **YAGNI，唔引入**。

### 5.2 近反義池

| 候選建模 | 判定 |
|----------|------|
| `syn`（阿茂整餅 ≈ 冇嗰樣整嗰樣） | **錯**；語用不穩定替換 |
| `ant` | **錯** |
| `semantic_related` | 語意上「相關」但產品近反義模式是否展示、排序如何，**未有歇後語產品需求**；開新 relation kind 屬範圍膨脹 |

→ **主線 no**。

### 5.3 產品功能（App 內歇後語百科）

- 與「填詞查韻」目標正交。  
- 要做應是**另一產品**或外鏈 cantonese.md，唔塞進 Canto 結果列表。  
→ **no**。

### 5.4 維護者審稿／文化對照

- 人手開站查歇後語：零成本。  
→ **允許，唔寫進管線**。

---

## 6. 可行性矩陣

| 方案 | 技術 | 授權 | 產品增益 | 建議 |
|------|------|------|----------|------|
| P0 人手瀏覽 cantonese.md | 無 | 瀏覽 | 審稿 | **可** |
| P1 抽出 term／answer + 粵拼；量度庫差 | 低 | CC0 | 未知至小 | **可選探針**；不足則停 |
| P2 差分通過後作 `sources.yaml` 小源或 curated 補讀 | 中 | CC0 | 小 | **僅當 P1 顯示缺口** |
| P3 term↔answer 入 syn／ant | 低 | CC0 | **負**（污染） | **禁止** |
| P4 全文 explanation 入 DB／UI | 中 | CC0 | 離題 | **不做** |
| P5 fork Next 站 | 高 | MIT | 錯產品 | **不做** |
| P6 submodule 常駐同步 | 中 | CC0 | 維護成本 > 收益 | **不做**（P2 可 pin 版本 tar） |

---

## 7. Verdict

### **整體：no-for-mainline；詞庫補洞僅條件式、低優先**

1. **唔引入** Cantonese.md 作為產品依賴、UI、近反義源、或整包文化正文。  
2. **授權上可**取 `src/contents/` 資料；**價值上**現階段只有「極小規模粵拼字面」一條窄路，且抽樣暗示**庫已覆蓋**。  
3. 若將來要做：先 **P1 差分報告**，再決定是否 P2；**永遠唔**把歇後語配對當 syn／ant。  
4. 相對現有源（rime-cantonese-upstream、words.hk、kaifang、project_syn／ant）：Cantonese.md **唔取代任何主源**，最多係 niche 補丁。

### 什麼時候會改判「值得做 P2」

- 全量 241 條中，**缺字面或缺合格粵拼讀音** 達可感比例（例如數十條以上，且填詞高頻）；且  
- 維護者願意為 CC0 小源付 NOTICE + rebuild 成本。

否則維持 **YAGNI**。

---

## 8. 建議下一步（可選；非必須）

1. **預設：唔開工。**  
2. 若好奇增量：一次性腳本對 `src/contents/idioms/*.md` 跑 membership 報告（唔 commit 源資料）。  
3. 報告結論寫回本檔「觀測補記」後關閉或升級 P2。

---

## 9. 參考

| 項目 | URL |
|------|-----|
| 源碼 | https://github.com/daimaruhk/Cantonese.md |
| 站 | https://cantonese.md/ |
| 資料授權 | https://github.com/daimaruhk/Cantonese.md/blob/main/LICENSE-DATA |
| 程式授權 | https://github.com/daimaruhk/Cantonese.md/blob/main/LICENSE |
| 貢獻／AI 政策 | CONTRIBUTING.md |
| Canto 詞庫源清單 | `data/lexicon/sources.yaml` |

---

*觀測基準日：2026-07-18。內容檔計數：GitHub recursive tree，`src/contents/idioms/*.md` = 241。本機 membership 抽樣 5 條皆已在 `lyrics.db`。非法律意見。*
