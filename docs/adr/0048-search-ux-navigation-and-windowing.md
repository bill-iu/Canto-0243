# ADR-0048: 搜尋 UX — 導航歷史、可用性層與結果視窗化

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 查詢語意解釋、搜尋結果視窗化、擷取頁、呈現批次。

整合並取代：[0019](./0019-search-result-navigation-history.md)、[0020](./0020-per-tab-search-history-stack.md)、[0021](./0021-search-usability-layer.md) 之導航相關、[0030](./0030-entry-detail-panel.md)、[0034](./0034-search-result-windowing.md)。0021 其餘可用性細節若未收入以 git 為準。

## 1. 分頁搜尋歷史

1. 結果列連到詞條詳情時，**每查詢分頁**各自 history stack（前進／後退），唔共用單一全局棧。
2. 導航唔破壞分頁隔離。

## 2. 詞條詳情

1. 搜尋清單精簡 + 詳情面板；Portable／PWA 共用 core 模型，資料路徑分渠。

## 3. 結果視窗化

1. **擷取頁** vs **呈現批次**（DOM +400）分離。
2. 首屏擷取 400、上限 800（0243 家族）；近反義沿用細頁。
3. 僅結果捲動區 scroll 觸發擴批；引擎只為當前窗口 sort／serialize。

## 4. 查詢語意解釋

1. 文案規則 SSOT 見 **[ADR-0021](./0021-search-usability-layer.md)**（仍為活檔）；雙引擎各一實作 + `contracts/query-explain-parity.json`。

**Consequences** — 常數雙端對齊；大結果集唔一次畫滿擷取頁。
