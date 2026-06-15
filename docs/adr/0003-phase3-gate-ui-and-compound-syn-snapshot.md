# Phase 3：就緒閘前端極薄化與近義複合快照

Phase 1 就緒閘改由 server 單點契約（ADR-0001）後，前端不應保留第二份 gate policy（本地 30 秒解鎖、`canOpenSearchGate` 規則）或 Python 鏡像測試。我們決定：Phase 3 先做 **#6**——`waitForPreloadReady` 僅 poll `/ready` 並依 `gate_ready`／`degraded` 呈現進度與文案；連線失敗可暫停動畫但不自行解鎖；policy 測試集中在 `readiness_gate`。再做 **#5**——deep **近義複合**模組對外提供 **近義複合快照**（curated ∩ 詞庫 + 同義素掃描），`search_compound_syn` 於查詢時追加單字近義合成（源 3）並 union 去重；第一版不為源 3 加跨請求 LRU。

**Considered Options**

- 抽出 `gate_client.js` 並以 Vitest 測 poll budget — 與 server 逾時重複，維護兩份 policy。
- 啟動時預算 ~~ 三源全 union — 與 CONTEXT 及冷啟動成本衝突。
- 源 3 查詢級 LRU — 可作效能優化，但超出 Phase 3 收斂模組的範圍。

**Consequences**

- `test_gate_budget` 鏡像邏輯可刪或改為 API／policy 整合測。
- PR 順序：PR5（#6）依賴 PR1；PR6（#5）可獨立於 Phase 2 之後進行。
