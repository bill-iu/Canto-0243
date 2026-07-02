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

## Scenario C (P2): Version alignment across portable and PWA

1. 選定某個 release semver（例如 `vX.Y.Z`）
2. portable 與 PWA 都使用該版號的詞庫資料包
3. 用同一組代表性查詢在兩邊測試

**Expected outcomes**
- 版本號一致
- 查詢結果等價（以使用者可觀察內容為準）

