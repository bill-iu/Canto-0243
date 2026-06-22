# Per-tab search history stacks (搜尋分頁回溯鏈)

Each **search** query tab keeps its own in-memory `historyStack` + `historyIndex`, persisted in `sessionStorage` across reload. Browser `pushState` records stack commits on the active tab only; tab switches use `replaceState`. `popstate` applies only when `state.tabId` matches the active **search** tab—otherwise the current URL is restored (teaching/relation views never cross-navigate on Back). New searches truncate forward branches; blank **新查詢** is stack index 0. Mode-only pill changes do not commit; mode change plus re-search does.

**Considered:** one global browser history (ADR-0019)—Back leaks across tabs. Rejected: browser-forward support within a tab.