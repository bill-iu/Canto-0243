# 教育部《重編國語辭典修訂本》相反詞／全文資料匯入可行性

**日期**：2026-07-14  
**對象專案**：ICE-U-code/Canto-0243（離線粵語填詞查韻；近反義模式經**靜態詞林埠**）  
**結論摘要**：**yes-with-conditions**（可以匯入，但須維持 CC BY-ND 不可改作邊界，且產品適配有國語／粵語落差）

---

## 1. Question / scope（問題與範圍）

本報告評估：臺灣教育部《重編國語辭典修訂本》資料——特別是**相反詞索引表**附錄，以及／或**全文詞條**（含條目內「相反詞／相似詞」欄）——是否能**合法**且**技術上可行**地匯入開源專案 Canto-0243。

主要用戶提供網址：

1. 資料下載頁：<https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/dict_reviseddict_download.html>
2. 相反詞索引表（網頁附錄）：<https://dict.revised.moe.edu.tw/appendix.jsp?ID=7&page=23&la=0&powerMode=0>

一併查閱：公眾授權總頁、使用說明、線上 FAQ、g0v／其他 GitHub 鏡像與授權註記，以及本專案 `CONTEXT.md`／既有近反義資料授權閘。

**非範圍**：不修改應用程式碼；不實際把資料 commit 進 repo。

---

## 2. License & redistribution findings（授權與再分發）

### 2.1 官方授權條款（以公眾授權網為準）

教育部國語辭典公眾授權網與下載頁明文：

> 中華民國教育部《重編國語辭典修訂本》、《國語辭典簡編本》、《國語小字典》與《成語典》相關資料採「**創用CC-姓名標示-禁止改作 3.0 臺灣授權條款**」釋出。本授權條款允許使用者**重製、散布、傳輸著作（包括商業性利用）**，但**不得修改該著作**，使用時必須遵照「使用說明」之內容要求。

來源：

- 下載頁：<https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/dict_reviseddict_download.html>（觀測日版本標籤示例：`dict_revised_2015_20260625`）
- 公眾授權總頁：<https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/index.html>
- CC 條款全文：<https://creativecommons.org/licenses/by-nd/3.0/tw/legalcode>
- 條款摘要 deed（繁）：<https://creativecommons.org/licenses/by-nd/3.0/tw/deed.zh_TW>

| 面向 | 結論 |
|------|------|
| 授權名稱 | **CC BY-ND 3.0 TW**（姓名標示－禁止改作） |
| 商業利用 | **允許**（下載資料包層級） |
| 再散布／重製／傳輸 | **允許** |
| 改作／衍生後再散布 | **禁止** |
| 姓名標示 | **必須** |
| 政府資料開放授權條款（OGDL） | **本典不套用 OGDL**；機關一般網站「政府資料開放宣告」≠ 本辭典資料包授權 |

### 2.2 《公眾授權使用說明》額外限制（重要）

第三方轉載之使用說明 PDF（內容與官方釋出一致，kemdict 鏡像）：  
<https://kemdict.com/l/reviseddict_10312.pdf>

重點摘錄：

1. 採用 **創用 CC－姓名標示－禁止改作 臺灣 3.0 版**。
2. **姓名標示**須為：  
   `中華民國教育部（Ministry of Education, R.O.C.）。《重編國語辭典修訂本》（版本編號：_____）網址：http://dict.revised.moe.edu.tw/`
3. **額外授權聲明**：對個別條目的**詞目、部首、筆畫、字形、音讀及釋義**不得修改，**不得轉為簡化字**。  
   惟依教育部對照表做**字碼改換**，或**不涉及更改個別條目所有內容**之調整，**可不被認定**落入禁止修改範圍。
4. 無論是否再散布，皆須**完整保留本使用說明**，並確認**資料版本**；發現錯誤應無償回報教育部供修訂參考。
5. 教育部得因政策等事由**停止提供**資料；民眾不得請求賠償。

### 2.3 Creative Commons BY-ND 與「僅改格式」

CC BY-ND 3.0 TW deed 註腳明言：**僅改變格式不算創作衍生作品**。  
→ JSON／TSV／SQLite 等**格式轉換**通常可接受；**改寫詞目／相反詞字串、簡化字、合併改寫成新辭典**則踩線。

### 2.4 g0v 對教育部解釋的轉述

[g0v/moedict-data](https://github.com/g0v/moedict-data) README：

> 依教育部之解釋，「創用CC-姓名標示-禁止改作 臺灣3.0版授權條款」之**改作限制標的為文字資料本身，不限制格式轉換及後續應用**。  
> 辭典本文著作權仍屬教育部；格式轉換／重新編排之編輯著作權（若有）由 @kcwu 以 **CC0** 釋出。

此為**社群轉述**，非本報告取得之教育部函文；實務上與使用說明「不改條目內容可調整」方向一致，但合規風險仍宜以官方使用說明為準。

### 2.5 線上 FAQ 與下載授權之張力（必須注意）

線上辭典 FAQ【綜合】Q3（<https://dict.revised.moe.edu.tw/qa.jsp>）稱：資料「現階段之授權範圍**限於非商業用途**」、不同意以 APP **線上查詢／解析網頁**、不提供 API／框架連結。

此表述與公眾授權網「**包括商業性利用**」的**下載資料包**條款衝突。較穩健解讀：

| 路徑 | 建議判定 |
|------|----------|
| 官方 ZIP／XLSX 下載後離線利用 | 依 **CC BY-ND 3.0 TW**（商用可，禁止改作） |
| 爬取／解析 **dict.revised.moe.edu.tw** 網頁塞進 App | FAQ **明確反對**；即使內容同源，合規風險高 |

**不建議**為了附錄索引去爬網站；應從下載包欄位抽出相反詞。

### 2.6 與 Canto-0243 既有授權閘的兼容性

`CONTEXT.md`：**靜態詞林埠**「授權閘：只納可再分發者」。  
既有反義來源：`guotong`（Anti-996）、專案自建 `project_ant`、cilin（MIT，近義為主）。

MOE 資料：

- **可再分發**：是（含商用），但必須保留 BY-ND 與說明書。
- **不可**：把 MOE 相反詞「潤飾／擴寫／改詞」後當成自有 `project_ant`；或簡化字；或宣稱整包歌詞庫授權（Canto-0243 License／BY-NC-SA 系）覆蓋 MOE 內容。
- **建議交付**：獨立檔＋`THIRD_PARTY_NOTICES.md` 分列 BY-ND；執行期 lookup，**勿**混進「專案自建」權威清單。

---

## 3. Available download / data formats（可下載格式）

### 3.1 官方下載（2026-07-14 觀測）

下載頁提供兩類 ZIP（版本號隨更新變動；當日主檔為 `2015_20260625`）：

| 套件 | 用途 |
|------|------|
| `dict_revised_2015_YYYYMMDD.zip` | **文字資料庫** |
| `dict_revised_pic_2015_YYYYMMDD.zip` | **字圖**資料 |

本報告實際下載文字包  
`https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/download/dict_revised_2015_20260625.zip`  
（HTTP 200，約 30.6 MB）：

| ZIP 內容 | 說明 |
|----------|------|
| `dict_revised_2015_20260625.xlsx` | 主資料（約 31 MB；單一工作表，觀測名「1150625辭典匯出」） |
| 第二個小型 `.xlsx` | **欄位名稱／說明**對照（檔名在部分系統亂碼） |

**沒有**：獨立的「相反詞索引表」ZIP、XML 附錄檔、或 API。

### 3.2 主表欄位（官方 XLSX）

| 欄位 | 備註 |
|------|------|
| 字詞名 | lemma |
| 辭條別名、字數、字詞號 | 識別／編碼 |
| 部首字、總筆畫數、部首外筆畫數 | 單字字形資訊 |
| 多音排序 | `0`＝非多音；`1~6` 對應「(一)(二)…」 |
| 注音一式、漢語拼音、變體* | 國語標音（**無粵拼／0243**） |
| **相似詞** | 近義（複詞） |
| **相反詞** | 反義（複詞） |
| 釋義、多音參見訊息、異體字 | 全文／參見 |

觀測統計（同版 XLSX）：

- 資料列約 **163,920**
- 「相反詞」非空列約 **8,564**

### 3.3 社群處理格式（非官方，仍受 BY-ND 約束）

| 專案 | 內容 | 授權註記 |
|------|------|----------|
| [g0v/moedict-data](https://github.com/g0v/moedict-data) | 官方 XLSX 鏡像＋`dict-revised.json.xz` 等 | 本文 **教育部 BY-ND**；格式層 CC0（kcwu） |
| [g0v/moedict-process](https://github.com/g0v/moedict-process) | XLSX → JSON → SQLite；`definitions.antonyms`／`synonyms` | 同上 |
| [kemdict/kemdict-data-ministry-of-education](https://github.com/kemdict/kemdict-data-ministry-of-education) | 欄位對照（`相反詞`→`antonyms`）＋使用說明 PDF | 標明官方授權 |
| [PeterDaveHello/moedict-data-for-chewing-editor](https://github.com/PeterDaveHello/moedict-data-for-chewing-editor) | 取詞彙＋注音轉酷音；重申 BY-ND／格式轉換解釋 | 轉換層 CC0 |

未找到名為 **kevinhsu** 且專門託管本典相反詞之可靠鏡像；常見入口以 **g0v／kemdict** 為主。

---

## 4. Antonym index structure（相反詞結構）

### 4.1 網頁「相反詞索引表」

URL 模式：`appendix.jsp?ID=7`（英文附錄 ID 系列不同）。

頁首體例（現行頁）：

1. 本表依據**辭典本文**整理。  
2. 所有詞目均按**音序**（注音／Bopomofo）排列。  
3. 詞目有**義項分立**時，所列相反詞注明相對之義項別。

構造：

```text
注音索引（ㄅ…ㄩ） → 詞目（lemma） → 相反詞（頓號「、」分隔列表）
```

樣本（與下載頁同源之網頁／XLSX 開頭列一致）：

| 詞目 | 相反詞 |
|------|--------|
| 八面玲瓏 | 四處碰壁、處處碰壁 |
| 拔出 | 放入、插進 |
| 痛苦 | 開心、快樂、高興、歡樂、幸福、愉快 |
| 同意 | 反對、否決、拒絕 |

註音分區計數加總（現行 ID=7 頁索引列）：約 **8,603** 詞目列（與 XLSX 非空相反詞列 8,564 極接近；差異可能來自多音列展開／附錄去重方式）。

**義項標註**：部分歷史／英文「第四版」附錄以 `＊①`／`＊②` 標在相反詞字串上（例：`＊②處處碰壁、四處碰壁`、`敗北` → `＊①凱旋、勝仗＊②獲勝`）。  
**2026-06-25 官方 XLSX「相反詞」欄字串本身未見 `＊①` 標記**；多義／多音改以**獨立資料列**＋「多音排序」區分，例如：

| 字詞名 | 多音排序 | 相反詞（摘） |
|--------|----------|--------------|
| 來往 | 1 | 往返 |
| 來往 | 2 | 絕交 |
| 自然 | 1 | 人工、人造 |
| 自然 | 2 | 局促、牽強、勉強、做作… |

→ 技術上應以 **(字詞名, 多音排序) → 相反詞列表** 建模，而非假設一字面僅一組反義。

### 4.2 附錄是否可單獨下載？

**否。** 官方僅提供**全文文字資料庫 ZIP（XLSX）**與字圖 ZIP。  
相反詞索引表是線上附錄 UI；內容來自辭典本文之相反詞整理。  
機器可讀正途：**下載 XLSX → 抽出「字詞名／多音排序／相反詞」（及可選「相似詞」）**，等同附錄所需圖，且避開示 FAQ 之網頁解析問題。

---

## 5. Fit to Canto-0243（與產品適配）

依 `CONTEXT.md`：

- 產品核心是**粵語**詞條＝字面＋**粵拼**＋**394052／0243 碼**。
- **近反義模式**回傳近義／反義／語意相關；資料經**近反義池**，runtime 消費 **靜態詞林埠**（cilin＋guotong）與 `word_relations`。
- 已有 Mandarin 書面反義：**guotong** `dict_antonym.txt`（字面匹配，無粵拼）；另有**專案自建反義**。

MOE《修訂本》適配評估：

| 面向 | 適配情況 |
|------|----------|
| 字面（繁體漢字） | 多數與粵語書面語共寫；可對本庫字面做交集 lookup |
| 音韻（注音／拼音） | **國語**；不能直接當粵拼或 0243 |
| 反義語義 | 歷史語言辭典＋古今語料；對填詞「口語粵語」覆蓋不完全 |
| 義項／多音 | 需保留；否則「來往」「自然」會串錯反義 |
| 授權閘 | 可再分發，但 **ND** 比 MIT／專案自建更嚴；NOTICE 負擔重於 cilin |
| 與 guotong 關係 | 同屬「國語字面反義」族；匯入前應度量**重疊率／增量**，避免白做 |

**缺口**：匯入不會自動產生粵拼詞條；只能幫「字面已在粵語詞庫」的頭找反義候選，再靠本庫投影到有碼詞條。國語獨有詞、文言義、與粵語日常反義習慣不合者，品質不保證。

---

## 6. Verdict（裁決）

### **yes-with-conditions**

**可以**把官方下載包中的相反詞（與可選相似詞）納入 Canto-0243 的近反義資料管線，前提是遵守下列條件並採建議做法。

### 建議做法（若「要做」）

1. **只從官方 ZIP／XLSX（或已標明同源的 g0v 鏡像）取資料**；不要爬 `appendix.jsp`／線上查詞頁。  
2. **格式轉換 only**：產出例如 `moe_dict_antonyms.tsv`＝`lemma \t het_sort \t antonyms_raw`（字串保持原頓號分隔）；可选并行 `相似詞`。  
3. **不改**詞目／相反詞內容、不做簡化字、不用 LLM 依 MOE 表擴寫成 `project_ant`。  
4. **完整保留**公眾授權使用說明＋版本號（如 `2015_20260625`），並在 `THIRD_PARTY_NOTICES.md`／關於頁標示教育部 BY-ND。  
5. **執行期**以字面對粵語詞庫做交集過濾；建議**仍打包完整抽出檔**（避免發布「剪裁後改作」爭議）。  
6. source 標記獨立（如 `moe_revised`），與 `guotong`／`project_ant` **並存**、可度量重疊。  
7. 若只想補反義覆蓋：先對比 guotong／`project_ant` 的增量；增量小則**YAGNI——不必匯入**。

### 什麼時候應判 **no**

- 需要**改寫**教育部反義以遷就粵語口語；或  
- 無法接受 BY-ND 標示／說明書／不得改作拘束；或  
- 計劃以網頁 scraping 當更新管線。

---

## 7. Open questions / risks（待決與風險）

1. **FAQ「限非商業」** vs 公眾授權「含商用」：下載包路徑較明確，但仍建議必要時向 `onile@mail.naer.edu.tw`（FAQ／使用說明聯絡）書面確認「離線開源工具 embedding 抽出之相反詞欄」是否符合其政策。  
2. **ND 與「過濾後再分發」**：嚴格解讀下，發布大幅刪減子集可能被視為改作；執行期過濾 + 完整抽出檔較穩。  
3. **多音／義項**：網頁附錄 `＊①` 與 XLSX `多音排序` 是否永遠等價，需抽樣對照。  
4. **產品價值**：相對已有 guotong＋專案自建，MOE 增量與粵語填詞體感是否值得 NOTICE／合規成本。  
5. **停止提供權**：使用說明允許教育部停供；應固定版本號、保留當時 ZIP 校驗資訊。  
6. **鏡像滯後**：g0v `dict_revised` README 曾標 `20220922`，官方已更新至 `20260625`；生產應釘官方下載或可驗證 checksum。  
7. **法律免責**：本文件為技術／公開授權條款整理，**不是**律師意見。

---

## 參考連結速查

| 項目 | URL |
|------|-----|
| 資料下載 | https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/dict_reviseddict_download.html |
| 公眾授權總頁 | https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/respub/index.html |
| 相反詞索引表 | https://dict.revised.moe.edu.tw/appendix.jsp?ID=7 |
| CC BY-ND 3.0 TW | https://creativecommons.org/licenses/by-nd/3.0/tw/ |
| 使用說明（鏡像 PDF） | https://kemdict.com/l/reviseddict_10312.pdf |
| 線上 FAQ | https://dict.revised.moe.edu.tw/qa.jsp |
| g0v 資料 | https://github.com/g0v/moedict-data |
| g0v 處理管線 | https://github.com/g0v/moedict-process |

---

*觀測基準日：2026-07-14；官方 ZIP 抽樣版本：`dict_revised_2015_20260625`。*
