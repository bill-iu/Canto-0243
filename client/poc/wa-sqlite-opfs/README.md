# DB-0 — wa-sqlite + OPFS spike

ADR-0024 §7.2 **DB-0**：最小可行驗證 — 把 release SQLite 寫入 OPFS，用 `OPFSCoopSyncVFS` 開庫並執行 `SELECT COUNT(*) FROM words`。

**不通過條件不進 DB-1**（不動 `client/src/db/init.ts` / query-engine）。

## Grill 決策（已鎖定）

見 [`GRILL.md`](./GRILL.md)。摘要：

| 決策 | 選擇 | 理由 |
|------|------|------|
| VFS | `OPFSCoopSyncVFS` | filesystem transparent（可 import 標準 `.db`）；iOS Safari 可用；多 tab 可接受 |
| 執行環境 | Dedicated Worker | OPFS sync access handle 需 Worker（wa-sqlite examples 慣例） |
| 本 spike 範圍 | 只驗 I/O + COUNT | 不接 `DatabaseBackend`、不改 parity |
| sql.js | 保留 | DB-5 前不刪；此目錄獨立 `package.json` |

## 執行

```bash
cd client/poc/wa-sqlite-opfs
npm install
npm run dev          # 本機 Chrome（http://localhost:5173）
npm run dev:ios      # iOS 實機（https + 區網，見下方）
```

桌面開發用 `npm run dev`（`http://localhost:5173`）。

**iOS 實機**請用 `npm run dev:ios`（Vite 6 已移除 `--https` CLI，改由 `@vitejs/plugin-basic-ssl` + `--mode ios` 啟用自簽 HTTPS）。

### 手動步驟（通過條件）

1. **Chrome（桌面）**
   - 選 `fixture` 來源 → 按 **Import → OPFS + COUNT** → 應見 `COUNT(*) = …`（fixture 詞條數）
   - 按 **COUNT only** → 同數字、**不應**再 fetch
   - 重新整理頁面 → 再按 **COUNT only** → 仍同數字（OPFS 持久）

2. **iOS Safari（一台實機）**
   - 電腦執行 `npm run dev:ios`，終端會顯示 `Network: https://192.168.x.x:5173/`
   - iPhone 與電腦同 Wi‑Fi，Safari 開該 **https** URL（憑證警告 → 繼續造訪）
   - 確認頁首 `OPFS=yes`、`SharedArrayBuffer=yes`
   - 選 `lyrics.dev.db` → Import（約 106MB，需耐心）
   - COUNT only 成功即 DB-0 iOS 通過

3. **DB-2（版本化 OPFS import）**
   - 按 **「3. DB-2 ensure」** 或開啟 `?selfcheck=1`
   - 應見 `DB-2 ok`（第二次 ensure 不觸發 fetch）
   - 實作見 `client/src/db/opfs-lexicon.ts`

4. **DB-3（init 雙路徑）**
   - 主線 `client/src/db/init.ts`：`VITE_DB_BACKEND=opfs` 時走 `ensureLexiconInOpfs` → sql.js 開庫；預設仍 `sqljs`（parity 不變）
   - 主 PWA 驗證：`cd client && VITE_DB_BACKEND=opfs npm run dev`（需 COOP/COEP，見 `vite.config.ts`）
   - Node 自檢：`npx tsx scripts/init-backend-self-check.ts`

5. **記錄**（DB-0 完成時填進 issue / WORKLOG）
   - 裝置型號 + OS 版本
   - COUNT 結果
   - Import 耗時（可選）

## 架構

```
main.ts ──postMessage──► db-worker.ts
                              ├─ fetch bytes → OPFS (lyrics-opfs.db)
                              ├─ wa-sqlite.mjs + OPFSCoopSyncVFS
                              └─ SELECT COUNT(*) FROM words
```

## 故障排除

- **SharedArrayBuffer=no**：確認 Vite dev server 有 COOP/COEP（見 `vite.config.ts`）
- **OPFS=no**：瀏覽器太舊或非安全 context（需 HTTPS 或 localhost）
- **Reset 後 COUNT only 報 `no such table`**：已修；Reset 會清 journal/wal 並丟棄 VFS 快取。Reset 後應見「請先按 Import」，屬預期。
- **fetch lyrics.dev.db 404**：確認 repo 根目錄已 `node client/copy-db.js` 產生 `client/public/lyrics.dev.db`
