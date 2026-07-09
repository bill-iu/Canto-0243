# PWA 雙階啟動：就緒閘解鎖與 tail 背景預載

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 就緒閘解鎖、啟動完畢、背景預載標示、閘前進度、詞庫暖啟動、詞庫預取、離線啟動預載。使用者契約：[`specs/001-pwa-offline-coexist/contracts/offline-readiness.md`](../../specs/001-pwa-offline-coexist/contracts/offline-readiness.md)。Portable 對照：ADR-0001、ADR-0003、ADR-0044 §4（詞庫快取預暖）。

PWA 首次冷啟動長時間卡在就緒閘，主因是閘前同步完成詞庫下載／開庫、輔助 JSON 載入與離線驗證，且 `progress` 長時間無 byte 比例。Portable 已採雙階模型（`gate_ready` 後搜尋、tail 以 header 標示背景完成），但 PWA 無 **詞庫快取索引**，閘前條件不同，不能照搬 server snapshot。

我們決定 PWA 引入與 Portable **平行語意**、**渠道專用實作**的雙階啟動：

1. **就緒閘解鎖**（閘前）— 阻塞 overlay 與搜尋，直至：詞庫開庫 + `validateOfflineReadiness` 探針（`事業`）成功；**不**引入「跳過探針早解閘」或 client 端降級逾時（維持 `offline-readiness.md` Ready 定義）。
2. **啟動完畢**（tail）— **就緒閘解鎖**後背景載入：**靜態詞林埠**索引預熱（`ensureStaticRelationIndexes`）。**韻母字母表**、複合詞表、排序 JSON 已移入閘前（**粵拼錨**與搜尋教學範例依賴，見 CONTEXT § **啟動完畢**）。未 **啟動完畢**時近反義池等依既有 fallback 降級。
3. **背景預載標示** — tail 進行中向創作者傳達進度（對齊 Portable warmup badge 職責）；不阻搜尋。
4. **閘前進度** — 首次須下載詞庫時回報 byte 比例與分階標籤（下載／開庫／驗證）；**詞庫暖啟動**快徑：有本機副本且開庫＋驗證於短閾值（約 500ms）內完成可跳過 overlay，否則 minimal 閘前進度（無 landing 儀式）。
5. **本輪一併優化** — **詞庫預取**（SW install／activate，省流量／metered 跳過）、下載與 WASM 並行預熱、多 Tab 下載進度廣播、**詞庫壓縮傳輸**（見下）。**詞庫分包**（H）另開 PR／ADR，本輪不做。

**詞庫壓縮傳輸（G）** — GitHub Pages 唔可靠透明 `Content-Encoding`；建置產 `lyrics.{v}.db.gz`，manifest 增 `dbFileGz`／`compressedByteSize`／`preferCompressed`（建置時 gzip 節省 ≥15% 才為 true）。客戶端預設拉 `.gz`，於 OPFS worker 以 `DecompressionStream('gzip')` **串流**解壓寫入 OPFS（唔整包 buffer）；`byteSize`／`sha256` 仍指解壓後本體。無 `DecompressionStream` 或 `preferCompressed` 為 false 時 fallback 拉 plain `.db`。SW **詞庫預取**與 `database-cache` 快取壓縮 URL。**閘前進度**文案不變（仍「執緊啲字…」「差啲就齊…」等）；百分比可按壓縮 byte 內部計算。維護者以 throttled benchmark 驗證 `download+decompress+OPFS` wall time 唔差於 plain `.db`（p95）。

**Considered Options**

- 對齊 Portable：閘僅等 **詞庫快取索引** — PWA 無此索引，須直查 DB；語意不符。
- 早解閘（開庫即可搜、探針背景）— 體感最快，但削弱離線就緒承諾與飛航驗收。
- tail 僅輔助索引、靜態關係維持 lazy — 閘內時間較短，但首條近反義查詢仍慢；改為 tail 主動預熱靜態關係索引。
- 未 **啟動完畢**時阻擋部分語法 — 品質穩但與「先搜尋、手尾背景」及 Portable UX 分叉。

**Consequences**

- `initializeDatabase` 拆分閘前／tail；`useDB` 暴露 **就緒閘解鎖** 與 **啟動完畢**（及 tail 進度），避免第二份 gate policy。
- 首次下載主耗時仍在閘前；tail 與 badge 不替代下載優化（預取、並行、壓縮、進度回報）。
- 煙霧／離線就緒探針不變；新增啟動分段與暖啟動快徑的 client 測試。
- 與 ADR-0026 懶載入方向一致：閘前只保留 Ready 必要項，其餘移 tail。
- `copy-db.js`／`lexicon-manifest.json` 契約擴充；`opfs-vfs-worker` 與 `lexicon-restore` 須支援壓縮與 plain 兩路，避免解壓 buffer 拖慢載入。