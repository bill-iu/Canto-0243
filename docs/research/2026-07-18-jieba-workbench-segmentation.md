# jieba 作為句格工作台分詞 — 研究

**日期**: 2026-07-18  
**問題**: 是否應將 [fxsjy/jieba](https://github.com/fxsjy/jieba) 引入 Canto-0243「句格工作台」(Line Grid Workbench) 作為分詞功能？  
**結論摘要**: **不建議引入 jieba（含 Python 原版與瀏覽器 jieba-wasm）作為工作台執行期依賴。** 句格工作台的 SSOT 單位是**逐 Unicode 字位**與 **1–4 字連續替換段**，不是 NLP 詞級切分；設計規格亦未要求自動斷詞，且明確拒絕在無可信資料時推斷詞性。jieba 預設詞典偏普通話／簡體語料、詞長常超出 4 字上限、離線 PWA 載入成本高（web `.wasm` 約 4 MB）。若將來要「一鍵選一整個詞」這類 UX 提示，**更懶、更貼產品的做法**是對既有詞庫字面做最長匹配（words.hk／rime／Essay），無需 jieba。

---

## 1. 背景與需求對齊

### 1.1 產品約束

Canto-0243 是粵語／粵拼／0243 碼導向的歌詞／填詞工具：離線 PWA（sql.js／wa-sqlite）＋ Portable／Python 服務雙端；詞條 SSOT 來自 rime、words.hk、Essay 詞頻等（見 `CONTEXT.md` § 詞庫與排序；`data/lexicon/sources.yaml`）。

句格工作台定位（設計規格）：

> 創作者可貼入一句半成品、394052／0243 碼或平仄，系統拆成**逐字句格**；創作者圈選 **1–4 個連續字位**後，以現有詞條庫、MatchSpec、近反義池與詞頻，在本機找出可替換詞……

來源：`docs/superpowers/specs/2026-07-17-line-grid-workbench-design.md` §1、§3.1。

產品邊界要求創作決定由用戶確認；非目標包含「在沒有可信資料時推斷詞性、地域或『書面／口語』等語體標籤」。  
來源：同上 §1.1、§3.2。

### 1.2 本研究所問的「分詞」

不是「候選是否為多字詞條」（工作台已透過 `width` 與詞庫字面長度對齊），而是：**是否要用外部 NLP 分詞器（jieba）把整句切成詞，再驅動選段／候選／提示**。

---

## 2. jieba 一手事實

### 2.1 定位與授權

| 項目 | 事實 | 來源 |
|------|------|------|
| 定位 | Python 中文分詞組件；四種模式：精確、全模式、搜尋引擎、paddle | [README](https://raw.githubusercontent.com/fxsjy/jieba/master/README.md) |
| 授權 | **MIT**；可商用、嵌入、再分發，須保留版權與許可聲明 | [LICENSE](https://raw.githubusercontent.com/fxsjy/jieba/master/LICENSE)；PyPI `jieba` 0.42.1 `license: MIT` |
| 與本專案 | 授權本身**不構成否決**（MIT 寬於下游常見限制） | 同上 |

### 2.2 核心 API（與工作台可能相關者）

摘自官方 README：

| API | 行為 |
|-----|------|
| `jieba.cut(s, cut_all=False, HMM=True, …)` | 精確／全模式；HMM 處理未登錄詞 |
| `jieba.cut_for_search(s)` | 在精確切分上再切長詞，提高召回 |
| `jieba.lcut`／`lcut_for_search` | 直接回傳 `list` |
| `jieba.Tokenizer(dictionary=…)` | 獨立詞典實例；`jieba.dt` 為預設 |
| `load_userdict`／`add_word`／`del_word`／`suggest_freq` | 自訂詞典與詞頻調節 |
| `jieba.tokenize` | 回傳詞在原文的起止位置 |
| `jieba.posseg` | 詞性標注（ictclas 相容標記；另有 paddle POS） |

算法自述：前綴詞典掃描 → DAG → 動態規劃最大機率路徑；未登錄詞用 HMM＋Viterbi。  
來源：[README「算法」「主要功能」](https://raw.githubusercontent.com/fxsjy/jieba/master/README.md)。

### 2.3 詞典語言偏置（繁體／粵語）

官方明確：

- 功能列表寫「**支持繁体分词**」。
- 預設內建 `jieba/dict.txt`；另提供 `extra_dict/dict.txt.big`，README 稱其「**支持繁体分词更好**」。
- 英文說明：bigger dictionary has better support for traditional Chinese；預設是中間體積的 `dict.txt`。

來源：[README「其他詞典」](https://raw.githubusercontent.com/fxsjy/jieba/master/README.md)；作者在 [#67](https://github.com/fxsjy/jieba/issues/67)（2013）：「默认的 dict.txt 是没有繁体字的」（歷史陳述；現版默認檔已含部分繁／粵用字，見下）。

本機對 `jieba/dict.txt`（Content-Length **5 071 852** bytes，約 4.8 MiB）抽樣（2026-07-18）：

| 字面 | 詞頻欄（檔內） | 觀察 |
|------|----------------|------|
| `是` | 796991 | 普通話高頻虛詞 |
| `的` | 318825 | 同上 |
| `不` | 360331 | 同上 |
| `喜欢` | 9783 | 簡體詞形 |
| `粤语` | 43 | 簡體寫法 |
| `係` | 5 | 粵語常見字，但頻次極低 |
| `唔` | 476 | 有收入，頻次遠低於普通話對照 |
| `嚟` | 40 | 有收入 |

預設詞典**並非純粵語模型**：詞頻與詞形仍以普通話／簡體書面語為主；粵語口語、歌詞異體、繁體書面詞需靠 `dict.txt.big`＋大量 `userdict` 才能勉強貼近。HMM 新詞發現亦按「漢字成詞能力」訓練，**無粵語語域保證**。

`dict.txt.big`：Content-Length **8 583 143** bytes（約 8.2 MiB）。  
來源：GitHub raw headers（`jieba/dict.txt`、`extra_dict/dict.txt.big`）。

### 2.4 套件體積與離線載入

| 產物 | 大小（一手量測） | 含義 |
|------|------------------|------|
| PyPI `jieba-0.42.1.tar.gz` | **19 214 172** bytes（~18.3 MiB） | 含默認詞典；服務端可接受，但非「輕依賴」 |
| 默認 `dict.txt` | ~4.8 MiB | 首次 `initialize`／首次 `cut` 才載入（延遲載入） |
| npm `jieba-wasm@2.4.0` tarball | **11 307 535** bytes；`unpackedSize` **16 126 591** | 含多 target |
| `pkg/web/jieba_rs_wasm_bg.wasm` | **4 015 140** bytes（~3.8 MiB） | 瀏覽器實際下載主體（另加 JS glue） |

來源：PyPI JSON；npm package metadata；本機解包量測 `/tmp/jieba-wasm.tgz`。

延遲載入：`import jieba` 不立刻建前綴樹；首次分詞才載詞典。  
來源：README「延迟加载机制」。

### 2.5 瀏覽器／JS 移植（非官方原版）

官方 README「其他语言实现」列出 Java／C++／**Rust (`messense/jieba-rs`)**／**Node (`yanyiwu/nodejieba`)** 等，**沒有**官方「瀏覽器 WASM」條目。  
來源：[README「其他语言实现」](https://raw.githubusercontent.com/fxsjy/jieba/master/README.md)。

社群方案：

| 方案 | 關係 | 與原版差距（一手） |
|------|------|-------------------|
| [fengkx/jieba-wasm](https://github.com/fengkx/jieba-wasm) | **jieba-rs** 的 WASM binding（非直接包 Python jieba） | README：`cut`／`cut_all`／`cut_for_search`／`tokenize`／`add_word` 等；瀏覽器須 `await init()` |
| [cxumol/jieba-wasm-html](https://github.com/cxumol/jieba-wasm-html) | 基於 jieba-wasm 的純前端示範 | Future plan 仍列未完成的 API 擴充 |
| `yanyiwu/nodejieba` | Node native addon | 不適合 PWA 瀏覽器端 |

授權：jieba-wasm 標 MIT（npm `license: MIT`）。

**結論**：離線 PWA 若硬嵌 jieba，現實路徑是 **~4 MB wasm＋詞典資料**，且行為對齊 **jieba-rs**，不是 Python `fxsjy/jieba` 位元級一致；paddle 模式亦不適用於瀏覽器。

---

## 3. 句格工作台現況

### 3.1 設計：逐字句格，非詞級畫布

| 規格要點 | 含義 |
|----------|------|
| 「拆成逐字句格」 | 畫布單位是字位，不是 jieba 詞 |
| 選段 **1–4 連續字位** | 與詞庫候選長度契約綁死 |
| 候選用現有詞條庫／MatchSpec | 不新建第三套查詢引擎 |
| 非目標：推斷詞性／語體 | 與 `jieba.posseg` 方向衝突 |

來源：`docs/superpowers/specs/2026-07-17-line-grid-workbench-design.md` §1、§3.1–3.2、§5–6。  
Phase 2 只加「放入句格／搜尋查看／批量鎖／鍵盤捷徑」，**仍無分詞需求**。  
來源：`docs/superpowers/specs/2026-07-17-line-grid-workbench-phase2-design.md` §1。

### 3.2 實作：按 Unicode 碼點拆槽

客戶端輸入解析：

```22:58:client/src/workbench/line-input.ts
export function parseLineInput(raw: string): ParsedLineInput {
  const input = raw.trim();
  // ...
  const values = Array.from(input);
  // ...
  return {
    ok: true,
    kind: 'surface',
    slots: values.map((surface) => ({ surface })),
    constraints: [],
  };
}
```

伺服端讀音解析同樣「每個 Unicode code point 獨立」：

```92:94:app/services/workbench/line_readings.py
def resolve_line_readings(surface: str, db, *, allow_inject: bool = True) -> tuple[LineReadingSlot, ...]:
    """Resolve each Unicode code point independently; unresolved slots remain editable."""
    return tuple(_resolve_slot(value, db, allow_inject=allow_inject) for value in surface)
```

替換段寬度硬上限 4：

```14:16:client/src/workbench/replacement-span.ts
  const width = end - start + 1;
  if (width < 1 || width > 4) return null;
```

契約：`ReplacementPlanV1.width`／候選 `literal` 皆 `ge=1, le=4`。  
來源：`app/schemas/workbench_schema.py`。

**現況裁決**：工作台是**按字**建格；「詞」只出現在**候選結果**（詞庫裡長度＝選段寬度的字面），不是輸入拆句的單位。

### 3.3 若引入分詞，表面上能對應的用戶問題

| 假設痛點 | 現況已覆蓋？ | jieba 是否必要？ |
|----------|--------------|------------------|
| 一次選「成語／詞組」整段 | 用戶點 1–4 字位鎖定；批量鎖（Phase 2） | 否；最多要**提示邊界** |
| 候選以詞為單位 | 已是：`width` 對齊詞庫字面長度 | 否 |
| 歌詞斷詞提示／閱讀輔助 | **規格未要求** | 可選 UX；非核心 |
| 語意種子用「詞」而非「字串切片」 | `semantic_seed` 已是選段字面拼接（≤4） | 否 |

---

## 4. 契合度評估

| 維度 | 評估 | 說明 |
|------|------|------|
| 單位模型 | **衝突** | jieba 輸出詞級；工作台 SSOT 是字位＋≤4 選段。長詞（如 README 例「清華大學」）超出 `width≤4`，無法直接當選段 |
| 規格需求 | **無** | 設計／Phase 2 皆無「自動分詞」；非目標排斥無據詞性推斷 |
| 語言適配 | **差** | 預設詞典偏普通話／簡體；粵語歌詞／口語需大改詞典才可靠 |
| 離線 PWA | **差** | 服務端 jieba 破壞雙端一致；瀏覽器需 ~4 MB wasm，且非官方 Python 同構 |
| 與現有詞庫 | **重疊且劣於自有資料** | 產品已有粵語詞面＋Essay 頻次；jieba 詞頻是另一套普通話語料 |
| 工程／YAGNI | **不划算** | 新依賴、雙端契約、詞典維護；對 60 秒選段→套用主路徑幾乎無增益 |
| 授權 | **可** | MIT，不構成阻擋 |

---

## 5. 替代方案

### 5.1 維持現況：純按字＋UI 選段（**預設建議**）

已滿足規格：逐字句格、1–4 鎖段、候選＝詞庫。零新依賴。符合 ponytail／YAGNI。

### 5.2 既有詞庫最長匹配（**若真要「詞邊界提示」時的懶方案**）

對 `LineDraft.slots` 做向前最長匹配：只認**已在本機詞庫／Essay 類型**、且長度 ∈ [2,4] 的字面，畫虛線建議或「一鍵鎖此詞」。

| 優點 | 缺點 |
|------|------|
| 與候選 SSOT 同一套字面 | 歧義仍在（需用戶確認） |
| 無額外 MB 依賴；PWA 離線天然可用 | 不是通用 NLP 分詞器 |
| 粵語覆蓋跟產品詞庫走 | 罕用語／未收歌詞造詞仍切不開（可接受：未收則不當「詞」） |

### 5.3 簡體 jieba ＋自訂粵語詞典

理論可行（`load_userdict`／`set_dictionary`），但仍要：選 `dict.txt.big`、匯出本庫為 userdict、服務端／wasm 雙端、處理 >4 字切分。**成本高於 5.2，收益幾乎相同。**

### 5.4 其他粵語／繁體友好分詞器（簡評）

| 選項 | 一手事實 | 對工作台 |
|------|----------|----------|
| [PyCantonese `segment`](https://docs.pycantonese.org/stable/word_segmentation.html) | 官方文件：Jieba-styled DAG+HMM；訓練資料含 HKCanCor、rime-cantonese、Common Voice 粵語等；MIT（`jacksonllee/pycantonese` LICENSE） | 語言適配優於原版 jieba，但仍是**執行期 NLP 依賴**；主路徑在 Python，瀏覽器需 Pyodide／WASM 輪子，體積與複雜度更高。規格仍無剛需 → **現階段不引入** |
| HKCanCor 分詞標注 | 既有研究已評：POS／分詞對本產品低價值 | 見 `docs/research/2026-07-17-hkcancor-lexicon-fit.md` §6(c) |

---

## 6. 建議

### 主建議

**不引入 jieba。** 句格工作台保持「按字建格、用戶鎖 1–4 字、詞庫出候選」。授權友好、社群有 wasm，都**解決唔到**單位模型衝突與粵語詞典偏置；離線 PWA 還要吞約 4 MB。

### 若試做：最小實驗（僅當產品明確要「詞邊界提示」）

1. **不要**先裝 jieba。  
2. 用本機詞庫字面（長度 2–4）對一句測試歌詞做最長匹配，量：建議段與用戶手動鎖段的重合率、誤鎖率。  
3. 若重合率高且用戶故事成立，再做**可選** UI hint（須用戶確認才鎖），仍不改 `parseLineInput` 的按字拆槽。  
4. 只有當「詞庫最長匹配」明顯失敗、且失敗主因是「庫外成詞」時，才值得對照評測 PyCantonese／jieba＋粵語 userdict——作為**研究對照**，不是預設依賴。

### 不建議做的事

- 把 jieba／jieba-wasm 塞進 PWA 冷啟動路徑。  
- 用 `jieba.posseg` 或 paddle 推詞性／語體（違反規格非目標）。  
- 用 jieba 切分結果**自動**改 `LineSlot` 邊界或自動套用候選（違反「創作決定由用戶確認」）。  
- 為了服務端方便單端跑 jieba，破壞 Portable／PWA 結果契約一致。  
- 建庫時預計算「全庫分詞」——工作台輸入是用戶當句草稿，預計算對不上。

### Ponytail 一句

**用現有詞庫做 ≤4 字最長匹配，比引入 jieba 更懶、更正確。**

---

## 來源

### jieba／移植

- <https://github.com/fxsjy/jieba>
- <https://raw.githubusercontent.com/fxsjy/jieba/master/README.md>
- <https://raw.githubusercontent.com/fxsjy/jieba/master/LICENSE>
- <https://github.com/fxsjy/jieba/issues/67>（繁簡／默認詞典）
- <https://raw.githubusercontent.com/fxsjy/jieba/master/jieba/dict.txt>（大小與詞頻抽樣）
- <https://raw.githubusercontent.com/fxsjy/jieba/master/extra_dict/dict.txt.big>
- <https://pypi.org/pypi/jieba/json>（0.42.1、MIT、sdist 大小）
- <https://github.com/fengkx/jieba-wasm>／npm `jieba-wasm@2.4.0`（web `.wasm` ≈ 4 015 140 bytes）
- <https://github.com/messense/jieba-rs>（官方 README 所列 Rust 實作）
- <https://github.com/cxumol/jieba-wasm-html>

### 粵語替代（對照）

- <https://docs.pycantonese.org/stable/word_segmentation.html>
- <https://github.com/jacksonllee/pycantonese>（MIT LICENSE）
- `docs/research/2026-07-17-hkcancor-lexicon-fit.md`

### 本專案

- `docs/superpowers/specs/2026-07-17-line-grid-workbench-design.md`
- `docs/superpowers/specs/2026-07-17-line-grid-workbench-phase2-design.md`
- `client/src/workbench/line-input.ts`
- `client/src/workbench/replacement-span.ts`
- `app/services/workbench/line_readings.py`
- `app/schemas/workbench_schema.py`
- `CONTEXT.md`（詞庫／Essay）
- `data/lexicon/sources.yaml`
