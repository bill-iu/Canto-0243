# ADR-0049: 就緒閘（server 契約 + 極薄 UI）

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 就緒閘、降級逾時、詞庫快取索引、離線啟動預載、近義複合快照。

整合並取代：[0001](./0001-readiness-gate-server-contract.md)、[0003](./0003-phase3-gate-ui-and-compound-syn-snapshot.md)。PWA 雙階啟動見 [ADR-0045](./0045-pwa-delivery-and-lexicon-channel.md) §3。

## 1. Server 單點真相

1. 解鎖 policy 只在 `readiness_gate`（唔散落 preload 編排與前端）。
2. 凡經**查詢分派**的搜尋：閘未開 → **503** + 與 `GET /ready` 相同 flat snapshot（`Retry-After: 1` 建議）。
3. Snapshot：`gate_ready`、`degraded`、`gate_open_reason`（`ready` | `failed` | `degraded` | null）。
4. 非查詢分派路由（如關係補錄）不受閘。
5. `GET /words/search` 一律 `execute_search`，路由層唔另 list-filter。

## 2. 前端極薄

1. 只 poll `/ready` 呈現進度；**禁止**本地逾時解鎖或第二份 gate policy。
2. 連線失敗可暫停動畫，**唔**自行當就緒。

## 3. 近義複合快照（同 ADR 一併收斂）

1. 單一模組提供**近義複合快照**；查詢時可追加源 3 單字合成並 union（規則見 CONTEXT）。
2. 唔在啟動時預算全 `~~` 三源。

**Consequences** — policy 測集中 `readiness_gate`；PWA 閘語意平行但無 word_cache（見 0045）。

Portable 閘解鎖改 **DB 探針**、word_cache 入 tail：見 [ADR-0055](./0055-portable-gate-db-probe-word-cache-tail.md)。
