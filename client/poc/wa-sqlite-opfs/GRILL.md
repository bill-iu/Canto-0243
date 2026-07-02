# DB-0 Grill 紀錄

依 [ADR-0024 §7.0–7.2](../../../docs/adr/0024-pwa-query-engine-execution-strategy-gate.md) 與 grill-me 流程，DB-0 前需鎖定的決策樹。

## 1. OPFS 是否現在就做？

**建議：是（僅 spike，不接主線）。**

- Parity 已全綠（D-G1–G3）；儲存層與執行層分階段（ADR §7.0）。
- DB-0 只驗「能開庫 + COUNT」，失敗成本低。

## 2. 用哪個 VFS？

**建議：`OPFSCoopSyncVFS`。**

| 候選 | 捨棄原因 |
|------|----------|
| `AccessHandlePoolVFS` | 單連線；非 filesystem transparent，難直接 import release `.db` |
| `IDBBatchAtomicVFS` | IndexedDB；大檔 RAM/效能不如 OPFS 路線 |
| `OPFSWriteAheadVFS` | Safari/iOS 不支援 |
| `OPFSAdaptiveVFS` | 需 asyncify build；CoopSync 已覆蓋 iOS + 多 tab |

Filesystem transparent = 可把 `fetch(arrayBuffer)` 寫入 OPFS 後當標準 SQLite 檔開啟（與 release pipeline 一致）。

**實作備註（DB-0 spike）**：`OPFSCoopSyncVFS.jAccess` 只認 `accessiblePaths`，不能直接寫裸 OPFS 再開。流程：VFS `CREATE` 空殼 → `close` → sync access handle 覆寫 bytes → `READONLY` 開庫。DB-2 import 可沿用。

## 3. Worker 還是主線程？

**建議：Dedicated Worker。**

wa-sqlite OPFS sync access handle 在 Worker；主線程 spike 會撞 API 限制。DB-0 不引入 SharedWorker（YAGNI）。

## 4. spike 要不要接 `init.ts`？

**建議：不要。**

DB-1 才做 `DatabaseBackend`；DB-0 通過條件僅 Chrome + iOS 手動 COUNT。

## 5. 用哪個詞庫檔驗證？

| 場景 | 檔案 |
|------|------|
| 本機快速迭代 | `tests/fixtures/lyrics.db`（`/lyrics.fixture.db`） |
| iOS / 接近 production | `client/public/lyrics.dev.db` |

## 6. 開放問題（DB-1 前再 grill）

- [ ] OPFS 與 SW `CacheFirst` 雙路復原的優先順序（DB-4）
- [x] `VITE_DB_BACKEND=opfs` 可選（DB-3）；預設 `sqljs`；翻預設等 DB-5

---

**DB-0 通過勾選**

- [x] Chrome：Import + COUNT + COUNT only（fixture，COUNT=17，2026-07-03 本機 Cursor/Electron Chromium）
- [ ] iOS：lyrics.dev.db Import + COUNT
