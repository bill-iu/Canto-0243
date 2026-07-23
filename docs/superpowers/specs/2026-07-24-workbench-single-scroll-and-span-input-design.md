# 句格工作台單一捲動與手改輸入欄修復設計

日期：2026-07-24

狀態：已批准並實作，待驗證

## 背景

句格工作台目前同時使用整頁垂直捲動與候選面板內捲。手機瀏覽器會把慣性捲動鎖定在起始容器；當整頁仍在減速時，即使下一次手勢落在候選區，候選區亦未必立即接管。現行規格更刻意保留預設 scroll chaining，並由 smoke test 禁止候選區使用 `overscroll-behavior`，因此這是雙層垂直捲動的結構性問題。

窄屏的「手打替換段」表單另有橫向溢出。表單內的 flex label 與 input 缺少允許收縮及限制寬度的規則，input 的固有寬度可以超出句格畫布。

## 決定

工作台改為只有整頁一個垂直捲動擁有者：

- 移除候選結果的獨立垂直 viewport。
- 候選分組與「載入更多」回到正常頁面文流。
- 保留整頁捲動。
- 當頂端輸入區離開 viewport 後，顯示固定的「↑ 回到輸入」按鈕。
- 修正手改表單的寬度約束；窄屏採標籤、輸入框、操作列三行排版。

本設計取代 `2026-07-23-workbench-candidate-inner-scroll-design.md` 的候選內捲、scroll chaining、候選 scroll position reset 與相關驗收要求。舊文件保留作決策歷史，不再代表預期行為。

## 範圍

本次改動包括：

- 工作台候選區的捲動容器與相關狀態。
- 返回頂端輸入區的固定操作。
- 手打替換段表單的響應式排版及寬度約束。
- 對應 client seam、互動與響應式驗證。

本次不改：

- 候選資料、canonical 排序、分組次序或詞條卡片內容。
- POS 與替換條件篩選。
- 空結果分組的預設摺疊／展開規則。
- 候選預覽、套用、放寬與載入更多資料流程。
- 工作台 header、句格格數與詞條密度。

## 單一捲動結構

`candidate-area`、候選標題、提示、`candidate-groups` 與 `candidate-load-more` 全部留在頁面正常文流。`CandidateGrid` 不再渲染可聚焦的 `candidate-scroll` region，也不再接收或管理候選捲動位置。

需要移除：

- `candidate-scroll` 的 `overflow-y`、最高高度及隱藏捲動條 CSS。
- `CandidateGrid` 的 viewport ref。
- `scrollResetKey` prop、effect 與 `scrollTop = 0`。
- `WorkbenchPage` 的 `candidateScrollResetKey`。
- 鎖定舊內捲行為的 smoke assertions。

整頁仍可正常捲動，既有工作台頁面 scroll position 保存行為不變。

## 「回到輸入」操作

### 顯示條件

- 以頂端建立句格輸入區作可見性基準。
- 輸入區仍在 viewport 內時不顯示按鈕。
- 輸入區離開 viewport 後顯示按鈕。
- 返回輸入區後再次隱藏。

### 位置與外觀

- 固定在 viewport 右下角。
- 文案為「↑ 回到輸入」。
- 遵守 `env(safe-area-inset-right)` 與 `env(safe-area-inset-bottom)`。
- 保留至少 44×44 CSS px 的可操作範圍。
- 使用現有 surface、line、ink 與 focus ring token。
- 頁面底部預留足夠空間，避免最後一列候選或「載入更多」永久被按鈕遮住。

### 點擊行為

- 點擊後立即把建立句格輸入區移到 sticky header 下方。
- 不程式化 focus 輸入框，避免自動喚起手機鍵盤。
- 輸入區設定合適的 `scroll-margin-top`，避免被 sticky header 蓋住。
- 按鈕有可讀 accessible name，並支援鍵盤啟動。

## 手打替換段表單

### 共通寬度約束

- 表單本身不得超出句格畫布內容寬度。
- flex/grid item 必須允許收縮。
- label 與 input 的 inline size 不得超出父容器。
- input 使用 border-box 計算，padding 與 border 包含在可用寬度內。
- 長錯誤訊息可以換行，不得撐寬面板。

### 窄屏

在 `max-width: 720px`：

1. 第一行顯示「手打替換段（N 格；規則同起句）」。
2. 第二行顯示獨佔可用寬度的輸入框。
3. 第三行顯示「套用」與「收起」。

按鈕可以並排；空間不足時只允許操作列本身正常換行，不得令 input 縮窄或溢出。

### 寬屏

保留現有緊湊的彈性橫排，但套用相同的寬度安全約束。

## 狀態與資料流

- 返回按鈕的顯示狀態只反映輸入區可見性，不進入 workbench session 或持久化資料。
- 路由離開後清理可見性 observer／listener。
- 返回操作不改候選查詢、鎖定格、替換條件、POS 或 undo 狀態。
- 移除候選 scroll reset 後，載入更多只延長文件內容，不觸發額外捲動。

## 驗收

### Client seams

- `CandidateGrid` 不再包含 `candidate-scroll`、`scrollResetKey` 或 `scrollTop = 0`。
- `WorkbenchPage` 不再建立或傳入 `candidateScrollResetKey`。
- 工作台 CSS 不再為候選結果建立 `overflow-y: auto` 或響應式最高高度。
- 返回按鈕以輸入區可見性控制，並有可讀標籤。
- 返回操作不呼叫 input focus。
- 手改表單包含可收縮、全寬與 border-box 約束。
- 窄屏規則明確建立標籤、input、操作列三行排版。
- 既有候選排序、分組、POS、替換、預覽與載入 seams 保持通過。

### 瀏覽器驗證

以 375px viewport 驗證：

1. 開啟兩格或以上的手打替換段。
2. input、label、按鈕及錯誤訊息全部留在句格畫布內。
3. 從頁首連續滑到候選底部；整段只有頁面接收垂直捲動，沒有手勢接管延遲。
4. 頂端輸入區離開畫面後顯示「↑ 回到輸入」。
5. 點擊後輸入區完整顯示在 sticky header 下方，手機鍵盤不會自動出現。
6. 返回頁首後按鈕隱藏。
7. 候選分組、排序、載入更多與套用結果與改動前一致。

另以寬屏驗證手改表單仍維持緊湊排版，候選結果隨整頁正常捲動。

### 命令

- 相關 workbench client smoke。
- workbench 單元／回歸測試。
- client lint。
- production build。

## 非目標

- 以 `overscroll-behavior` 修補巢狀捲動。
- 固定或 sticky 候選分組標題。
- 候選虛擬化。
- 自動無限載入。
- 持久化頁面或候選捲動位置的新機制。
- 點擊返回按鈕後自動進入輸入狀態。
