# 缺字型查詢：正規化在查詢分派、執行層只收比對規格

缺字型家族的 ParsedQuery→MatchSpec 轉換與 `execute_mask_family_search` 內的 isinstance 分派梯，使新語法需同步改 `query_parse`、`query_dispatch`、`position_match` 三處。我們決定：Phase 2 先將**缺字型家族**（七種 ParsedQuery）的正規化收進 **查詢分派**（`QueryEngine`），再讓**缺字型查詢執行**只接收正規化後的比對規格（`execute_match_spec`），不再依 ParsedQuery 型別分支；`HybridTailEqualsAlias` 等別名改寫亦在分派層完成。其餘路徑（近反義關係查詢、近義複合詞、`WordLookup` 等）維持現有 executor。交付拆為兩 PR：PR3 搬正規化（#4），PR4 換執行 registry（#3）。

**Considered Options**

- 正規化留在 `position_match` — 與「查詢分派」領域定義衝突，執行層持續綁語法型別。
- 執行層仍收 ParsedQuery、只換 registry 實作 — 正規化已上移但 seam 仍洩漏分類型別。
- Phase 2 一次合併 #3+#4 單 PR — review 與 rollback 面過大。

**Consequences**

- 新增缺字語法時，預期只改 `query_parse`（分類）與 `QueryEngine`（正規化／路由）；`position_match` 變更應限於候選來源與比對引擎。
- `EqualsQuery` 若保留 `run_equals_query` 快路徑，由 `QueryEngine` 顯式分支，不將 ParsedQuery 傳入執行模組。
