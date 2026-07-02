# Contract: Offline Readiness (User-Facing)

**Scope**: PWA 使用者體驗契約（非實作細節）  
**Spec**: [../spec.md](../spec.md)

## Purpose

使用者在任何時候都能知道：
- 目前是否已「離線就緒」
- 若未就緒，需要做什麼才可恢復到可離線查詢

## Contract

### States

系統必須對外呈現以下其中一個狀態：

1. **Not Ready**
   - 意味：尚未完成離線就緒
   - 使用者提示：需要一次連網開啟以完成離線就緒

2. **In Progress**
   - 意味：正在準備離線就緒
   - 使用者提示：顯示可理解的進度/等待提示

3. **Ready**
   - 意味：已完成離線就緒
   - 使用者提示：清楚顯示「離線就緒」，並允許使用者在離線狀態下查詢

4. **Failed**
   - 意味：離線就緒失敗
   - 使用者提示：說明可能原因（例如儲存空間不足）與復原方式（重新連網重試）

### Rules

- 系統不得在 Not Ready / Failed 狀態下誤導使用者「已可離線查詢」
- 當狀態由 Ready 退回 Not Ready（例如 cache 被清除）時，必須可被使用者理解且可自助復原
- **Ready 的技術定義**（D-G2）：詞庫可開啟且能完成至少一次真查詢（非僅 `COUNT(*)`）；探針查詢見 `OFFLINE_READINESS_PROBE_QUERY`（`client/src/db/query.ts`）

### Lexicon storage (DB-4)

詞庫資料包可有**兩條本機復原路徑**（職責分開、互為備援）：

| 路徑 | 職責 | 典型生命週期 |
|------|------|----------------|
| **OPFS** | 版本化檔案 `lyrics-{version}.db` 落地（`VITE_DB_BACKEND=opfs` 時必寫入） | 瀏覽器儲存空間；清除「網站資料」可能一併刪除 |
| **Service Worker `CacheFirst`** | HTTP 層快取 `lyrics.{version}.db`（含 `lyrics.dev.db`） | Workbox `database-cache`；與 HTML/JS 快取策略分開 |

**復原優先順序**（實作：`client/src/db/lexicon-restore.ts`）：

1. **OPFS** — 若該版本檔案存在，直接讀取（離線可用）
2. **SW 快取** — `fetch(lyrics.*.db)` 由 `CacheFirst` 命中（離線可用）
3. **網路** — 僅在在線且前兩者皆無時下載

兩條本機路徑**任一存在**即視為「詞庫已可離線取得」的前置條件（`isLexiconCachedForBackend`）；完成開庫與探針查詢後才進入 **Ready**。

**`VITE_DB_BACKEND` 差異**：

- `sqljs`（預設）：開庫 bytes 來自上述 1→2→3；整檔進 RAM
- `opfs`：優先 OPFS 開庫；若 OPFS 缺失則從 2 或 3 取得並**寫入 OPFS** 後再開

### Scenario B (cache evicted)

見 [quickstart.md § Scenario B](../quickstart.md#scenario-b-p3-cache-evicted--user-can-self-recover)：

- 若 **OPFS 與 SW 皆已清除** 且裝置離線 → **Not Ready**，提示需連網一次
- 若 **僅清除其一** → 仍可能透過另一路徑完成離線就緒（無需重新下載全檔，除非兩路皆空）
- 使用者可透過「重新嘗試離線就緒」在連網後自助復原
