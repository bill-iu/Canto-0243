# Research: PWA Offline Coexist

**Date**: 2026-07-02  
**Spec**: [spec.md](./spec.md)  
**ADR context**: `docs/adr/0023-introduce-static-client-bundle-and-pwa-delivery-channel.md`

## Key Decisions (Resolved)

### Decision: Offline definition = “offline after first successful load”

**Chosen**: 完全離線能力以「首次成功載入並完成離線就緒」之後開始。  
**Rationale**: 這是最低成本且不需要 Apple Developer 的方式；符合 PWA 的常見交付模型；符合「不維護雙 pipeline」要求。  
**Alternatives considered**:
- 首次開啟也必須完全離線：通常意味著原生封裝/安裝包路線，會引入簽名/上架/多平台打包成本與新 pipeline。

### Decision: Hosting = free static hosting (GitHub Pages)

**Chosen**: 以純靜態網站部署（GitHub Pages 類）。  
**Rationale**: 零後端、最低營運成本；符合「完全離線（首次載入後）」與跨平台瀏覽器能力。  
**Alternatives considered**:
- 自架後端 API：違反「完全離線」核心價值且提高成本。

### Decision: DB update strategy = “release-only”

**Chosen**: DB 只在新 release（semver）時更新；平時優先使用已緩存版本。  
**Rationale**: 避免 iOS 反覆下載大檔造成體感與成本問題；降低更新風險；更可預期。  
**Alternatives considered**:
- 每次啟動都檢查/更新 DB：對大檔不友好，iOS 風險高。

### Decision: Versioning = semver tag

**Chosen**: DB 版本識別對齊 release semver tag，並以「版本化資產 URL」確保可預期更新。  
**Rationale**: 單一版本來源（portable 與 PWA 共用）；便於回滾與驗證一致性。  
**Alternatives considered**:
- timestamp / git sha：雖可用，但較不直覺且不利於對齊 release 心智模型。

## Known Risks (Accepted) + Mitigations

### Risk: iOS may evict PWA caches

**Impact**: 使用者可能在完全離線時打開後發現未就緒。  
**Mitigation**:
- 明確的「離線就緒」狀態呈現與失敗提示
- 提供自助復原說明：重新連網打開一次即可恢復

### Risk: Large initial download (DB size)

**Impact**: 首次載入時間較長、行動網路成本較高。  
**Mitigation**:
- 清楚提示下載進度
- 只在 release 更新 DB（避免反覆下載）

---

## DB-5: Storage layer measurements (ADR-0024 §7.2)

**Date**: 2026-07-02  
**Harness**: `client/src/db/db-benchmark.ts`；瀏覽器開啟 `?benchmark=1`（見 [quickstart.md](./quickstart.md) Scenario D）

### Scope

| 項目 | 說明 |
|------|------|
| 對照 backend | `sqljs`（預設）vs `VITE_DB_BACKEND=opfs` |
| 現況限制 | 兩者皆經 **sql.js 整檔進 RAM**；OPFS 現階段主要改善**重開不下載**，**尚非** mmap 降 RAM（wa-sqlite VFS 為後續） |
| 成功定義（本階段） | 飛航探針查詢可用；記錄 baseline；**預設 backend 維持 sqljs** 直至連續兩版 release 穩定 |

### Metrics

| ID | 指標 | 來源 | 備註 |
|----|------|------|------|
| **D5-M1** | 冷啟 init→就緒 | `initMs` | 殺進程後重開；`?benchmark=1` 含 `resetFirst` |
| **D5-M2** | 探針查詢 | `probeQueryMs` | `OFFLINE_READINESS_PROBE_QUERY`（`事業`） |
| **D5-M3** | JS heap | `memoryAfterInit` / `memoryAfterProbe` | Chrome/Electron 有值；**Safari 用 Web Inspector** |
| **D5-M4** | 儲存用量 | `storageUsageMb` | `navigator.storage.estimate()`（含 OPFS） |
| **D5-M5** | 飛航查詢 | 手動 Scenario A 步驟 4–6 | 離線就緒後飛航模式再查 |

### 操作腳本（維護者）

```bash
# 1) 產生 lyrics.dev.db
cd client && node copy-db.js

# 2) sqljs baseline（桌面 Chrome）
npm run dev
# 開 http://localhost:5173/?benchmark=1 → 複製 JSON

# 3) opfs 對照
VITE_DB_BACKEND=opfs npm run dev
# 首次：寫入 OPFS；關閉分頁再開 ?benchmark=1 → 比較 initMs

# 4) iOS：npm run dev:ios（poc 目錄）或 Pages 部署後 Scenario A + D5-M5
```

### Results（手動填入）

| 裝置 | OS | Backend | D5-M1 initMs | D5-M2 probeMs | D5-M3 heap MB (init) | D5-M5 飛航 OK | 備註 |
|------|-----|---------|--------------|---------------|----------------------|---------------|------|
| _TBD_ | | sqljs | | | | | |
| _TBD_ | | opfs 2nd cold | | | | | 預期 init 無網路 fetch |

### Gate（DB-5 完成勾選）

- [ ] 桌面 Chrome：`?benchmark=1` 產出有效 JSON（`ok: true`）
- [ ] iOS：Scenario A 飛航查詢通過（D5-M5）
- [ ] `sqljs` vs `opfs` 各至少一筆 D5-M1/M2 記錄於上表
- [ ] **不**翻轉 `VITE_DB_BACKEND` 預設（待上表 + 兩版 release）

### RAM 峰值結論（預期）

直至 **wa-sqlite + OPFS VFS** 取代 sql.js 整檔載入，D5-M3 **不應**期望 opfs backend 顯著低於 sqljs。DB-5 交付的是**量測方法與 baseline**，而非提前宣告 RAM 達標。

