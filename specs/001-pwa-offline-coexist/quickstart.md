# Quickstart: Validate PWA Offline Coexist

**Date**: 2026-07-02  
**Spec**: [spec.md](./spec.md)  
**Contracts**:
- [contracts/offline-readiness.md](./contracts/offline-readiness.md)
- [contracts/versioned-lexicon-package.md](./contracts/versioned-lexicon-package.md)

本文件係「驗證指引」，目標係用最少步驟證明：PWA 能首次載入後離線可用、版本化資料包只在 release 更新、同 portable 共存。

維護者發佈流程（Pages + 詞庫版本對齊）見：[`docs/pwa.md`](../../docs/pwa.md)。

## Prerequisites

- 一部 iPhone（iOS Safari）同/或一部 Android（Chrome）
- 可以部署靜態網站嘅位置（例如 GitHub Pages）

## Scenario A (P1): First online load → offline ready → fully offline search

1. 用手機開啟 PWA（在線）
2. 等到介面顯示「離線就緒」（見離線就緒契約）
3. 執行至少 1 次查詢並看到結果
4. 將手機切換到飛航模式（完全離線）
5. 從主畫面重新開啟 PWA
6. 再執行至少 1 次查詢

**Expected outcomes**
- 離線狀態下可開啟並查詢
- 不需要額外登入或後端服務

## Scenario B (P3): Cache evicted → user can self-recover

1. 模擬清除網站資料/快取（或以測試機重置）
2. 在完全離線狀態下打開 PWA
3. 觀察提示：應告知需要一次連網完成離線就緒
4. 重新連網後打開 PWA 並完成離線就緒

**Expected outcomes**
- 提示清楚、可自助復原

**DB-4 細節**（見 [offline-readiness.md](./contracts/offline-readiness.md) § Lexicon storage）：
- 詞庫有 **OPFS** 與 **SW CacheFirst** 雙路；清除其中一路時，另一路仍可能支援離線開庫
- 僅當**兩路皆空**且離線時，才應顯示「需連網完成離線就緒」
- 驗證子情境（可選）：
  - B1：只清 SW cache，保留 OPFS → 離線仍應就緒（`VITE_DB_BACKEND=opfs` 或曾寫入 OPFS）
  - B2：只清 OPFS，保留 SW cache → 離線仍應就緒（`fetch` 命中 SW）
  - B3：兩者皆清 → 離線 Not Ready；連網後重試成功

## Scenario C (P2): Version alignment across portable and PWA

1. 選定某個 release semver（例如 `vX.Y.Z`）
2. portable 與 PWA 都使用該版號的詞庫資料包
3. 用同一組代表性查詢在兩邊測試

**Expected outcomes**
- 版本號一致
- 查詢結果等價（以使用者可觀察內容為準）

## Scenario D (DB-5): Cold start + memory benchmark

**Prerequisites**: `client/public/lyrics.dev.db` 已存在（`node copy-db.js`）

1. **桌面 Chrome — sqljs baseline**
   - `cd client && npm run dev`
   - 開啟 `http://localhost:5173/?benchmark=1`
   - 等待 JSON 輸出（`ok: true`）；記錄 `initMs`、`probeQueryMs`、`memoryAfterInit`
2. **桌面 Chrome — opfs 對照**
   - `VITE_DB_BACKEND=opfs npm run dev`（同 URL `?benchmark=1`）
   - 首次執行後關閉分頁，再開一次 `?benchmark=1`（第二次應無網路 fetch）
3. **iOS 飛航（D5-M5）**
   - 完成 Scenario A 步驟 1–3（離線就緒 + 在線查詢一次）
   - 飛航模式 → 主畫面重開 PWA → 再查詢 `事業` 或任意 golden query
4. 將結果填入 [`research.md` § DB-5](./research.md#db-5-storage-layer-measurements-adr-0024-72)

**Expected outcomes**
- Benchmark 頁可重現、JSON 可複製到 research 表
- 飛航模式下探針查詢有結果
- Safari 無 `performance.memory` 時，以 Web Inspector Memory 手動補 D5-M3

