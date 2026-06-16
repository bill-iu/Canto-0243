# 就緒閘由 server 契約單點強制

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 就緒閘、降級逾時、詞庫快取索引、離線啟動預載。

曾出現前端 poll `/ready` 與搜尋 API 各算各的就緒狀態（含前端自行逾時解鎖、API 靜默 DB 降級）。我們決定：**就緒閘**解鎖真相由 `app/startup/readiness_gate.py` 單點定義；凡經**查詢分派**的搜尋請求，閘未解鎖前 server 拒絕（503），與 UI 一致；`/ready` 與前端只消費同一份 snapshot。

**Considered Options**

- 僅前端隱藏搜尋列、API 靜默 DB 降級 — 與「阻擋搜尋」產品行為不符，且易出現 UI 已開、請求仍失敗或仍慢查的割裂。
- 前端自行逾時解鎖、server 等真正就緒 — 與 API 強制拒絕衝突。
- 就緒閘 policy 留在 `offline_preload.py` — 編排與解鎖規則混檔，不利測試與索引拆分。

**Consequences**

- 關係補錄等不經**查詢分派**的路由不受就緒閘影響。
- 預載中繞過 UI 直打搜尋 API 將收到 503，直至就緒、`failed` 或**降級逾時**。
- 503 body 與 `GET /ready` 回傳相同 flat JSON（`readiness_gate.snapshot()`），不用 FastAPI `{"detail": …}` 包裝；建議加 `Retry-After: 1`。
- Snapshot 含 `degraded` 與 `gate_open_reason`（`ready` | `failed` | `degraded` | `null`）；`gate_ready` 為三者之一即 true。
- Policy 測試集中在 `readiness_gate`，不必鏡像前端 state machine。