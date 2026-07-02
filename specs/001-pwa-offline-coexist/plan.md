# Implementation Plan: PWA Offline Coexist

**Branch**: `pwa` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-pwa-offline-coexist/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

建立一個 iOS/Android 可用的 PWA 交付渠道：第一次上線載入後可完全離線查詢；詞庫資料包以 release semver 版本化，與現有 PC portable 共存，維護者不需要維護第二條資料管線。

## Technical Context

**Language/Version**: TypeScript（client），Python（既有 portable / build-db）

**Primary Dependencies**: 前端查詢端（靜態客戶端束）、詞庫資料包（SQLite 檔作為靜態資源）、PWA 能力（Service Worker + 安裝體驗）

**Storage**: 單一離線詞庫資料包（每個 release 一份）

**Testing**: 以端到端驗證為主：iOS/Android 實機離線測試；附帶基本 smoke 檢查（可在 CI 跑）

**Target Platform**: iOS Safari / Android Chrome（PWA），以及免費靜態 hosting（如 GitHub Pages）

**Project Type**: 靜態 PWA（離線可用）＋既有 PC portable（離線單機交付）

**Performance Goals**:
- 第一次載入後，離線開啟可在可接受時間內完成可用（以「可查詢」為準）
- 查詢互動保持可用（不需要即時級，但不能明顯卡死）

**Constraints**:
- 不需要 Apple Developer（不做原生上架/簽名）
- 「完全離線」定義為：首次成功載入並完成離線就緒後可離線使用
- DB 更新策略：只在 release 更新（版本化資產 URL），平時離線使用已緩存版本
- iOS 可能清除 cache：屬可接受，但需提示與自助復原

**Scale/Scope**:
- iOS/Android PWA 的離線交付與更新策略
- 不改變 portable 的核心交付流程；以「同一份詞庫資料包」達成共用

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`/.specify/memory/constitution.md` 目前為模板占位內容，未載明實際約束。此計劃將以既有 repo 約定為準：
- 對用戶承諾：離線單機交付為核心形態；PWA 為新增交付渠道，不引入常駐後端依賴
- 風險承認：iOS cache 限制不可完全避免，需以 UX 提示降低成本

## Project Structure

### Documentation (this feature)

```text
specs/001-pwa-offline-coexist/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)
```text
client/                         # 靜態客戶端束（PWA）
├── public/                     # 靜態資產（含版本化詞庫資料包）
└── src/                        # UI + 瀏覽器查詢引擎

portable/                       # PC portable 交付
app/                            # 既有後端/領域邏輯（portable 路線）
docs/adr/                       # ADR（含 ADR-0023）
scripts/                        # build / release / 資料產物處理
```

**Structure Decision**: 採「靜態 PWA + 既有 portable」並存；PWA 僅新增一個 `client/` 靜態交付渠道與部署步驟，不引入第二條資料建置 SSOT。詞庫資料包以同一個 release semver 版本化，供兩個渠道共用。

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
