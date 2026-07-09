# 搜尋結果視窗化（擷取頁 × 呈現批次）

大結果集（如平仄串列 `PZ`）若一次畫出整個**擷取頁**會卡頓；若用 IntersectionObserver 在 sentinel 可見時連環觸發，又會未捲動就自動拉完整個總數。連續換查詢（教學例子、debounce 輸入）若每次都撈滿 **擷取頁上限** 並對全量候選 sort，會令上一查堵住下一查。

## 決策

1. **兩層分離**：**擷取頁**與 **呈現批次**（DOM 每次 +200 合併詞條）分開；統計「已擷取 N / 總數」只反映記憶體列數。
2. **首屏擷取 vs 上限**：**擷取頁上限** 1200（load-more／續頁）；**0243搜尋模式**家族 **首屏擷取** 400（offset=0 首查）。近反義池沿用既有較細頁。雙端共用常數。
3. **引擎窗口**：sort／serialize 只服務當前 offset+limit 窗口所需工作，避免先全量 materialize 再 slice（在唔破壞排序契約前提下）。
4. **捲動觸發**：僅 **結果捲動區** 的 `scroll` 事件在 sentinel 進入視窗時擴一批或拉下一**擷取頁**；不用 IO pump、不用假 padding 推 sentinel。
5. **佈局**：`body` 鎖 `100dvh`；`app-shell` 固定視窗高（`height/max-height: 100dvh`）；`main-wrap → search-view → search-results-scroll` flex 鏈 + `min-height: 0`，保證捲動條在**結果捲動區**而非整頁。
6. **雙端共用**：`frontend/infinite-results.mjs` 定義 `RESULT_RENDER_BATCH`；PWA hook 與 Portable workbench 同規則；首屏／上限常數雙端對齊。

**Considered：** 首屏畫晒擷取頁（1200 DOM）——拒絕（卡頓）。首查亦 1200——拒絕（連續查詢 wall time）。IO + scroll pump 連環——拒絕（自動拉完整庫）。每批 50——改 200（減捲動次數、仍可控 DOM）。PWA 改為只 submit 先搜——拒絕（教學 click 已 flush；改觸發模型唔修卡舊結果）。無證據硬補 I2 索引——拒絕（先 U／C／首屏／窗口 sort）。