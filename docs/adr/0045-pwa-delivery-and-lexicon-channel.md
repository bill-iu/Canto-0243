# ADR-0045: PWA 交付渠道、雙引擎查詢與詞庫掛載

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § **PWA**、**靜態客戶端束**、**瀏覽器查詢引擎**、**就緒閘解鎖**、**啟動完畢**、**詞庫掛載**、**詞庫渠道同步**、**詞庫開發掛載**。

整合並取代：[0023 靜態客戶端](./0023-introduce-static-client-bundle-and-pwa-delivery-channel.md)、[0024 執行策略閘](./0024-pwa-query-engine-execution-strategy-gate.md)（結論）、[0025 OPFS VFS](./0025-use-opfs-vfs-for-pwa-database.md)、[0026 帶寬](./0026-pwa-bandwidth-budget-and-lazy-lexicon-delivery.md)、[0032 雙階啟動](./0032-pwa-dual-phase-startup.md)、[0036 雙渠道掛載](./0036-dual-channel-lexicon-mount.md)。歷史全文見 git。

## 1. 交付形態與查詢引擎

1. **React + Vite PWA**（`client/`）部署 GitHub Pages；Service Worker 離線快取。
2. **查詢引擎** — **方案 D**：TypeScript port（與 Portable 雙引擎），**唔**走 Pyodide（方案 E 暫緩）。Parity 以 golden／smoke 守。
3. **DB backend** — 預設／fallback **sql.js**；**opfs-vfs**（wa-sqlite Worker + OPFSCoopSyncVFS）為可選路徑，流式寫入 OPFS、唔把整庫載入 sql.js heap。能力不足則降級 sql.js。

## 2. 帶寬與詞庫發現

1. **殼不自動下全庫** — 首次搜尋或顯式準備離線才拉 `lyrics.db`（進度可見）；其後 OPFS／SW 持久。
2. **`lexicon-manifest.json`** — 網路優先短 cache；含 `lexiconVersion`、`dbFile`、`byteSize`、`sha256`、可選 `dbFileGz`／`preferCompressed`。App semver 與詞庫版本可獨立。
3. **壓縮傳輸** — 建置可產 `.gz`（節省 ≥15% 才 prefer）；客戶端 `DecompressionStream` 串流解壓；無則 plain。
4. **輔助索引 lazy** — 如靜態詞林大 JSON 由功能路徑載入，非普通 init 必載。
5. **Pages 產物** — 部署物不得含多於一個 `lyrics*.db`（防 stale 耗帶寬）。

## 3. 雙階啟動

1. **就緒閘解鎖** — 開庫 + 離線就緒探針成功；**無** client 端降級逾時（對齊 offline-readiness 契約）。
2. **啟動完畢（tail）** — 閘後背景：靜態詞林索引等；未完則近反義 fallback。
3. **閘前進度** — 下載／開庫／驗證分階；暖啟動快徑可跳過 overlay。

## 4. 雙渠道詞庫掛載

1. **SSOT** — 根目錄 `lyrics.db`；runtime 分渠開庫（Desktop sqlite vs PWA OPFS／sql.js），唔共用 live connection。
2. **渠道同步（S3）** — 發佈閘綠後 `copy-db.js` copy 入 `client/public/` + 刷 manifest（可選 gz）；閘紅唔自動 sync。
3. **開發掛載（S2）** — Vite dev 優先 stream 根 `lyrics.db`。
4. **完整性** — 開庫校 `byteSize`／`sha256`；唔合 purge OPFS + SW 後重拉。OPFS 同 version 不同 size 須重下（唔靜默沿用舊包）。

**Considered Options（摘要）**

- Pyodide 同源 Python — 拒（體積／iOS／parity 閘未過）。
- 閘僅等「有 DB 檔」跳過探針 — 拒（削弱離線 Ready）。
- hardlink 根→public — 拒（Windows／gz）。
- 開站即下全庫 — 拒（Pages 帶寬）。

**Consequences**

- 維護者：`build-db` 綠閘 → public 同步；改詞庫須更新 manifest 完整性欄。
- 雙引擎規則變更須顧 Portable + PWA；共享 meta 見 ADR-0035／0040／0042。
- 音素 j2 開庫契約見 ADR-0037／0038（併入詞庫簇時再指）。
