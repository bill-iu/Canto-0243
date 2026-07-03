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
2. 等到介面顯示「資料庫離線就緒」（見離線就緒契約；Ready 狀態 UI 文案）
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

## Scenario E (P2): Visual parity — gate + shell

**Prerequisites**: `npm run dev`（`client/`）；桌面 Chrome 或手機 Safari。

1. **冷啟 gate**
   - 清除該 origin 的 `sessionStorage`（或無痕視窗首次開啟）
   - 開啟 PWA 根 URL
   - 應見全屏 gate：SVG wordmark、ink 進度、「執緊啲字…」文案
   - 離線就緒後短暫顯示「開得工！」再 handoff 至搜尋殼
2. **Gate 後 header**
   - header **不**應常駐「離線就緒」chip（僅 brand + 模式選單下拉）
   - 模式選單內可進入「搜尋教學」「關於」（**無** Portable 頂欄 ghost-button）
3. **搜尋殼**
   - hero「ONE·搵·韻」、warm paper 背景、`search-panel` 圓角輸入與 primary 搜尋鈕
   - 查 `事業`、`?+m?` 有結果；詞條 grid 視覺與 Portable light 一致（允許 PWA 多 code/jyutping 標題列）
4. **Guide / About**
   - `guide-hero` 排版；About 頁顯示詞庫版本（與 release 一致）
5. **Benchmark**（`?benchmark=1`）
   - 使用 open-design token 與最小 shell（不要求 pixel-perfect）

**Failure paths**
- 離線且未就緒：gate **不撤**，顯示需連網／重試
- `failed`：gate 保留錯誤訊息 + 重試鈕

**Expected outcomes**
- light 視覺與 Portable 同源 CSS；行為見 [offline-readiness.md](./contracts/offline-readiness.md)

---

## Scenario F (P2): PWA 查詢分頁

**Prerequisites**: 離線就緒（gate handoff 完成）；桌面 Chrome 或 iPhone 主畫面 PWA。

1. **新增分頁**
   - 點分頁列 `+` → 新「新查詢」分頁；≥1 分頁時可 `×` 關閉（不可關到零）
2. **並行查詢**
   - 分頁 A 查 `事業`、分頁 B 查 `香港` → 切換分頁應**即時**顯示各自結果（同 session **唔**重查）
3. **session 還原**
   - 兩個以上分頁各有查詢 → **同 tab 內**重整 → 分頁列與標籤還原；**只**作用中分頁自動重跑搜尋
4. **URL**
   - 切換作用中分頁 → 網址只反映該分頁 `q` / `mode` / `view`；Guide/About 各至多一 singleton 分頁
5. **回溯鏈**
   - 同一搜尋分頁：查 A → 再查 B → 瀏覽器「返回」→ 回到 A 的結果（或空查詢）

**Failure paths**
- 僅剩一個分頁時：`×` 不可用或無效

**Expected outcomes**
- 行為對齊 `CONTEXT.md` §查詢分頁；契約測試 `tests/query_tabs_state_test.mjs` 仍 pass

---

## Scenario G (P2): PWA 分頁重排 + 快捷鍵（桌面）

**Prerequisites**：離線就緒；**桌面 Chrome** 開 https://bill-iu.github.io/Canto-0243/（非 iPhone）。

1. **滑鼠拖曳**
   - 開 ≥3 個搜尋分頁（不同查詢字）
   - 用滑鼠拖曳 pill 改變順序；按住時該分頁變作用中
   - **+** 鈕不可拖曳
2. **Alt+N / Alt+W**
   - Alt+N → 新空白「新查詢」分頁並聚焦搜尋框
   - Alt+W → 關閉作用中分頁（Guide/About 亦適用）；僅剩 1 分頁時無效
3. **session 列順序**
   - 拖曳後同 tab 重整 → 分頁列順序還原

**Out of scope（Phase 10b）**：iPhone 長按拖曳；iPhone 不驗 Alt。

**Expected outcomes**
- `reorderTab` / session 序列化與 Portable 共用契約一致

---

## Scenario G-mobile (P2, Phase 10b): iPhone touch 分頁重排

**Prerequisites**：iPhone 主畫面 PWA；Phase 10b 實作後才驗。

1. 長按 pill → 拖曳重排；tap 仍切換分頁
2. **不**驗 Alt+N/W

---

## Results（2026-07-03 T018）

**環境**：https://bill-iu.github.io/Canto-0243/（`dev` deploy + `v1.0.4-beta` 詞庫）  
**裝置**：iPhone iOS **26.5.1**（主畫面 PWA）；Android **pending**

| 情境 | 結果 | 備註 |
|------|------|------|
| **A** 在線就緒 → 飛航查詢 | **pass** | UI 顯示「資料庫離線就緒」；飛航重開後查 `事業` 成功 |
| **B3** 兩路皆空 → 復原 | **韌性 pass / strict 未重現** | 飛航下刪網站資料後仍就緒（OPFS 存活）；連網後 SW 回填。符合 DB-4 雙路設計 |
| **B1/B2** | **pending** | 待 Android 或桌面 Chrome |
| **C** portable ↔ PWA | **parity 腳本 pass** | `pwa_golden_parity.py --gate all` 20/20；肉眼對照待 `v1.0.4-beta` portable zip |
| **P6 smoke** | **pass** | 桌面瀏覽器代測：mode menu、`?view=guide/about`、URL sync |
| **D5-M5** iOS 飛航 | **pass** | 含於 Scenario A |

**Deploy run**：[Actions #28651396099](https://github.com/bill-iu/Canto-0243/actions/runs/28651396099)（`dev` + `v1.0.4-beta`）

