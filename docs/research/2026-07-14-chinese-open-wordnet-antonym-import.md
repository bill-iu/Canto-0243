# Chinese Open Wordnet（COW）作為反義引用／匯入來源可行性

**日期**：2026-07-14  
**對象專案**：ICE-U-code/Canto-0243（離線粵語填詞查韻；近反義模式經**靜態詞林埠**）  
**結論摘要**：**no**（授權本身大致可再分發，但 **COW 下載物不含中文反義關係**；所謂「反義」只能經 Princeton WordNet 英文 lemma 樞紐派生，品質／繁簡／產品價值皆不適合作為低風險反義來源）

---

## 1. Question / scope（問題與範圍）

本報告評估：Chinese Open Wordnet（COW；Bond Lab／NTU；亦經 PORTULAN CLARIN 與 Open Multilingual Wordnet 再分發）是否能作為 Canto-0243 的**低風險反義引用／匯入來源**。

主要用戶提供網址：

1. PORTULAN CLARIN 紀錄：<https://portulanclarin.net/repository/browse/chinese-open-wordnet/1d169c58fe4711eabc3f02420a0004e17282b412623c45ecabeb1c0f70abcb37/>  
   （持久句柄：<https://hdl.handle.net/21.11129/0000-000D-FE55-6>）

一併查閱：官方專案頁、OMW 鏡像資料與 LICENSE、ALR-2013 論文、Princeton WordNet 3.0 授權、既有 `CONTEXT.md`／`sources.yaml`／近反義授權閘，以及與 MOE《修訂本》研究筆記之對照。

**命名辨異（必須）**：

| 簡稱 | 全名 | 腳本 | 單位 |
|------|------|------|------|
| **COW** | Chinese Open Wordnet（本報告對象） | **簡體**普通話 | NTU Bond Lab（Francis Bond、Shan Wang） |
| **CWN** | Chinese Wordnet（臺灣） | **繁體** | 臺大／中研院等（Academia Sinica CWN group） |
| BOW／SEW | 中研院雙語本體 WN／東南大學 WN | 繁／簡 | 歷史前驅；論文中用於對照 |

Global WordNet Association「Wordnets in the World」明確：Traditional → Chinese Wordnet；Simplified → Chinese Open Wordnet (COW)。  
來源：<https://globalwordnet.github.io/resources/wordnets-in-the-world>

**非範圍**：不修改應用程式碼；不實際把資料 commit 進 repo；不評估以 COW 專做近義（synset 內 lemma）是否值得（見第 6 節邊界）。

---

## 2. License & redistribution findings（授權與再分發）

### 2.1 PORTULAN 元資料 vs 資料包內 LICENSE（有張力）

PORTULAN 瀏覽／下載同意頁標示：

- **Distribution Licence**：`CC - BY`
- **Restrictions**：Attribution
- 下載同意框載入 `CC-BYv3.0` 條款文本（下載頁：<https://portulanclarin.net/repository/download/1d169c58fe4711eabc3f02420a0004e17282b412623c45ecabeb1c0f70abcb37/>）
- 簡介明文：*「All relations (hypernyms, meronyms ...) come from Princeton WordNet 3.0. We have enriched the synsets with Chinese lexical units.」*

來源：PORTULAN 紀錄頁（上列 URL）、句柄頁同文。

### 2.2 上游實際授權：WordNet 式許可（非 CC 正文）

可機讀包內的 LICENSE（應為合規準據）是 **Princeton WordNet 風格條款**，著作權標示 **Francis Bond & Shan Wang (2013, 2014)**，要點：

- 允許 **use / copy / modify / distribute**，**any purpose**，**without fee or royalty**
- 條件：著作權聲明、disclaimer 須出現在**所有**副本（含內部修改與再分發）
- 無「禁止改作」、無「非商業」限制

實測來源：

- OMW 鏡像：<https://raw.githubusercontent.com/omwn/omw-data/main/wns/cow/LICENSE>
- 專案頁同文：<https://bond-lab.github.io/cow/LICENSE>（頁面鏈結為相對 `LICENSE`）
- 數據檔頭標記 license 欄為 **`wordnet`**（不是 `CC-BY`）：  
  `# Chinese Open Wordnet	cmn	http://compling.hss.ntu.edu.sg/cow/	wordnet`

ALR-2013 論文摘要亦寫：

> COW is released under the same license as the PWN, an open license that freely allows use, adaptation and redistribution.

來源：<https://aclanthology.org/W13-4302.pdf>（亦見 ACL Anthology HTML）

GWA 表亦將 COW 標為 **WORDNET** 授權：  
<https://globalwordnet.github.io/resources/wordnets-in-the-world>

| 面向 | PORTULAN 元資料 | 包內／論文／OMW 準據 |
|------|-----------------|----------------------|
| 授權名稱 | CC-BY（標籤） | **WordNet-style**（Bond & Wang） |
| 商業利用 | CC BY 允許 | **允許** |
| 改作／衍生再散布 | CC BY 允許 | **允許**（須保留聲明） |
| 姓名標示 | Attribution | **必須**保留 copyright notice + disclaimer |
| 與 PWN 關係 | 敘述「關係來自 PWN 3.0」 | 若再匯入 PWN **結構／反義指針**，另受 **Princeton University** WordNet 3.0 LICENSE 約束 |

**合規建議**：以 **`wns/cow/LICENSE` + 數據頭 `wordnet` 標籤 + 論文聲明**為準；PORTULAN「CC-BY」視為 CLARIN 目錄粗標／下載同意 UI，**不宜**單獨寫進 `THIRD_PARTY_NOTICES` 取代 WordNet 式全文。現有 `data/syn_ant/sources.yaml` 中 `cow.license: CC-BY` **與準據不符**（資訊性欄位；本報告不改碼）。

### 2.3 Princeton WordNet 3.0 譜系摩擦

PWN 商業頁：WordNet「unencumbered」，依 LICENSE 可用於商業應用，並建議商業用途由律師審視；條款同樣要求所有副本保留 Princeton 著作權與 disclaimer，且不得將 Princeton 名稱用於宣傳背書。  
來源：<https://wordnet.princeton.edu/license-and-commercial-use>

摩擦點（對「反義」場景尤其相關）：

1. COW **自己的**再分發物（見第 3 節）幾乎只有 **cmn lemma ↔ PWN synset id**；**不含** antonym 邊。
2. 若要「做反義」，必須**另外**使用 PWN 3.0 的 **lexical antonym**（lemma／sense 級），再映射回 COW 中文 lemma——派生資料同時帶 **Bond/Wang** 與 **Princeton** 雙重 NOTICE。
3. 這比「只打包 MOE 相反詞欄」或「只打包 guotong `dict_antonym.txt`」**複雜一階**；不是「多一個 CC 標籤」而已。

### 2.4 與 Canto-0243 授權閘

`CONTEXT.md`：**靜態詞林埠**「授權閘：只納可再分發者」；反義主路徑為 guotong，**唔 OpenHowNet**。

| 來源 | 授權性格 | 對閘門 |
|------|----------|--------|
| cilin | MIT | 可再分發 |
| guotong | Anti-996 | 可再分發但有勞動條款色彩；已入庫 |
| project_ant | 專案自有 | 可 |
| MOE 修訂本 | CC BY-ND 3.0 TW | 可再分發但**禁止改作**（見 sibling 報告） |
| **COW 引理層** | WordNet-style | **可再分發／可改作**（聲明負擔低於 ND） |
| **COW+PWN 派生反義** | WordNet×2 | 理論可再分發，但屬**衍生建構**，品質與 NOTICE 成本高 |

**授權 alone**：COW 引理層**不比 MOE 更高風險**（反而比 BY-ND 寬鬆）。  
**作為「反義來源」**：授權友好≠資料存在（見下節）。

---

## 3. Available download / data formats（可下載格式）

### 3.1 官方／準官方入口（2026-07-14 觀測）

| 入口 | 內容 | 備註 |
|------|------|------|
| <https://bond-lab.github.io/cow/> | 專案說明；下載鏈至 `data/0.9/wn-data-cmn.tab` | 頁面註：伺服器版可能新於可下載檔 |
| <https://bond-lab.github.io/cow/data/0.9/wn-data-cmn.tab> | synset–lemma tab | 本報告 HTTP 200，約 2.5 MB |
| <https://github.com/omwn/omw-data/tree/main/wns/cow> | `wn-data-cmn.tab`、`cow-not-full.txt`、`LICENSE`、`cow2tab.py`、`citation.bib` | 鏡像完整、可腳本拉取 |
| PORTULAN Download | 須勾選 licence agree | UI 標 CC-BY；本環境 POST 下載因 CSRF 未取得二進位包，改以 OMW／bond-lab 檔驗證內容 |
| 舊 NTU URL `http://compling.hss.ntu.edu.sg/omw/wns/cmn.zip` | 歷史 OMW 壓縮包 | 本環境連線失敗（size 0）；**勿當唯一生產來源** |

統計標稱（專案頁與 PORTULAN Size）：

- **42,315** synsets  
- **79,812** senses  
- **61,536** unique words  

### 3.2 檔案結構（實測：omw-data `wn-data-cmn.tab`）

格式（OMW `wns/README`）：

```text
# name<TAB>lang<TAB>url<TAB>license
offset-pos<TAB>lang:type<TAB>lemma
```

觀測：

| 項目 | 值 |
|------|-----|
| 資料列（`cmn:lemma`） | **79,797** |
| 唯一 lemma | **61,525** |
| 關係型別 | **僅** `cmn:lemma`（**0** 筆 `antonym`／其他 semantic pointer） |
| `cow-not-full.txt` | `synset<TAB>lemma`（匯出前源）；同樣**無** antonym |
| `cow2tab.py` | 只把 status ∈ {Y,O} 的 lemma 寫入 tab；`wnlicense = "wordnet"` |

→ **可下載的 COW 再分發物＝中文詞形掛上 PWN 3.0 synset id 的對照表**，不是「中文反義詞典」。

### 3.3 若要把「關係」算進來

PORTULAN／專案頁宣稱 *All relations … come from Princeton WordNet 3.0*。  
OMW 再分發慣例（`wns/README`）：各語言目錄只放 **synset–lemma**；**不**把 PWN `data.*` 指針複製進 `wn-data-cmn.tab`。  
英語目錄 `wns/eng/wn-data-eng.tab` 同樣幾乎只有 `lemma`（無可用 antonym 邊）。

因此：**「關係來自 PWN」≠「COW ZIP 裡有中文反義表」**；要用關係必須另取 PWN（或經 NLTK／`wn` 庫載入的完整 WordNet）。

---

## 4. Antonym index structure（相反詞結構）

### 4.1 COW 本身

**沒有**獨立 antonym 索引、沒有 `lemma → 反義列表` 欄位、檔內 **0** 次 `antonym` 字樣（實測 `wn-data-cmn.tab`／`cow-not-full.txt`）。

論文構建焦點是：**核心理念 synset 的中文翻譯校對與擴充**（刪錯譯、改正體、補 的／地），並假設 PWN **語意關係**（hypernym 等）可沿用；**並未**記述另建漢語反義庫。  
來源：Wang & Bond (2013)，<https://aclanthology.org/W13-4302.pdf>

### 4.2 經英文樞紐「借」反義（非 COW 原生）

WordNet 官方文件：antonymy 屬 **lexical pointer**（詞形級），不是對整個 synset 成立的 semantic pointer。  
來源：<https://wordnet.princeton.edu/documentation/wninput5wn>

實務路徑（社群／庫維護者確認）：

1. 中文 lemma → COW／OMW synset  
2. 對應英文 sense／lemma  
3. 取英文 `antonym`  
4. 再 translate 回中文 lemma  

`wn` 庫維護者 goodmami（NLTK #2972）：

> … the Chinese wordnet does not have any antonyms defined, you can try to rely on the English antonyms, but you may be surprised by the results.

來源：<https://github.com/nltk/nltk/issues/2972>

樣本偏差示例（同 thread）：「大+的」經英文可映射到「有限+的」等——對粵語填詞「自然反義」體感不可靠。

構造（若強制生產派生表）概念上為：

```text
cmn_lemma_i  --(same synset / sense map)-->  en_lemma
en_lemma     --(PWN lexical antonym)-->     en_ant
en_ant       --(COW lemmas on ant synset)--> cmn_lemma_j
```

此表是 **工程派生**，不是 COW 作者標註的漢語反義金標。

### 4.3 與專案既有 cow stub 行為

`data/syn_ant/sources.yaml` 已有停用預設之 `id: cow`（`parser: wordnet_synsets`，`local_only: true`）。  
`ingest/syn_ant_sources.py::parse_wordnet_synsets` 只把**同一 synset 內**多個 lemma 連成 **`syn` 邊**，**不產生 `ant`**。

→ 即使 maintainer 放入 raw 檔，現管線也是「近義團」，不是「反義匯入」。

---

## 5. Fit to Canto-0243（與產品適配）

依 `CONTEXT.md`：產品詞條＝繁體漢字字面＋粵拼＋0243／394052；近反義經**近反義池**／**靜態詞林埠**；授權閘只納可再分發者。

| 面向 | COW 適配 |
|------|----------|
| 腳本 | **簡體**為設計目標（論文 §3：「Because SEW, WIKT and the corpus … are in simplified Chinese, COW is also made in simplified Chinese」）。抽樣標記字（国／学／对／发…）落在簡體側；繁體標記字命中約 **0**。 |
| 字面形態 | 大量形容詞形如 **`大+的`**、**`小+的`**（`+` 約 13.7k／61.5k unique）——與粵語詞庫常用「大／細／細細個」等**字面交集差** |
| 與粵語書面繁體 | 須 OpenCC **s2t**（類似 cilin），且轉換後仍有普通話語域／書面詞 |
| 音韻 | 無粵拼、無 0243 |
| 反義語義 | **無原生反義**；英文樞紐派生≠國語辭典式相反詞，更遠於粵語口語 |
| 授權閘 | 引理層可再分發；派生反義需雙 NOTICE |
| 相對既有源 | guotong 已有漢字反義對（`dict_antonym.txt`）；project_ant  crouch 自建；cilin 近義；MOE 有現成「相反詞」欄但 BY-ND |

**缺口**：匯入 COW **不會**直接增加直連反義覆蓋；最多是（a）簡體 synset 近義團，或（b）高噪聲的英樞反義候選。相對上下文「反義 guotong，唔 OpenHowNet」的精神——**英樞 WordNet 反義與 HowNet 類跨語資源同屬高噪聲外語投影**，不應偷偷升成直連權威。

---

## 6. Verdict（裁決）

### **no**（就「低風險**反義**來源」而言）

COW **不建議**作為 Canto-0243 的低風險反義引用／匯入來源。

理由收束：

1. **資料事實**：可再分發檔**不含** antonym；「有反義」是誤讀 PORTULAN「relations from PWN」句。  
2. **產品適配**：簡體＋`X+的`＋英樞派生，與繁體粵語填詞交集／體感差。  
3. **相對價值**：授權雖寬於 MOE BY-ND，但 **MOE 至少有相反詞欄**；COW 在反義任務上**價值更低**。對已有 guotong＋project_ant，COW 反義路徑屬 YAGNI。  
4. **風險形態**：問題不在「能不能合法拷貝 tab」，而在「拷貝後仍沒有可用反義」＋「若硬造派生表，合規與品質雙重摩擦」。

### 什麼時候才接近 **yes-with-conditions**（非本報告推薦預設）

僅當產品明確改目標為例如「可選 synset 近義擴展／跨語實驗」，而非直連反義權威，且：

1. 以 **WordNet-style LICENSE**（非僅寫 CC-BY）置入 NOTICE；標示 Bond & Wang + 版本／來源 URL。  
2. 若使用任何 PWN 指針／antonym：**並附 Princeton WordNet 3.0 LICENSE**。  
3. 派生 ant 標記獨立 source（如 `cow_pwn_pivot`），**不得**混充 `project_ant`；須人工／抽樣閘。  
4. 維持 `enabled_by_default: false`／`local_only`；執行期 s2t＋詞庫字面交集。  
5. 修正對內文件：`sources.yaml` 的 `license: CC-BY` 應改為反映 WordNet 式準據（何時改碼另議）。

### 與 MOE sibling 報告對照（問題 5）

| | COW | MOE《修訂本》 |
|--|-----|----------------|
| 授權友善（再分發／改作） | 較寬（WordNet-style） | 較嚴（BY-ND） |
| 原生中文反義表 | **無** | **有**（XLSX「相反詞」／附錄） |
| 繁體字面 | 差（簡體為主） | 佳（國語繁體） |
| 作「反義來源」總評 | **no** | **yes-with-conditions** |

→ **COW 並非「比 MOE 更低風險的反義源」**；授權風險較低的是「引理表本身」，不是「反義用例」。

---

## 7. Open questions / risks（待決與風險）

1. **PORTULAN CC-BY vs 包內 WordNet LICENSE**：目錄元資料不一致；再分發應釘準據檔，必要時向 CONTACT（Shan Wang／PORTULAN helpdesk）確認寄存條款是否意圖改授 CC。  
2. **NTU 舊下載 host**（`compling.hss.ntu.edu.sg`）可用性不穩定；生產應釘 **GitHub omw-data commit** 或 bond-lab `0.9` 檔＋checksum。  
3. **英樞反義覆蓋率／噪聲率**：未在本報告跑完整 PWN×COW join（環境無 NLTK／`wn`）；定性證據已足夠否決「低風險反義源」，定量增量仍可另開實驗但不影響本裁決。  
4. **`sources.yaml` 誤標 CC-BY**：易造成維護者誤判合規文案。  
5. **CWN（繁體）**：GWA 另列 Traditional Chinese Wordnet；授權亦為 WordNet 式，但**仍非本報告對象**；是否另研繁體 WN 反義須獨立開題（且同樣可能缺漢語原生 ant）。  
6. **法律免責**：本文件為技術／公開授權條款整理，**不是**律師意見。

---

## 參考連結速查

| 項目 | URL |
|------|-----|
| PORTULAN 紀錄 | https://portulanclarin.net/repository/browse/chinese-open-wordnet/1d169c58fe4711eabc3f02420a0004e17282b412623c45ecabeb1c0f70abcb37/ |
| 持久句柄 | https://hdl.handle.net/21.11129/0000-000D-FE55-6 |
| 專案頁 | https://bond-lab.github.io/cow/ |
| COW LICENSE（專案） | https://bond-lab.github.io/cow/LICENSE |
| COW tab 0.9 | https://bond-lab.github.io/cow/data/0.9/wn-data-cmn.tab |
| OMW cow 目錄 | https://github.com/omwn/omw-data/tree/main/wns/cow |
| OMW cow LICENSE | https://raw.githubusercontent.com/omwn/omw-data/main/wns/cow/LICENSE |
| OMW 總覽 | https://omwn.org/ |
| GWA Wordnets in the World | https://globalwordnet.github.io/resources/wordnets-in-the-world |
| Wang & Bond ALR-2013 PDF | https://aclanthology.org/W13-4302.pdf |
| PWN 授權與商用 | https://wordnet.princeton.edu/license-and-commercial-use |
| PWN wninput（lexical antonym） | https://wordnet.princeton.edu/documentation/wninput5wn |
| NLTK #2972（中文無 antonym） | https://github.com/nltk/nltk/issues/2972 |
| Sibling：MOE 相反詞匯入 | docs/research/2026-07-14-moe-revised-dict-antonym-import.md |

---

*觀測基準日：2026-07-14；實測檔：omw-data `wns/cow/wn-data-cmn.tab`（79,797 `cmn:lemma` 列）與 bond-lab `data/0.9/wn-data-cmn.tab`。*
