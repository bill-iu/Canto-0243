# ADR-0048: 搜尋 UX — 導航、詳情、視窗化與查詢語意解釋

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 查詢語意解釋、搜尋結果視窗化、擷取頁、呈現批次。

整合並取代：[0019](./0019-search-result-navigation-history.md)、[0020](./0020-per-tab-search-history-stack.md)、[0021](./0021-search-usability-layer.md)、[0030](./0030-entry-detail-panel.md)、[0034](./0034-search-result-windowing.md)。

## 1. 分頁搜尋歷史

1. 結果列連到詞條詳情時，**每查詢分頁**各自 history stack（前進／後退），唔共用單一全局棧。
2. 導航唔破壞分頁隔離。

## 2. 詞條詳情

1. 搜尋清單精簡 + 詳情面板；Portable／PWA 共用 core 模型，資料路徑分渠。

## 3. 結果視窗化

1. **擷取頁** vs **呈現批次**（DOM +400）分離。
2. 首屏擷取 400、上限 800（0243 家族）；近反義沿用細頁。
3. 僅結果捲動區 scroll 觸發擴批；引擎只為當前窗口 sort／serialize。

## 4. 查詢語意解釋（原 ADR-0021）

創作者面對位置敏感錨語法時，搜尋框下（debounce）顯示 **查詢語意解釋**。**唔改** parse／dispatch 行為。

### 演算法形狀

1. `normalize_and_parse` → `ParsedQuery`
2. `build_match_spec_for_parsed` → **比對規格**（同分派 registry）
3. 由左至右掃 slot；等號整詞一句 + **押韻標註**；缺字逐字約束；無規格最短句
4. 位置易混 **warning** 在 summary **下方**，唔取代之

無 MatchSpec 的 kind（lookup、純碼、近反義、粵拼片段、unmatched）只靠 `ParsedQuery` 最短句。

### 雙引擎

| 渠道 | 路徑 |
|------|------|
| Portable | `GET /words/query/explain` → Python `explain_query` |
| PWA | 本地 `explainQuery`（唔需 DB） |

共用演算法形狀；漂移由 `contracts/query-explain-parity.json` + smoke／self-check 閘住。  
**禁止**第三套 client-only parse／自創槽語。

### 創作者文案規則（SSOT）

- 位置：**第 N 個字**（唔用格／槽）
- 通配：**任意字**
- 碼：**同 {digit} 同音**
- 音素錨：同「字」同韻／同聲；粵拼片段：同片段同韻母／聲母
- 整詞等號：一句 + 押韻標註（N 字 = N 押，無 cap）
- 前綴通配等號：首字任意 + 第 2…n 同參考詞 + 押韻標註
- 左碼整詞等號：押韻標跟參考詞長；碼約束另句
- 近反義 lookup：**近義詞**／**反義詞**

**Consequences** — 常數雙端對齊；大結果集唔一次畫滿擷取頁；改文案須雙端 + parity 契約。
