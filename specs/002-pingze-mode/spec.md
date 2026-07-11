# Feature Specification: 平仄模式

**Feature Branch**: `002-pingze-mode`

**Created**: 2026-07-10

**Status**: Ready for planning

**Input**: Add a dedicated 平仄 mode with selectable 0243, 02493, and 394052 sub-modes. P and Z always use 394052 tone classes; numeric positions use the selected sub-mode. Support mixed positional patterns and existing serial, wildcard, literal-anchor, rhyme-anchor, and missing-character operations, while excluding Jyutping anchors.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 搜尋平仄位置模式 (Priority: P1)

填詞者可選擇平仄模式，輸入由 `P`、`Z`、數字和 `?` 組成的逐位模式，以尋找符合平仄與聲調限制的詞條。

**Why this priority**: 這是平仄模式的核心價值，亦解決現有 `p`／`z` 粵拼聲母被平仄語法截走的問題。

**Independent Test**: 在平仄模式搜尋 `PZ?`、`?PZ` 與 `PZ3`，核對每個結果都符合其逐位條件。

**Acceptance Scenarios**:

1. **Given** 使用者在平仄模式，**When** 搜尋 `PZ?`，**Then** 系統只列出第一位為平、第二位為仄、第三位不限的三位結果。
2. **Given** 使用者在一般搜尋模式，**When** 輸入含 `p` 或 `z` 的粵拼片段，**Then** 系統按粵拼處理，不自動轉入平仄模式。
3. **Given** 使用者在平仄模式，**When** 搜尋 `PZ3`，**Then** 第一、二位按平仄限制，第三位按目前 sub-mode 的數字規則限制。

---

### User Story 2 - 選擇數字聲調規則 (Priority: P2)

填詞者可在平仄模式內切換 0243、02493 與 394052 sub-mode，控制數字位置的聲調等價規則，而不改變 `P`／`Z` 的平仄判定。

**Why this priority**: 使用者需要同時表達穩定的平仄類別與不同精度的數字聲調限制。

**Independent Test**: 對同一個含數字 slot 的平仄模式，依次切換三個 sub-mode，核對數字位置與對應純數字搜尋的規則一致，且 `P`／`Z` 結果不變。

**Acceptance Scenarios**:

1. **Given** 使用者在平仄模式，**When** 切換 sub-mode，**Then** 查詢保留且重新按新 sub-mode 的數字規則顯示結果。
2. **Given** 一個查詢含有 `P` 或 `Z`，**When** 使用者切換 sub-mode，**Then** 平與仄的定義維持不變。
3. **Given** 使用者分享或重新開啟平仄搜尋，**When** 連結或 tab 還原，**Then** 系統還原原本的 sub-mode。

---

### User Story 3 - 組合現有錨語法 (Priority: P3)

填詞者可在平仄模式把平仄／通配位置條件與既有字面、韻錨及缺字型操作組合，而既有錨的語義不變。

**Why this priority**: 這令平仄可融入既有工作流，而非只可作孤立串列搜尋。

**Independent Test**: 搜尋 `PZ好=` 與 `?PZ好=`，核對前段位置符合平仄／通配條件，且 `好=` 仍按既有韻錨語義運作。

**Acceptance Scenarios**:

1. **Given** 使用者在平仄模式，**When** 搜尋 `PZ好=`，**Then** 前兩位受平仄限制，而 `好=` 保持既有韻錨語義。
2. **Given** 使用者在平仄模式，**When** 使用粵拼錨語法，**Then** 系統說明該語法在平仄模式不受支援，並指引使用者切換一般搜尋模式。

### Edge Cases

- `?` 只代表一個位置，不能匹配任意長度。
- 一般模式中的大寫或小寫 `P`／`Z` 不觸發平仄自動切換。
- 平仄模式內無法組成合法語法的輸入顯示平仄模式專屬提示，不回落為粵拼。
- 沒有指定 sub-mode 的平仄分享連結以 0243 sub-mode 開啟。

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 系統必須提供獨立的平仄模式，讓使用者明確選入或離開。
- **FR-002**: 平仄模式必須提供 0243、02493、394052 三個可切換 sub-mode，並保存目前選擇於搜尋 tab 與分享連結。
- **FR-003**: 在平仄模式中，`P` 必須代表該位置為平，`Z` 必須代表該位置為仄，且兩者的判定不受 sub-mode 影響。
- **FR-004**: 在平仄模式中，數字位置必須使用所選 sub-mode 與相同位置純數字搜尋一致的聲調等價規則。
- **FR-005**: 在平仄模式中，`?` 必須代表剛好一個完全不設限制的位置。
- **FR-006**: 系統必須允許平仄、數字與 `?` 位置條件結合既有合法的串列、字面錨、韻錨及缺字型操作，而不改變既有錨的語義。
- **FR-007**: 平仄模式必須拒絕粵拼錨，並提供可行的切換模式指引。
- **FR-008**: 在非平仄模式中，系統不得將 `P` 或 `Z` 解讀為平仄，也不得自動切換模式。
- **FR-009**: 系統必須保留既有非平仄搜尋的結果排序、去重與分頁行為。
- **FR-010**: 沒有 sub-mode 資訊的平仄搜尋狀態必須以 0243 sub-mode 還原。

### Key Entities

- **平仄搜尋模式**: 使用者明確選取的搜尋範圍，決定 `P`、`Z` 是否有平仄含義。
- **平仄 sub-mode**: 使用者為數字位置選擇的聲調等價規則。
- **位置條件**: 套用至詞條單一位置的平、仄、數字或不限限制，可與既有錨條件組合。
- **搜尋狀態**: 查詢文字、平仄模式與其 sub-mode 的可還原組合。

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 使用者可在一次搜尋中完成 `PZ?`、`?PZ`、`PZ3`、`PZ好=` 和 `?PZ好=` 五種代表性查詢，且每個結果都符合所有指定位置條件。
- **SC-002**: 三個 sub-mode 下，每個含數字位置的平仄查詢與相同數字位置的既有純數字規則完全一致。
- **SC-003**: 代表性的 `p`、`z` 粵拼查詢在一般模式中 100% 不被分類為平仄搜尋，亦不觸發模式切換。
- **SC-004**: 使用者重新開啟平仄搜尋 tab、瀏覽器歷史項目或分享連結時，查詢和所選 sub-mode 均能還原。

## Assumptions

- 平仄模式首次開啟時，使用者可沿用目前或最近使用的 0243 家族模式；沒有可用狀態時使用 0243。
- `P` 表示平（394052 為 0 或 3），`Z` 表示仄（394052 非 0 或 3）。
- 純漢字與不含平仄 token 的既有合法查詢在平仄模式維持既有行為。
- 既有錨語法已定義其位置與寬度規則；本功能只增加可合成的位置條件，不更改該等規則。
