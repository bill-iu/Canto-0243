# 就緒閘前端極薄化與近義複合快照

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 就緒閘、近義複合詞、近義複合快照、源 3 tier 快取。

ADR-0001 之後，前端不應保留第二份 gate policy（本地逾時解鎖、`canOpenSearchGate` 規則）或 Python 鏡像測試；`waitForPreloadReady` 僅 poll `/ready` 並依 snapshot 呈現進度，連線失敗可暫停動畫但不自行解鎖。近義複合由單一模組對外提供**近義複合快照**；`search_compound_syn` 於查詢時追加**單字近義合成**（源 3）並 union 去重（候選規則見 CONTEXT）。

**Considered Options**

- 抽出 `gate_client.js` 並以 Vitest 測 poll budget — 與 server 逾時重複，維護兩份 policy。
- 啟動時預算 `~~` 三源全 union — 與 CONTEXT 及冷啟動成本衝突。
- 源 3 跨請求 LRU — 可作效能優化，超出本階段收斂模組的範圍。

**Consequences**

- `test_gate_budget` 等鏡像邏輯可刪，改為 API／`readiness_gate` policy 整合測。
- 近義複合快照模組化可獨立於缺字型 seam 之後進行。