# Tasks: PWA Offline Coexist

**Input**: Design documents in `specs/001-pwa-offline-coexist/` (plan.md, spec.md, research.md, data-model.md, contracts/)

**Prerequisites**: `specs/001-pwa-offline-coexist/plan.md` (done), `specs/001-pwa-offline-coexist/spec.md` (done)

**Tests**: 本 spec 未要求新增自動化測試；任務以「quickstart.md 實機驗證」為主要驗收方式。  
**自動化基線**：`python scripts/pwa_golden_parity.py --gate all`（18/18 journeys + 15/15 match_spec，2026-07-03）。

**Last reviewed**: 2026-07-03 — 修復 Pages「事業」搜尋無結果（`useSearch` 重複 `useDB` state）；portable smoke 接受 `開心`/`高興`。

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 決定 PWA 部署目標路徑（GitHub Pages base path）並在 `client/` 產出可用的 deploy 設定（確保離線資源路徑正確）
- [x] T002 清理/補齊 `client/public/` 所需 PWA 靜態資源（icons、manifest 內容一致性、必要的離線提示文案資源）
- [x] T003 [P] 補齊 `client` build 前置資料檔存在性檢查（缺少詞庫資料包時 fail fast；避免部署出「可開但不可用」）— `copy-db.js` + Pages workflow `test -s lyrics.db`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Checkpoint**: PWA 可以在本機完整跑起、且「離線就緒狀態」可被判定與展示。

- [x] T004 定義「版本化詞庫資料包」輸入格式與命名規則（對齊 release semver tag；見 `contracts/versioned-lexicon-package.md`）
- [x] T005 修改 `client/copy-db.js`：支援將 repo root 的詞庫資料包複製到 `client/public/` 的「版本化檔名」（而非固定 `lyrics.db`）
- [x] T006 修改 PWA 離線緩存規則：確保版本化詞庫資料包會被 cache（並且是 CacheFirst）
- [x] T007 建立「離線就緒」判定：當且僅當詞庫資料包已可離線取得且可完成查詢時，狀態為 Ready（見 `contracts/offline-readiness.md`）；探針須在結果中見到 `事業` 字面

---

## Phase 3: User Story 1 - 首次上線載入並離線就緒 (Priority: P1) 🎯 MVP

**Goal**: 第一次上線開啟後，完成離線就緒；之後完全離線仍可查詢。

**Independent Test**: 依 `specs/001-pwa-offline-coexist/quickstart.md` 的 Scenario A。

- [x] T008 [US1] UI 呈現離線就緒狀態（Not Ready / In Progress / Ready / Failed），並在未就緒時避免誤導可離線查詢
- [x] T009 [US1] 確保在完全離線狀態下仍可載入 UI（HTML/JS/CSS 等必要資源均可離線）
- [x] T010 [US1] 確保在完全離線狀態下可完成查詢並顯示結果（詞庫資料包讀取不依賴網路）— 引擎 + `DBProvider` 共用 state；桌面已驗

**Checkpoint**: 完成後，Scenario A 可在 iOS 與 Android 各至少一台實機跑通。→ **待補實機（見下方 Remaining）**

---

## Phase 4: User Story 2 - 與 PC portable 共存且不造成額外維護 (Priority: P2)

**Goal**: PWA 與 portable 共用同版（semver）詞庫資料包；維護者不需要維護第二條資料管線。

**Independent Test**: 依 `quickstart.md` Scenario C。

- [x] T011 [US2] 將 release semver tag 作為詞庫資料包版本來源（單一真源），並在 PWA 介面顯示「目前詞庫版本」
- [x] T012 [US2] 串接現有 release / lexicon 工作流：定義「如何從既有 release tag 取得對應詞庫資料包並部署到 PWA」— `.github/workflows/pages.yml`
- [x] T013 [US2] 文件化維護流程（面向維護者）：同一個 release tag 下，portable 與 PWA 使用同版資料包的步驟與驗證點 — `docs/pwa.md`

---

## Phase 5: User Story 3 - 緩存被清除時可自助復原 (Priority: P3)

**Goal**: iOS cache 被清除後，用戶可理解提示並自行復原。

**Independent Test**: 依 `quickstart.md` Scenario B。

- [x] T014 [US3] 在 Not Ready / Failed 狀態提供清楚提示與復原路徑（重新連網開啟一次即可）
- [x] T015 [US3] 加入「重新嘗試離線就緒」的明確操作（避免只靠重整/猜）

---

## Phase 6: Deployment (GitHub Pages)

- [x] T016 新增/更新 GitHub Pages 部署方式（workflow 或手動指引），確保部署後離線資源路徑正確
- [x] T017 針對 GitHub Pages 的 base path 進行驗證（首次載入、離線就緒、離線開啟）— 桌面 Chrome 已驗；**本次 redeploy 後再驗搜尋「事業」**

---

## Phase 7: Validation & Handoff

- [ ] T018 跑完 `specs/001-pwa-offline-coexist/quickstart.md` 全部情境（A/B/C），記錄結果（至少 iOS + Android 各一次）
- [x] T019 回填必要的 docs（若新增部署/維護步驟，更新對應文件入口點，保持「單 pipeline」敘事一致）— `docs/pwa.md`、`quickstart.md` Scenario D

---

## ADR-0024 儲存層（延伸，非原 tasks 範圍）

| 階段 | 狀態 | 備註 |
|------|------|------|
| DB-1 sql.js backend | ✅ | `database-backend.ts` |
| DB-2 OPFS lexicon | ✅ | `opfs-lexicon.ts` |
| DB-3 `VITE_DB_BACKEND=opfs` | ✅ | 預設仍 `sqljs` |
| DB-4 雙路還原 | ✅ | OPFS → SW → network |
| DB-5 benchmark | ✅ 桌面 | `?benchmark=1`；見 `research.md` |
| D5-M5 iOS 飛航 | ⏳ | 需 **連網重開一次**（v1.0.4-beta+ OPFS write-through）後再測 |
| wa-sqlite VFS（降 RAM） | ⏳ | POC 在 `client/poc/`；非本 release blocker |

---

## Remaining（不阻擋本次 Pages redeploy）

| 項目 | 優先 | 說明 |
|------|------|------|
| **T018** quickstart A/B/C 實機 | P1 | iOS Safari + Android Chrome 各跑一輪 |
| **D5-M5** iOS 飛航探針 | P2 | `research.md` gate 最後一項 |
| **portable zip** 上傳 release | P3 | smoke 已修；用戶明確不補 zip |
| **production SW cache** 詞庫命中 | P3 | dev 無 SW cache；Pages 部署後可選驗 |
| **PR dev→main** | 維護 | `main` 有分支保護；合併需用戶確認 |

---

## 本次修復摘要（2026-07-03）

- **Bug**：`useSearch` 內再次 `useDB()` → 搜尋 state 永遠 `not ready` → UI 顯示「未找到結果」
- **Fix**：`DBProvider` 共用 context；`validateOfflineReadiness` 驗證結果含 `事業` 字面
- **portable smoke**：反義詞 `痛苦` 接受 `開心` 或 `高興`

## iOS 飛航修復（2026-07-03）

- **Bug**：`sqljs` 預設路徑只載入 RAM，未寫 OPFS；iOS 重開飛航時 SW 快取不可靠 → 開庫失敗
- **Fix**：`sqljs` 成功開庫後 write-through 至 OPFS；Ready 前驗證 OPFS 已落地；`sql-wasm-browser.wasm` 納入 SW 快取
- **用戶操作**：部署後需 **連網再開一次**，待「離線就緒」完成 OPFS 寫入，再測飛航
