# Search result links and per-tab browser history

Chrome-style query tabs store each search tab’s `q` in session state; `syncViewPanels` mirrors `tab.q` into the search input. Result clicks must update `tab.q` **before** any view sync, or the input reverts and the search never changes (e.g. `34` → click `可以` stays on `34`).

Result cells are `<a href="?q=…">` with `preventDefault` for SPA search. Every new `q=` (manual search, result click, guide example) uses `pushState` unless `q` and `mode` match the current history entry (`replaceState`). Switching app tabs uses `replaceState` only so browser Back walks the active search tab’s query chain, not tab switches. **`syncViewPanels` must not touch browser history** — an earlier `replaceState` there overwrote pushed entries and broke Back. On `popstate`, restore from `searchCache` when present; otherwise re-fetch.

**Considered:** `<button>` only (no shareable URL); full page navigation on click (breaks tab session). Rejected: duplicate history entries for identical `q=`+mode.