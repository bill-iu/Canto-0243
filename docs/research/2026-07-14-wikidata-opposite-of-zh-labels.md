# Wikidata P461「opposite of」＋中文標籤作為反義／相反來源可行性

**日期**：2026-07-14  
**對象專案**：ICE-U-code/Canto-0243（離線粵語填詞查韻；近反義經**靜態詞林埠**；字面偏好繁體）  
**關聯報告**：[`2026-07-14-moe-revised-dict-antonym-import.md`](./2026-07-14-moe-revised-dict-antonym-import.md)（教育部修訂本：CC BY-ND）  
**結論摘要**：**yes-with-conditions**（授權友善、可抽出帶中文標籤嘅 P461 對；惟屬**概念對立**而非辭典反義詞，須過濾雜訊，且繁體覆蓋遠小於泛 `zh`）

---

## 1. Question / scope（問題與範圍）

評估 Wikidata（結構化資料 **CC0**）能否產出同時具：

1. 屬性 **P461**（opposite of／相反於），以及  
2. **中文標籤**（`zh`／`zh-tw`／`zh-hant`／`zh-hans`／`zh-hk`／`zh-cn` 等）

之 item／邊，作 Canto-0243 **靜態詞林埠**潛在反義／相反來源。

**非範圍**：唔改應用程式碼；唔把資料 commit 進 repo。

主要一手來源（用戶指定）：

| 主題 | URL |
|------|-----|
| P461 | <https://www.wikidata.org/wiki/Property:P461> |
| 授權概覽 | <https://www.wikidata.org/wiki/Wikidata:Licensing> |
| 版權聲明 | <https://www.wikidata.org/wiki/Wikidata:Copyright> |
| 資料存取 | <https://www.wikidata.org/wiki/Wikidata:Data_access> |
| 資料庫下載 | <https://www.wikidata.org/wiki/Wikidata:Database_download> |
| SPARQL | <https://query.wikidata.org/sparql> |

補充一手：

| 主題 | URL |
|------|-----|
| Lexeme sense 反義 **P5974** | <https://www.wikidata.org/wiki/Property:P5974> |
| Label 說明 | <https://www.wikidata.org/wiki/Help:Label> |
| 中文變體轉換 fallback（社群模組） | <https://www.wikidata.org/wiki/Module:Conversion-zh> |

觀測日 SPARQL 查詢以 `User-Agent: Canto-0243-research/1.0` 對 WDQS 執行（2026-07-14）。數字會隨 Wikidata 編輯變動。

---

## 2. License：結構化資料 CC0（再分發意涵）

### 2.1 官方政策

**Wikidata:Copyright** 明文：

> All structured data from the main, Property, Lexeme, and EntitySchema namespaces is available under the Creative Commons **CC0** License; text in the other namespaces is available under the Creative Commons Attribution-ShareAlike License; additional terms may apply.

來源：<https://www.wikidata.org/wiki/Wikidata:Copyright>

**Wikidata:Licensing** 重申：main／property／lexeme 命名空間之結構化資料以 **CC0（等同公有領域）** 提供；其他命名空間文字為 CC BY-SA 4.0。

來源：<https://www.wikidata.org/wiki/Wikidata:Licensing>

**Wikidata:Database download** 對 dump 同樣寫明：main／Property／Lexeme／EntitySchema 結構化資料 **CC0**；其他命名空間文字 BY-SA。

來源：<https://www.wikidata.org/wiki/Wikidata:Database_download>

### 2.2 對開源 App 再分發的意義

| 面向 | Wikidata 結構化資料（含 item 陳述、標籤、lexemes） |
|------|------------------------------------------------------|
| 權利狀態 | **CC0**——無保留權利（「No rights reserved」） |
| 再散布／改作／商業 | **允許**（政策層級） |
| 強制署名 | **法律上唔要求** |
| 社群期望 | Data access 頁懇請標註來源（如 “Powered by Wikidata”／“Data from Wikidata”），屬善意、非 CC0 義務 |

來源：<https://www.wikidata.org/wiki/Wikidata:Data_access>（「Using Wikidata's data」）

**實務含義（Canto-0243）**：

- 可把抽出嘅 P461 對＋中文標籤 **bundled** 進開源離線 App、改格式、過濾、映射到詞條字面——**唔像**教育部修訂本 CC BY-ND 有禁止改作邊界。  
- Item／Property／Lexeme 之外嘅 wiki 頁面文字仍可能係 BY-SA；本用例只取結構化陳述＋標籤，維持喺 CC0 範圍內。  
- 仍宜喺文件標註來源與抽取日期（社群期望＋可追溯性）。

### 2.3 與教育部修訂本（輕比較）

| | Wikidata P461 路線 | 教育部《重編國語辭典修訂本》相反詞 |
|--|-------------------|--------------------------------------|
| 授權 | **CC0** | **CC BY-ND 3.0 TW** |
| 改作／過濾後再散布 | 政策允許 | ND：內容改寫／合併成新辭典踩線風險高 |
| 適合靜態詞林埠授權閘 | **高** | **受限**（見既有 MOE 報告） |
| 語意性質 | 概念／本體對立（見 §3） | 辭典**相反詞**字面 |

→ 授權面 Wikidata **明顯較易**納入 `CONTEXT.md` 所述「授權閘：只納可再分發者」。產品適配問題在**語意噪音**與**非詞引理**，唔在授權。

---

## 3. P461 係乜：本體「相反」，唔係語言學反義詞典

### 3.1 定義與用法指示

P461 英文 label：**opposite of**；描述：

> item that is in some way the opposite of this item

**Data type**：Item（指向另一 Q-item）。

官方 usage instructions：

> Only use with values that are **directly opposed** to the item with respect to a **binary quality or relation**. Specify with the qualifier ‘criterion used’ **P1013**. If the quality or relation is not binary, use ‘different from’ **P1889**.

來源：<https://www.wikidata.org/wiki/Property:P461>

官方例子包括：war↔peace、proprietary software↔free software、winter↔summer、black↔white（qualifier：lightness）、south↔north、female↔male（qualifier：gender binary）。

約束方面有 **symmetric constraint**（對稱約束），實務上多數成對互指，但唔保證每條邊都有反向陳述。

### 3.2 與「詞典反義詞」嘅差異（對 Canto-0243 關鍵）

| | P461 | 辭典反義／粵語近反義池期望 |
|--|------|---------------------------|
| 節點 | **Q-items**（概念、實體、類） | **詞引理／詞條字面** |
| 關係 | 二元性質／關係上嘅對立 | 語言學 antonym／opposite sense |
| 標籤 | 多語言 item label（可歧義；靠 description 消歧） | 詞目本身 |
| 典型噪音 | 政黨對、生物分類、地緣區域、軟體授權、性別二元… | 詞彙層面較少出現「共和黨↔民主黨」 |

→ **唔可以**把 P461 當「下載即得」嘅中文反義詞典。充其量係**可 CC0 再分發嘅概念相反圖**，再經標籤投影＋過濾，弱覆蓋／增強現有反義源。

### 3.3 相關：Lexeme sense 反義 P5974

**P5974 antonym**：

> sense of a lexeme with the opposite meaning to this sense, **in the same language**

- Data type：**Sense**（詞義單位，唔係 Q-item）  
- Instance of：Wikidata property for lexicographical senses  
- 標註為 **subproperty of** opposite of（P461）  
- 約束：只允許加喺 sense；**conflicts-with** 提示唔好加喺 items  

來源：<https://www.wikidata.org/wiki/Property:P5974>

**規模（SPARQL，2026-07-14）**：

| 計量 | 值 |
|------|-----|
| 全部 P5974 邊 | **3 427** |
| 主詞 lemma 語言為 `zh*` 或 `yue` 嘅 P5974 | **124**（其中 lemma `zh` ≈ 55，其餘為匹配到嘅 zh*／yue 合計） |

→ 真正「詞典式」Wikidata 反義（P5974）目前對中文／粵語**極稀疏**；短期唔足以替代 guotong／自建反義。P461 反而喺 **item 層**覆蓋大好多，但語意層次唔同。

---

## 4. 點樣抽取：SPARQL、JSON／RDF dump

### 4.1 Wikidata Query Service（SPARQL）

- 端點：`https://query.wikidata.org/sparql`（互動：`https://query.wikidata.org`）  
- 適用：已知關係特徵、結果集可收窄（例如只抽 P461＋中文標籤）  
- 唔適合：要把 Wikidata「大半」拉返嚟；大型結果應改 dump  

來源：<https://www.wikidata.org/wiki/Wikidata:Data_access>（「Wikidata Query Service」）

最佳實踐：合理 `User-Agent`、勿過密請求、遇 429 停等、大型抽取設合理 timeout。

### 4.2 Database dumps

| 格式 | 位置／說明 |
|------|------------|
| **JSON（建議）** | 週更；整庫 entities：`https://dumps.wikimedia.org/wikidatawiki/entities/` |
| **RDF**（Turtle／N-Triples） | 同目錄；另有 **truthy** dumps（僅 best-rank 直接值，`wdt:`） |
| Lexeme RDF | 同目錄，`lexemes` 后缀 |

來源：<https://www.wikidata.org/wiki/Wikidata:Database_download>

- JSON／RDF dumps 視為 **stable interfaces**（變動受 Stable Interface Policy 約束）。  
- Data access：結果集很大時優先 dump；SPARQL 適合「只知特徵、結果已收窄」。  

**P461 子集**：約數萬邊，**SPARQL 一次抽出可行**；若要離線可重現／避免 WDQS 負載，可對 truthy RDF 或 JSON dump 過濾 `P461`（或用第三方 WDumper 做 partial RDF）。

### 4.3 其他入口（本用例次要）

Linked Data Interface（單一 entity JSON／RDF）、Action API／REST API、GraphQL——適合抽少量已知 Q；大批量仍 dump／SPARQL。  
來源：同上 Data access 頁。

---

## 5. 中文標籤語碼與 P461 覆蓋（SPARQL 實測）

### 5.1 語碼現實

Wikidata item 可同時有多個中文相關 label；社群模組 `Module:Conversion-zh` 列出嘅目標變體包括：`zh`、`zh-hans`、`zh-hant`、`zh-cn`、`zh-tw`、`zh-hk`、`zh-mo`、`zh-sg`、`zh-my`，並定義繁簡 fallback 鏈（例如 `zh-hant` → `zh-tw` → `zh-hk` → … → `zh`）。

來源：<https://www.wikidata.org/wiki/Module:Conversion-zh>

語意直覺（與 Wikimedia／Wikidata 慣例一致）：

| 碼 | 大致用途 |
|----|----------|
| `zh` | 泛中文標籤；**實務常混簡繁**（觀測樣本見下） |
| `zh-hans`／`zh-cn`／`zh-sg`／`zh-my` | 簡體側 |
| `zh-hant` | 繁體（跨區通用繁） |
| `zh-tw` | 台灣用詞／繁體 |
| `zh-hk`（及 `zh-mo`） | 港澳用詞／繁體 |

Labels 係「最常見名稱」、可歧義；唔等同詞典詞目。  
來源：<https://www.wikidata.org/wiki/Help:Label>

### 5.2 規模數字（WDQS，2026-07-14）

**邊計數方法**：`COUNT(*)` 於 `?a wdt:P461 ?b`，以 `EXISTS { … rdfs:label … }` 避免一個 item 多個 zh* label 導致笛卡兒膨脹。

| 計量 | 數值 | 備註 |
|------|------|------|
| P461 有向邊總數 | **51 110** | `wdt:P461` truthy |
| 其中 `STR(?a) < STR(?b)`（約「一半」對稱配對） | **25 557** | 約略無向對數 |
| 出現為 P461 主語嘅 distinct items | **49 937** | |
| 兩端皆有 **任何** `LANGMATCHES(…,"zh")` 標籤 | **10 911** | ≈ 總邊 21% |
| 兩端皆有泛 **`zh`** | **10 471** | 覆蓋主力；字形品質不一 |
| 兩端皆有 **`zh-hans`** | **2 314** | |
| 兩端皆有 **`zh-hant` OR `zh-tw` OR `zh-hk`** 之一 | **3 681** | 繁體側可用性上限（有向邊） |
| 兩端皆 **`zh-hant`** | **3 444** | |
| 兩端皆 **`zh-tw`** | **1 654** | |
| 兩端皆 **`zh-hk`** | **1 263** | |
| 無向＋兩端 `zh-hant` 且字串長度 ≤4 | **1 020** | 粗濾「較似詞」嘅上限之一 |

**P461 主語有中文標籤嘅 distinct item 數（按語碼；同一 item 可入多碼）**：

| 語碼 | Distinct 主語數 |
|------|-----------------|
| `zh` | 13 173 |
| `zh-hant` | 5 577 |
| `zh-hans` | 4 279 |
| `zh-tw` | 2 947 |
| `zh-cn` | 2 782 |
| `zh-hk` | 2 584 |
| `zh-sg` | 1 262 |
| `zh-my` | 498 |
| `zh-mo` | 497 |

### 5.3 標籤品質示意（樣本，非抽樣統計）

泛 `zh` 樣本同時見簡繁混用，例如「硬件／软件」與「戰爭／和平」、「網頁伺服器」並存。  
`zh-hant` 樣本包括可用於詞彙聯想者（黑／白、冬／夏、東／西），亦包括明顯噪音：東南亞↔東北亞、共和黨↔民主黨、偶蹄目↔奇蹄目、短片↔劇情長片、複數↔實數等。

→ **有中文標籤 ≠ 適合填詞反義**。繁體碼減少簡繁混雜，但唔解決概念／專名對立噪音。

---

## 6. 與 Canto-0243 嘅適配

專案需求摘自 `CONTEXT.md`：**靜態詞林埠**要可再分發；反義現有 guotong 等；近反義面對嘅係**詞條字面／詞關係**，用於 `!`／反義池。

| 維度 | 適配判斷 |
|------|----------|
| 授權閘 | **強適配**（CC0 ≫ MOE BY-ND） |
| 節點形態 | **弱適配**：Q-items＋label → 需投影成字面；label 可歧義、可係專名／術語 |
| 繁體偏好 | **中等**：優先 `zh-hant`→`zh-tw`→`zh-hk`→謹慎使用泛 `zh`；泛 `zh` 量大但簡繁混 |
| 與辭典反義重疊 | **部分重疊**（黑白、冬夏、父母等）＋大量**無詞典反義意義**嘅對立 |
| P5974 詞典式反義 | 中文量太小，僅作未來監控，唔宜當主源 |
| 離線 bundle | 技術可行（數千～一萬級邊遠細過全庫 dump） |

**定位建議**：Wikidata P461 = **可選、可過濾嘅概念相反輔助源**，補充而非取代辭典／自建反義；若產品只接受「像詞典反義」嘅邊，預期最終保留率遠低於 3 681（繁體兩端）／10 911（任意 zh*）。

---

## 7. Verdict

### **yes-with-conditions**

**Yes** 嘅部分：

1. 結構化資料（含 P461 陳述與中文 labels）以 **CC0** 提供，適合開源 App 再分發、過濾、改格式。  
2. 可經 SPARQL 或 dump **實際抽出**帶中文標籤嘅 P461 對；繁體相關兩端邊以千計。  
3. 相對教育部修訂本，**授權風險低得多**。

**Conditions（必須滿足先有產品價值）**：

1. 認知上定位為 **ontological opposite**，唔當漢語反義詞典。  
2. Label 優先序與簡繁清洗：`zh-hant`／`zh-tw`／`zh-hk`；泛 `zh` 需簡繁偵測或降權。  
3. **強制過濾雜訊**（見 §8）；可選：只接受雙方 label 短、雙方有 sitelink 至辭典類、或與現有詞庫字面交集。  
4. 唔依賴 P5974 作中文主源（現時過稀）。  
5. Bundle 標註來源與抽取日期；遵守 API／query 禮儀。

若堅持「匯入即詞典級反義、零過濾」，則應改判 **no**——但喺上述條件下，作為 CC0 輔助語料屬 **yes-with-conditions**。

---

## 8. 建議最小抽取配方＋風險

### 8.1 最小配方（手動／腳本皆可；本報告唔落地程式）

1. **SPARQL 抽出**（示意；生產可加 `SERVICE wikibase:label` 或明確 `rdfs:label`）：

```sparql
SELECT ?a ?b ?la ?lb ?langA ?langB WHERE {
  ?a wdt:P461 ?b .
  ?a rdfs:label ?la . FILTER(LANG(?la) IN ("zh-hant","zh-tw","zh-hk"))
  ?b rdfs:label ?lb . FILTER(LANG(?lb) IN ("zh-hant","zh-tw","zh-hk"))
}
```

2. **正規化**：有向邊去重成無向對（`min(Q,Q')`）；對稱缺邊可補一邊。  
3. **標籤選擇**：每 item 優先 `zh-hant` > `zh-tw` > `zh-hk`；缺則跳過或降級到審核佇列。  
4. **過濾（最低限度）**：  
   - 字串長度上限（例如 ≤4～6 汉字；排除長專名／機構名）  
   - 排除明顯分類／地理／組織命名模式（可 blacklist 關鍵字或 instance of／subclass 粗濾）  
   - **與現有詞庫／粵語音庫字面求交**——無交集嘅對唔入 runtime 埠  
5. **人工或半自動抽樣驗收**後，先以小檔（例如數百對）進 **靜態詞林埠** 實驗軌，唔一次全量當 guotong 同級。  
6. **署名／溯源**：`source=wikidata`、`property=P461`、dump／query 日期；檔頭註 CC0。

可選升級：truthy RDF dump 本地過濾，避免倚賴 WDQS 穩定性。

### 8.2 風險與噪音類型（官方例子＋觀測）

| 類型 | 例子 | 對填詞反義風險 |
|------|------|----------------|
| 抽象政治／價值對立 | war↔peace（官方例） | 詞彙可用，但廣；與「開心↔唔開心」唔同類 |
| 軟體授權 | proprietary↔free software（官方例） | 術語，填詞價值低 |
| 性別二元 | female↔male + qualifier gender binary（官方例） | 敏感＋產品未必想推導「反義」 |
| 地緣／行政 | 東南亞↔東北亞 | 幾乎唔係反義詞 |
| 政黨／組織 | 共和黨↔民主黨 | 噪音 |
| 生物分類 | 偶蹄目↔奇蹄目 | 噪音 |
| 數學／技術術語 | 複數↔實數、硬體↔軟體 | 偶可用；多數偏術語 |
| Label 簡繁混 | 泛 `zh` | 破壞繁體字面契約 |
| Label 歧義 | 同 label 多 Q | 錯連詞條 |

Qualifier **P1013**（criterion used）有時可幫分類，但唔完整；**唔好**假設有 qualifier＝乾淨。

### 8.3 相對 MOE 報告嘅一句比較

- **MOE**：詞典相反詞品質較貼近產品，但 **BY-ND** 限制過濾／衍生再散布。  
- **Wikidata P461**：**CC0** 暢通，但必須承認語意層係「概念對立＋標籤投影」，要靠過濾同詞庫交集先接近 Canto-0243 反義埠期望。

---

## 9. 來源清單（一手）

1. <https://www.wikidata.org/wiki/Property:P461>  
2. <https://www.wikidata.org/wiki/Wikidata:Licensing>  
3. <https://www.wikidata.org/wiki/Wikidata:Copyright>  
4. <https://www.wikidata.org/wiki/Wikidata:Data_access>  
5. <https://www.wikidata.org/wiki/Wikidata:Database_download>  
6. <https://query.wikidata.org/sparql>（本報告即日實測）  
7. <https://www.wikidata.org/wiki/Property:P5974>  
8. <https://www.wikidata.org/wiki/Help:Label>  
9. <https://www.wikidata.org/wiki/Module:Conversion-zh>  
10. 本 repo：`docs/research/2026-07-14-moe-revised-dict-antonym-import.md`、`CONTEXT.md`（產品語境；非 Wikidata 政策來源）

---

---

## 10. 後續計量：繁體 P461 ∩ 本地詞庫（2026-07-14）

依 §8 建議做了一次本機抽出＋求交（**未**接入 ingest／runtime）。

### 10.1 資料與方法

| 輸入 | 來源 |
|------|------|
| P461 邊 | WDQS `SELECT ?a ?b WHERE { ?a wdt:P461 ?b }` → **51 110** 有向邊 |
| 繁體標籤 | 分別取 `zh-hant`／`zh-tw`／`zh-hk` label；每 Q 優先序 `zh-hant` > `zh-tw` > `zh-hk` |
| 詞庫字面 | 本機 `lyrics.db`：`SELECT DISTINCT char` → **157 898** |
| 對照反義 | `project_antonyms.tsv`；guotong 以「非漢字分隔」完整切開（見下） |

本機產出（`data/syn_ant/raw/` 已 gitignore，不入版控）：

- `wikidata/p461_zh_trad_pairs.tsv`
- `wikidata/p461_intersect_lexicon.tsv`
- `wikidata/p461_novel_vs_guotong_project.tsv`
- `wikidata/p461_novel_kept_heuristic.tsv`
- `wikidata/p461_intersect_summary.json`

### 10.2 漏斗數字

| 階段 | 無向對數 |
|------|----------|
| 兩端皆有繁體優先標籤 | **1 946**（與 §5 有向 ~3.7k 同量級） |
| 兩端 label 皆純 CJK 且長度 ≤6 | **1 372** |
| 再 ∩ 詞庫字面（去自環） | **412** |
| 已在完整 guotong（CJK 切開，11 257 無向對） | **75** |
| 已在 project_ant | **23** |
| **相對兩者皆新** | **326** |
| 粗噪音啟發式後（政黨／主義／生肖／干支等） | **282** |
| 其中兩端長度皆 ≤2 | **182** |

### 10.3 樣本（啟發式保留、二字）

可用傾向：`丈夫|妻子`、`下班|上班`、`下載|上傳`、`健康|疾病`、`兄弟|姐妹`、`出生|死亡`、`前綴|後綴`。

偏弱／概念對立：`上下|左右`、`僵局|妥協`、`兒子|父母`、`仰臥|臥姿`。

被啟發式濾掉示例：`反對黨|執政黨`、`協約國|同盟國`、`兔|酉`。

### 10.4 副產品：guotong runtime 解析缺口

`dict_antonym.txt` 約 **1.7 萬**行主分隔符其實是 ASCII `--`（U+002D×2），另有 `——`／`—`／`―`／`──`。  
現行 `app/thesaurus/static_index.load_thesaurus_dicts` 只把 `——`／`—`／`–` 換成空白再 `split()`，**吃唔到 `--`**，runtime 無向反義對約只得 **366**（對完整 CJK 切開嘅 **11 257**）。  
→ 修呢個 loader 可能比匯入 Wikidata **更大、更直接**提升既有反義覆蓋；與 P461 決策獨立。

### 10.5 產品建議（更新）

1. **Wikidata P461**：授權佳；詞庫交集後「相對 guotong＋project_ant 新增」約 **300** 無向對，粗濾後約 **180** 短字面——有料但唔多，只適合**小檔輔助源＋人工抽樣**，唔值得當主源。  
2. **優先考量**：先修 guotong `--` 解析（見 §10.4），再決定要唔要接 `wikidata_p461`。  
3. 若要試接：只收 `p461_novel_kept_heuristic.tsv` 級別、source=`wikidata_p461`、NOTICE 註 CC0＋抽取日。

---

*報告結束。§5／§10 數字以 2026-07-14 為準；再評估前請重跑 SPARQL 與本機求交。*
