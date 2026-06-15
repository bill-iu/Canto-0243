# 就緒閘由 server 契約單點強制

離線查韻啟動時，**詞庫快取索引**預載與**就緒閘**曾分裂：前端以 poll `/ready` 決定是否解鎖搜尋列，但搜尋 API 在索引未就緒時仍可走 DB 降級，且前端 30 秒逾時可解鎖 UI 而 server 仍視為未就緒。我們決定：**就緒閘**改由 `app/startup/readiness_gate.py` 的 policy 模組定義唯一解鎖真相（含 **降級逾時** 與 `failed` 立即解鎖）；凡經**查詢分派**的搜尋請求，在閘未解鎖前 server 拒絕（503），與 UI 一致。`/ready` 與前端只消費同一份 snapshot，不再各自倒數逾時。實作順序：先交付此契約（PR1），再拆**詞庫快取索引**與 adapter（PR2）。

**Considered Options**

- 僅前端隱藏搜尋列、API 靜默 DB 降級 — 與「阻擋搜尋」產品行為不符，且易出現 UI 已開、請求仍失敗或仍慢查的割裂。
- 前端 30 秒解鎖、server 等真正就緒 — 與 API 強制拒絕衝突。
- 就緒閘 policy 留在 `offline_preload.py` — 編排與解鎖規則混檔，不利測試與 PR2 索引拆分。

**Consequences**

- `test_gate_*` 改測 policy 模組，不必鏡像 JS state machine。
- 關係補錄等不經查詢分派的路由不受就緒閘影響。
- 預載中繞過 UI 直打搜尋 API 將收到 503，直至就緒、failed 或降級逾時。
- **503 body schema**：與 `GET /ready` 回傳**相同 flat JSON**（`readiness_gate.snapshot()`），不用 FastAPI `{"detail": …}` 包裝；客戶端可共用同一 parser。建議加 `Retry-After: 1`。
- Snapshot 新增 `degraded`（降級逾時已觸發）與 `gate_open_reason`（`ready` | `failed` | `degraded` | `null`）；`gate_ready` 為三者之一即 true。
