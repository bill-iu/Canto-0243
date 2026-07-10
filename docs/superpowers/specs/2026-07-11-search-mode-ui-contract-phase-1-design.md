# 搜尋模式 UI／contract：Phase 1 設計

日期：2026-07-11
狀態：已獲產品設計核准，待工作計劃確認

## 目標

把搜尋模式的使用者介面收斂為三個搜尋家族：**基本搜尋**、**平仄模式**、**近反義**。數字規則是獨立的 code profile，由搜尋欄下方三個 segmented pills 控制；不再把 `m1`、`m2`、`m3` 當成頂層 UI mode。

Portable、PWA 與 Python 共用一份搜尋模式 contract，避免平仄被 Portable 誤送為 `m3` 的漂移。

## 已定決策

- 搜尋家族為 `basic`、`pingze`、`synonym`。
- code profile 為 `m1`、`m2`、`m3`；基本搜尋與平仄模式都顯示三個 pills。
- 近反義不顯示 pills；每個搜尋 tab 保存自己的**近反義前次0243搜尋模式**。近反義語意關係查詢轉接回該 tab 的基本搜尋與 profile。
- 外部 wire URL 保持既有相容性：基本搜尋使用 `mode=m1|m2|m3`；平仄使用 `mode=pz&pzmode=m1|m2|m3`；近反義使用 `mode=syn`。
- 新 contract 只擁有行為語意與 URL 映射；翻譯、文案與排版留在各 adapter。
- 窄屏 pills 顯示「四聲」、「五聲」、「六聲」；桌面保留完整名稱。可見短標籤不可取代無障礙名稱，三粒固定等寬且不換行。
- PWA warm-up badge 在載入時只顯示「載入中…」，完成時顯示「完成！」約 700ms 後淡出；不顯示百分比或進度圖。reduced-motion 不加入額外動態。

## 架構

新增 machine-readable 搜尋模式 contract，並生成 Python、TypeScript 與 Portable 所需的模式映射資料。每個 adapter 將 UI family/profile 序列化為既有 wire URL，或由既有 URL 還原 UI state。

```text
Search-mode contract
  ├─ Python adapter: validate/interpret wire mode
  ├─ PWA adapter: family + profile + tab/history state
  └─ Portable adapter: menu, pills, URL/fetch state
```

所有 tab history frame 都保留可重播的 wire mode；UI family 是 adapter 的還原結果，而不是新的 URL 格式。這使舊書籤與分享連結保持有效。

## UI 與狀態

- 下拉選單只列三個搜尋家族。
- 在 basic/pingze 的搜尋欄下方顯示同一個 code-profile control；pills 改變目前 tab 的 profile，並重新提交現有查詢。
- 在 synonym 隱藏 control。其 relation syntax 轉接以該 tab 保存的基本 profile 作為 wire mode。
- profile 的短標籤僅由 CSS breakpoint 決定，不建立 viewport JavaScript state。
- warm-up badge 是獨立狀態 module，不再以進度數字參與 header 排版。

## 錯誤處理與相容性

- `mode=pz` 仍是唯一辨識 P/Z 的 wire mode；Portable 不得把 P/Z 轉去 `m3`。
- 不帶 `pzmode` 的平仄 URL 預設 `m1`。
- 基本搜尋的舊 `m1/m2/m3` URL 和既有 tab history 可直接還原。
- 近反義沒有獨立的數字規則控制；轉接時不丟失該 tab 前次基本 profile。

## 驗收

- Portable、PWA 對三個 family/profile 的 URL round-trip 一致。
- 每個 tab 的近反義轉接只使用自己的前次基本 profile。
- P/Z 在 Portable 經 `mode=pz` 查詢；不再有 P/Z→`m3` redirect。
- 窄屏短標籤與桌面完整標籤均具正確 accessible name，三粒 pills 不換行。
- warm-up badge 不呈現數字或圖形，正確走「載入中… → 完成！ → 淡出」。

## 非目標

- 不處理 guide execution contract、fixture／relation runtime、MatchSpec dead path、query transaction 或 compatibility façade。
- 不修改 P/Z parser、MatchSpec slot 語意、排序、去重與分頁。
