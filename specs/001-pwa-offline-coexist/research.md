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

