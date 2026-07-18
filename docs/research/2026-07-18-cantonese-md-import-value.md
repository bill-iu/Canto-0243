# daimaruhk/Cantonese.md 引入價值與可能性

**日期**：2026-07-18  
**對象專案**：ICE-U-code/Canto-0243（離線粵語填詞查韻；詞庫字面＋粵拼＋0243；近反義另線）  
**主要 URL**：[https://github.com/daimaruhk/Cantonese.md](https://github.com/daimaruhk/Cantonese.md)  
**線上站**：[https://cantonese.md/](https://cantonese.md/)  
**評估軸**：**唔限近反義** — 主問係「詞庫未擁有字面」是否夠多而值得引入字面＋粵拼。

**結論摘要**：

| 引入對象 | 裁決 |
|----------|------|
| **Cantonese.md 本體**（Next.js 站／UI／整站 fork） | **no** |
| **歇後語正文／文化解說全文** 入 App | **no** |
| **`term`／`answer` 字面 + 粵拼** 作詞庫源 | **yes-with-conditions** — 見 §2.2 差分：**481** 唯一字面中 **197 缺庫（~41%）**、len≤12 可入約 **196**；授權 **CC0**；絕對量中小但**相對源本體缺口大**，值得作**可選 lexicon 小源**，唔當主源 |
| **term↔answer 當近義／反義邊** | **no**（本評估唔靠呢條；硬灌仍禁） |
| **缺讀音校正**（字面已在庫、粵拼唔同） | **可選抽樣** — 差分 **29** 側；可餵勘誤／curated，唔自動蓋寫 |

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

### 2.2 全量 membership 差分（本機 `lyrics.db`，2026-07-18）

腳本：`scripts/research/cantonese_md_membership.py`  
產物：`docs/research/2026-07-18-cantonese-md-membership.json`  
源：GitHub `main` zip → `src/contents/**/*.md`（**241** 條歇後語）。

| 指標 | 數值 |
|------|------|
| 條目 | 241 |
| 唯一字面（term∪answer） | **481** |
| 已在詞庫字面集 | **284**（~59%） |
| **缺字面** | **197**（~41%） |
| 缺字面且 len 1–12（有效字面契約內） | **196** |
| 缺字面且 len >12 | 1（例：超長 answer，invalid／拒收） |
| 側檢查（term+answer 各計一側，482 側） | ok **256**；缺字面 **196**；字面在庫但粵拼唔匹配 **29**；invalid **1** |
| 本庫字面總數（對照） | ~156k distinct |

**解讀（對齊「有大量未擁有字面先考慮引入」）**：

1. **相對源本體**：近半字面本庫冇 → **算「大量」缺口**，唔係可忽略抽樣噪音。  
2. **絕對規模**：~200 字面，對全庫係小補丁；**唔**改變主源（rime／words.hk／kaifang）格局。  
3. **粵拼帶貨**：缺字面側幾乎都有 `termJyutping`／`answerJyutping` → 可直入 **(字面, 粵拼)** 重建，再算 0243。  
4. **早期 5 條抽樣全中庫** 有倖存者偏差；**以全量為準**。  
5. **29 缺讀音**：字面已在、Cantonese.md 粵拼與庫內列唔一致 — 可作**人工勘誤候選**，禁止無審 bulk 蓋寫。

缺字面例（len≤12）：`一隻筷子食豆腐`、`搞爛曬`、`三元宮土地`、`上山捉蟹`、`二叔公割禾`、`冇檳榔嚼唔出汁`、`問和尚借梳`…（全表見 JSON）。

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
| 大規模收錄（十數萬詞） | 源僅 **~241 條**；唯一字面 **481**，其中本庫缺 **~197**（§2.2） |
| 近反義：同詞性、同義層、context-free 可替換 | term／answer 係**謎面—謎底**；**本評估唔靠近反義決定是否引入** |
| 離線 SQLite | 可（靜態 MD 抽出即可） |
| 押韻／wildcard／句格 | 無直接增益（只係多幾個長字面若缺庫） |

`CONTEXT` 契約：

- **詞條 SSOT** 要 (字面, 粵拼)；可走 `sources.yaml` 新源。  
- **專案自建近義／反義** 要求自然近反義；歇後語配對**唔合格**。  
- 有效字面最長 12：多數歇後語截句落在範圍內；過長 answer 須截斷或拒收。

---

## 5. 價值場景

### 5.1 詞庫補洞（字面 + 粵拼）— **主評估軸**

| 項 | 評估 |
|----|------|
| 授權 | **強**（CC0） |
| 粵語本位 | **強**（粵文 + Jyutping） |
| 增量 | **相對源大（~41% 缺字面）／絕對中小（~196）** — §2.2 |
| 工程 | 低～中：MD frontmatter → 正規化粵拼 → lexicon source 或 curated |
| 風險 | 粵拼空白、異體、粗口／俚語收錄政策、與現讀衝突 |

→ **值得考慮引入作可選詞庫小源**（只補缺字面＋帶來嘅粵拼；唔灌全文、唔灌近反義）。

建議管線（若做）：

```text
extract (term, termJyutping), (answer, answerJyutping)
→ normalize jyutping（去空白；校 1–6 調）
→ 只收 missing_literal ∩ len≤12 ∩ is_valid_term
→ sources.yaml 新 id（如 cantonese_md）或 curated_lexicon 批次
→ rebuild；NOTICE 標 CC0 + upstream URL + pin commit／日期
```

### 5.2 近反義池

| 候選建模 | 判定 |
|----------|------|
| `syn`／`ant`（term↔answer） | **禁止** — 歇後語配對≠可替換近反義 |
| `semantic_related` | 無產品需求則 **不做** |

本評估**唔**以近反義決定是否引入；即使引入詞面，**邊關係仍 no**。

### 5.3 產品功能（App 內歇後語百科）

→ **no**（與填詞查韻正交）。

### 5.4 維護者審稿／文化對照

→ **允許**人手開站；唔強制。

---

## 6. 可行性矩陣

| 方案 | 技術 | 授權 | 產品增益 | 建議 |
|------|------|------|----------|------|
| P0 人手瀏覽 | 無 | 瀏覽 | 審稿 | 可 |
| P1 全量 membership 差分 | 低 | — | 決策依據 | **已完成**（§2.2） |
| P2 缺字面 → lexicon 小源／curated | 中 | CC0 | ~196 字面 + 粵拼 | **可做**（維護者拍板後） |
| P3 29 缺讀音 → 勘誤候選表 | 低 | CC0 | 讀音質 | 可選、人工 |
| P4 term↔answer → syn／ant | 低 | CC0 | **負** | **禁止** |
| P5 全文 explanation 入 DB／UI | 中 | CC0 | 離題 | 不做 |
| P6 fork 站／submodule 常駐 | 高 | MIT／CC0 | 錯產品／過重 | 不做（P2 pin zip／commit） |

---

## 7. Verdict

### **詞庫字面軸：yes-with-conditions（可選小源）**

1. 全量差分顯示 **約四成** Cantonese.md 字面本庫未收（**197／481**）→ 符合「有大量未擁有字面可考慮引入」嘅門檻（**相對源**）。  
2. 絕對量 **~196** 合格缺字面 + 現成粵拼 → 工程划算；**CC0** 合規簡單。  
3. **唔**引入站本體、全文百科、近反義邊。  
4. 實作時：只 append **缺字面** 讀音；已在庫字面預設略過（缺讀音 29 條另開人工）。  
5. 相對 rime／words.hk／kaifang：**補丁級**，`source_rank` 宜低；enable 預設可 `false` 或 true 由維護者定。

### **近反義軸：no**（不變）

與「是否引入詞面」脫鈎。

---

## 8. 建議下一步

1. 維護者確認：**是否做 P2**（缺字面 → 詞庫源）。  
2. 若做：pin 上游 commit、寫 extract 腳本、NOTICE、`sources.yaml`、rebuild 抽樣校粵拼。  
3. 可選：匯出 29 條 missing_reading 作勘誤草稿。  
4. 重跑差分：`PYTHONIOENCODING=utf-8 python scripts/research/cantonese_md_membership.py`

---

## 9. 參考

| 項目 | URL / path |
|------|------------|
| 源碼 | https://github.com/daimaruhk/Cantonese.md |
| 站 | https://cantonese.md/ |
| 資料授權 | LICENSE-DATA（CC0） |
| 差分腳本 | `scripts/research/cantonese_md_membership.py` |
| 差分 JSON | `docs/research/2026-07-18-cantonese-md-membership.json` |
| Canto 詞庫源 | `data/lexicon/sources.yaml` |

---

*觀測基準日：2026-07-18。差分對本機 `lyrics.db`（~156k 字面）。非法律意見。*
