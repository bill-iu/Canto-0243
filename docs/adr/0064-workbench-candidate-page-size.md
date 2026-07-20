# ADR-0064: Workbench candidate page size 400 + load-more

句格工作台曾硬截 `limit: 120`，令 `300`（m1）只見 ~120，而主搜尋同池顯示 **結果數** 384。Grill 共識：當 bug，對齊搜尋**首屏擷取** 400，並加共用「載入更多」（每批 +400，無全域硬頂）。

## Decision

1. **單次請求** `limit` 上限由 120 改為 **400**（`WORKBENCH_CANDIDATE_PAGE_SIZE`）；契約加可選 **`offset`**（預設 0）。
2. 回應必帶引擎池 **`total`**（排序後、**詞性篩選前**）。UI：「已載 N／池內 M」；啟用創作者詞性篩時「篩後 N／池內 M」。
3. **一掣共用續載**：同一 MatchSpec 分頁；三分組係頁內投影，唔各自 offset。
4. **PWA + Portable** schema／planner 一齊改。
5. 續載 **無** 800 硬頂（與搜尋擷取頁上限刻意唔綁死）；成本靠每批 400 線性控制。
6. **創作者詞性篩（client）** — 篩選喺引擎分頁**之後**。啟用篩選時 UI 必須 **auto over-fetch** 引擎頁，直到 **篩後累積 ≥ 當前目標**（首屏 400；每次「載入更多」再 +400）或引擎池盡。用戶體感嘅「一批」以**篩後**計，唔好每批引擎 400 只露出 1–2 張卡。
7. **全寬 dense 碼桶** — 有完整 width 位 0243 碼時，length-bucket 來源 **唔**用 `LIMIT 2000 + ORDER BY char` 截斷（截斷後再 essay 排序會漏高頻字，如工作台「貪婪」→`30` 漏「金錢」）。

## Considered

| Option | Result |
|--------|--------|
| Keep 120 + clarify copy only | Rejected — user chose fix counts |
| Cap at 800 like search | Rejected — chose uncapped +400 batches |
| Auto infinite scroll | Rejected — explicit button |
| PWA-only contract | Rejected — dual-port parity |
| POS: one huge engine limit | Rejected — prefer over-fetch batches of 400 |
| POS: server-side POS in MatchSpec | Deferred — dual-port cost; client over-fetch first |

## Consequences

- Self-checks／JSON schema／Pydantic 跟 400 + `total`。
- CONTEXT **擷取頁**／**結果數** 補工作台語意。
- 大池（≫400）要點「載入更多」先睇晒；首屏已覆蓋常見碼查（如 384）。
- 詞性篩開啟時首屏／續載可能多打幾次引擎請求；`hasMore` 仍跟引擎 `fetched < total`。
- Dense-code 全桶可能一次載入數千行（再 client 排序分頁）— 正確性優先於 2000 alpha cap。
