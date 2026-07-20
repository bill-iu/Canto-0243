# ADR-0064: Workbench candidate page size 400 + load-more

句格工作台曾硬截 `limit: 120`，令 `300`（m1）只見 ~120，而主搜尋同池顯示 **結果數** 384。Grill 共識：當 bug，對齊搜尋**首屏擷取** 400，並加共用「載入更多」（每批 +400，無全域硬頂）。

## Decision

1. **單次請求** `limit` 上限由 120 改為 **400**（`WORKBENCH_CANDIDATE_PAGE_SIZE`）；契約加可選 **`offset`**（預設 0）。
2. 回應必帶引擎池 **`total`**（排序後、詞性篩選前）。UI：「已載 N／池內 M」；啟用創作者詞性篩時「篩後 N／池內 M」。
3. **一掣共用續載**：同一 MatchSpec 分頁；三分組係頁內投影，唔各自 offset。
4. **PWA + Portable** schema／planner 一齊改。
5. 續載 **無** 800 硬頂（與搜尋擷取頁上限刻意唔綁死）；成本靠每批 400 線性控制。

## Considered

| Option | Result |
|--------|--------|
| Keep 120 + clarify copy only | Rejected — user chose fix counts |
| Cap at 800 like search | Rejected — chose uncapped +400 batches |
| Auto infinite scroll | Rejected — explicit button |
| PWA-only contract | Rejected — dual-port parity |

## Consequences

- Self-checks／JSON schema／Pydantic 跟 400 + `total`。
- CONTEXT **擷取頁**／**結果數** 補工作台語意。
- 大池（≫400）要點「載入更多」先睇晒；首屏已覆蓋常見碼查（如 384）。
