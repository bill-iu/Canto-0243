# Feature Specification: PWA Offline Coexist

**Feature Branch**: `pwa`

**Created**: 2026-07-02

**Status**: Draft

**Input**: 使用者需求：基於現有 `dev`（現已對齊至 `pwa` 分支）研究並建立一個可在 iOS/Android 使用的 PWA 交付渠道；要求最高效率最低成本、可在「首次成功載入後」完全離線、與現有 PC portable 版本共存，且不需要額外維護兩條 pipeline。

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.

  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - 首次上線載入並離線就緒 (Priority: P1)

創作者第一次在手機瀏覽器打開 Canto-0243 PWA，完成必要資源與資料包下載後，畫面顯示「離線就緒」。之後即使完全無網路，仍可開啟並查詢。

**Why this priority**: 這是 PWA 交付渠道的核心價值：用一次上網成本換取後續離線可用。

**Independent Test**: 以一支 iPhone 或 Android 實機，完成一次在線開啟後切換飛航模式仍可查詢。

**Acceptance Scenarios**:

1. **Given** 使用者第一次打開 PWA 且有網路，**When** 等待離線就緒完成，**Then** 顯示離線就緒狀態且可執行查詢並看到結果
2. **Given** 使用者已完成離線就緒，**When** 在飛航模式下從主畫面開啟 PWA 並查詢，**Then** 可正常開啟與回傳查詢結果（不依賴網路）

---

### User Story 2 - 與 PC portable 共存且不造成額外維護 (Priority: P2)

維護者發佈新版本時，PWA 與 PC portable 使用同一份版本化詞庫資料包與一致的版本號；維護流程不需要分岔成兩條獨立資料管線。

**Why this priority**: 需求明確要求「最低成本」與「不需維護兩條 pipeline」。

**Independent Test**: 以同一個 release 版本號，驗證 portable 與 PWA 所使用的詞庫版本一致，且發佈過程不需要額外的人手步驟（或新增只針對其中一邊的特殊處理）。

**Acceptance Scenarios**:

1. **Given** 維護者已產出某個 release 版本的詞庫資料包，**When** 同步提供給 PWA 與 portable，**Then** 兩者呈現同一版號與一致的查詢結果（同一查詢輸入得到等價結果）
2. **Given** 維護者僅更新版本號與對應詞庫資料包，**When** 重新部署 PWA，**Then** 使用者可在需要時取得新版資料，而舊版仍可在離線狀態下持續運作

---

### User Story 3 - 緩存被清除時可自助復原 (Priority: P3)

在 iOS 可能因系統清理導致離線緩存被移除的情況下，使用者再次上線打開即可恢復離線就緒；過程有清楚提示，避免「以為壞了」。

**Why this priority**: iOS PWA 儲存體限制屬已知風險；用提示與復原流程降低支援成本。

**Independent Test**: 模擬清除網站資料/快取後，重新上線打開能再次完成離線就緒；離線未就緒時提示清楚。

**Acceptance Scenarios**:

1. **Given** 使用者的離線緩存已不存在，**When** 在無網路下打開 PWA，**Then** 顯示「需要一次上線以完成離線就緒」的提示（不誤導為已可查詢）
2. **Given** 使用者重新連網打開 PWA，**When** 等待離線就緒完成，**Then** 恢復到可離線查詢狀態

---

### Edge Cases

- iOS/Android 儲存空間不足導致離線就緒失敗時，如何提示與回復（例如要求使用者清理空間、或只提供線上模式）
- 使用者在離線就緒過程中中斷（關閉頁面、切換網路）時，重新打開是否可續跑/重試且不造成壞狀態
- PWA 更新發生時（程式碼更新與資料包更新不同步），離線狀態下仍可使用舊版完整功能，不會出現「開得起但查不到」的半壞狀態
- 使用者同時裝了多個版本（或不同瀏覽器）時，離線資料包是否會重複佔用空間、提示是否清楚

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系統 MUST 以 PWA 形式提供手機（iOS/Android）可用的查詢介面，並支援「加入主畫面 / 安裝」使用體驗
- **FR-002**: 系統 MUST 在「首次成功載入並完成離線就緒」後，在完全離線狀態下仍可開啟並完成查詢與顯示結果
- **FR-003**: 系統 MUST 清楚呈現離線就緒狀態（未開始/進行中/完成/失敗），並在未就緒時避免讓使用者誤以為已可離線查詢
- **FR-004**: 系統 MUST 支援「版本化」的離線詞庫資料包，且版本識別 MUST 對齊同一個 release semver tag（每個版本必須能以唯一識別取得對應資料包）
- **FR-005**: 系統 MUST 允許在離線狀態下持續使用已緩存的舊版本（包含查詢與展示），不因線上更新不可用而中斷
- **FR-006**: 系統 MUST 在緩存被清除或不可用時，提供可理解的復原路徑：使用者只要再次連網打開即可重新完成離線就緒
- **FR-007**: 系統 MUST 與現有 PC portable 版本共存：PWA 的引入不得要求維護者維護第二條獨立資料管線（例如不得要求額外人工整理另一份不同格式的資料包）

### Key Entities *(include if feature involves data)*
- **版本化詞庫資料包**：每個 release 版本對應的一份可離線使用的詞庫資料檔；以版本號辨識與更新；可被 PWA 緩存
- **離線就緒狀態**：表示當前裝置是否已具備完整離線運作所需資源（包含詞庫資料包）；用於提示與決策（例如是否允許查詢）

## Success Criteria *(mandatory)*

### Measurable Outcomes
- **SC-001**: 在可用網路環境下，使用者能在 1 次開啟流程內完成「離線就緒」（看到明確完成提示）並成功完成至少 1 次查詢
- **SC-002**: 在完成離線就緒後，使用者能在完全離線狀態下成功完成至少 10 次連續查詢而不中斷
- **SC-003**: 每次新 release 發佈時，維護者能在不新增第二條資料建置流程的前提下，同步供應 PWA 與 portable 使用的同版詞庫資料包
- **SC-004**: 在 iOS 緩存被清除的情境下，使用者能從提示理解問題並在重新上線後完成復原；復原後可再次離線查詢

## Assumptions

- 使用者可接受「首次載入需要網路」；離線可用的保證從「離線就緒完成」之後開始
- iOS 可能在系統清理儲存空間時移除離線緩存；此情況屬可接受，但系統需提供清楚提示與復原路徑
- 版本號採用專案 release 的 semver tag 作為單一真源（portable 與 PWA 共用）
- PWA 交付渠道以純靜態網站部署；不引入必需的常駐後端服務作為依賴
