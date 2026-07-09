# 雙渠道詞庫掛載（S3 渠道同步 + S2 開發掛載）

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § **詞庫掛載**、**詞庫渠道同步**、**詞庫開發掛載**、**詞庫刷新**。

維護者曾手維兩份完整 `lyrics.db`（repo 根 vs `client/public/`），易漂移。Desktop（Python sqlite）與 PWA（OPFS／sql.js）runtime 仍分渠開庫；「一份檔」指 **一個 SSOT 產物 + 掛載／同步**，唔係共用 live connection。

## 決策（Combo C）

1. **詞庫渠道同步（S3，主）** — `build-db` 只寫根 `lyrics.db`；**詞庫發佈閘**通過後**預設** copy（唔 hardlink）入 PWA `public/` 並刷新 `lexicon-manifest.json`（+ 可選 gz，見 ADR-0032 G）。可用 `--no-copy-public` 跳過。閘紅 exit≠0 且**唔**自動 sync；本地要 public 可人手 `node client/copy-db.js`。
2. **詞庫開發掛載（S2）** — Vite dev middleware：`GET /lyrics.db` 優先 stream 根 `lyrics.db`，否則 fallback `public/lyrics.db`。只 dev；build／Pages 用 S3 產物。manifest 仍讀 public；**唔**在 request 路徑重算 sha256。
3. **固定 URL + 完整性（C1）** — 檔名可固定 `lyrics.db`；SW 維持 CacheFirst。開庫前用 manifest `byteSize`／`sha256` 校验；唔合則 purge OPFS 與 SW `database-cache` 後再拉（**詞庫刷新**契約）。

**Considered：** hardlink／hardlink+fallback copy——拒絕（Windows／覆寫 inode 風險；gz 本要讀檔）。`predev` 每次自動 copy——拒絕（百 MB 慢）。db 改 NetworkFirst 或 content-hash URL——拒絕（帶寬／契約過大）。閘紅仍預設 sync——拒絕（易誤 ship）。

**Consequences**

- `copy-db.js` 仍為 S3 實作入口；`build-db` 預設呼叫。
- Dev 改根 db 後：跑 `build-db`（綠閘→sync）或 S2 直接吃根；固定 URL 下靠 manifest 完整性淘汰舊 cache。
- 與 **詞庫分包**（核心包／關係包，v1.0.7 唔做）無關。
