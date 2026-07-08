# 搜尋結果視窗化（擷取頁 × 呈現批次）

大結果集（如平仄串列 `PZ`）若一次畫出整個**擷取頁**會卡頓；若用 IntersectionObserver 在 sentinel 可見時連環觸發，又會未捲動就自動拉完整個總數。

## 決策

1. **兩層分離**：**擷取頁**（API／引擎一次最多 1200 列）與 **呈現批次**（DOM 每次 +200 合併詞條）分開；統計「已擷取 N / 總數」只反映記憶體列數。
2. **捲動觸發**：僅 **結果捲動區** 的 `scroll` 事件在 sentinel 進入視窗時擴一批或拉下一**擷取頁**；不用 IO pump、不用假 padding 推 sentinel。
3. **佈局**：`body` 鎖 `100dvh`；`app-shell` 固定視窗高（`height/max-height: 100dvh`）；`main-wrap → search-view → search-results-scroll` flex 鏈 + `min-height: 0`，保證捲動條在**結果捲動區**而非整頁。
4. **雙端共用**：`frontend/infinite-results.mjs` 定義 `RESULT_RENDER_BATCH`；PWA hook 與 Portable workbench 同規則。

**Considered：** 首屏畫晒擷取頁（1200 DOM）——拒絕（卡頓）。IO + scroll pump 連環——拒絕（自動拉完整庫）。每批 50——改 200（減捲動次數、仍可控 DOM）。