# 搜尋模式 UI／contract：Phase 1 工作計劃

> 本文件是 Phase 1 唯一工作計劃；其餘架構候選待本 phase 驗收及提交後再各自 grill。

## 目標

以搜尋模式 contract 收斂 Portable、PWA、Python 的 mode/profile 語意，實作三個頂層搜尋家族、可重播的每 tab profile、窄屏 profile pills 與無數字 warm-up badge。

## 範圍與決策

- family：`basic`／`pingze`／`synonym`。
- profile：`m1`／`m2`／`m3`；basic/pingze 顯示，synonym 隱藏。
- wire：basic=`m1|m2|m3`、pingze=`pz&pzmode=`、synonym=`syn`。
- synonym 的關係語法轉接使用同一 tab 的近反義前次0243搜尋模式。
- 窄屏 pills：四聲／五聲／六聲；桌面保留完整名稱與 accessible name。
- warm-up badge：載入中… → 完成！ → 淡出，無數字、無進度圖。

## 依賴順序任務

### WP-01：建立搜尋模式 contract 與生成檢查

- [ ] 建立搜尋 mode/profile 的 machine-readable contract，產出 Python、TypeScript 與 Portable 所需映射。
  - 依賴：無。
  - 邊界：`contracts/`、既有 codegen scripts、Python／TS generated mode metadata。
  - 完成條件：每個 family/profile 只在 contract 定義一次；生成檔不可手寫漂移。
  - 驗證：codegen `--check` 與 contract shape tests。

### WP-02：收斂 URL、tab history 與搜尋轉接

- [ ] 以 contract 還原／序列化 PWA 與 Portable 的 family/profile；每個 tab 保存前次基本 profile。
  - 依賴：WP-01。
  - 邊界：PWA mode metadata、URL、query tabs；Portable mode state、tab history、fetch/query explain。
  - 完成條件：舊 URL 仍可用；P/Z 只送 `mode=pz`；synonym 轉接不跨 tab 取 profile。
  - 驗證：URL/history unit cases、Portable mode-detect／PWA state self-check、Python route input tests。

### WP-03：改為三家族 menu 與共用 profile pills

- [ ] Portable 與 PWA 的下拉選單只列 basic/pingze/synonym；basic/pingze 的搜尋欄下共用 profile pills。
  - 依賴：WP-02。
  - 邊界：Portable HTML/MJS/CSS、`client/src/mode-menu.tsx`、`client/src/App.tsx`、`client/src/pwa-app.css`、Open Design tokens。
  - 完成條件：profile pills 更新當前 tab 查詢與 URL；synonym 不顯示 pills。
  - 驗證：typecheck、mode menu self-check、窄屏目視／DOM assertion。

### WP-04：收斂 warm-up badge

- [ ] 將 PWA warm-up badge 改為純狀態文字與完成淡出。
  - 依賴：無。
  - 邊界：`client/src/components/TailPreloadBadge.tsx`、`frontend/shell.css`。
  - 完成條件：沒有百分比與進度圖；完成狀態可見後淡出；reduced-motion 可讀。
  - 驗證：state transition test、窄屏 visual check、typecheck。

### WP-05：整合驗收、提交與進度記錄

- [ ] 跑雙端 targeted checks，更新本計劃，僅 stage 本 phase 檔案並提交推送 `dev`。
  - 依賴：WP-01、WP-02、WP-03、WP-04。
  - 邊界：本計劃列出的程式、測試與文件。
  - 完成條件：無 P/Z→m3、URL/profile round-trip 正確、窄屏無溢出、badge 無數字。
  - 驗證：Python targeted unittest、PWA self-check、`npx tsc --noEmit -p tsconfig.json`、`npm run build`、`git diff --check`。

## 風險與非目標

- contract 的生成輸出需配合現有 `frontend/*.mjs` 無 bundler 路徑。
- 保留既有 URL 是兼容性優先；不引入 `mode=basic` 新 URL。
- guide、relation runtime、MatchSpec、query transaction 與 facade cleanup 不屬本 phase。

## 進度記錄

- 2026-07-11：設計已獲確認；待工作計劃確認後實作。
