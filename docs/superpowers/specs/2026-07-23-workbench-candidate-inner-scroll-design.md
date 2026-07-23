# 句格工作台候選詞條內捲設計

> 已由 `2026-07-24-workbench-single-scroll-and-span-input-design.md` 取代；本文件只保留作決策歷史。

日期：2026-07-23

## 目標

句格工作台顯示大量候選詞條時，候選結果改在候選面板內獨立捲動並隱藏捲動條。整體工作台頁面繼續正常捲動；當候選內捲區到頂或到底後，後續手勢自然接續捲動整頁，讓創作者可直接回到頁面頂部的輸入欄。

## 範圍

本次只改候選結果區的捲動責任與捲動位置管理，不改：

- 候選資料、分組、排序或詞頻規則
- POS 篩選行為
- 候選分頁游標與「載入更多」資料流程
- 空結果分組的摺疊／展開行為
- 候選預覽與套用流程
- 整體工作台頁面的捲動能力

## 結構

`candidate-area` 保持在工作台頁面的正常文流中。新增 `candidate-scroll` viewport，只包住：

- `candidate-groups`
- `candidate-load-more`

以下內容留在 viewport 外，捲動候選時保持可見：

- 面板 eyebrow
- 「替換候選」／「放寬後結果」標題
- 已載／池內結果數量
- 空池提示
- 近義資料不足提示

## 捲動行為

`candidate-scroll` 使用垂直自動 overflow，並隱藏 Firefox、舊 Edge 與 WebKit 捲動條。不得使用 `overscroll-behavior: contain` 或 `none`；沿用預設 scroll chaining：

- viewport 尚可捲時，滾輪或觸控手勢捲動候選。
- viewport 到頂後繼續向頁面上方滑動，整頁接手並可回到輸入欄。
- viewport 到底後繼續向下滑動，整頁亦可接手。

內捲區可聚焦，提供可讀的區域標籤，讓鍵盤使用者能以方向鍵、Page Up、Page Down、Home 與 End 操作。

## 響應式尺寸

只設定最高高度，不設定固定或最低高度。候選不足時按內容自然縮短：

- 窄屏（`max-width: 720px`）：`max-block-size: 52dvh`
- 寬屏：`max-block-size: min(60dvh, 36rem)`

候選面板本身仍隨頁面文流排列；這個高度只限制候選結果 viewport。

## 捲動位置生命週期

`WorkbenchPage` 由延後後的候選 plan 與 POS 篩選建立穩定的 `scrollResetKey`，傳給 `CandidateGrid`。

- 鎖定字面、替換條件、候選模式或 POS 篩選改變時，key 改變，viewport 回到頂部。
- 「載入更多」沿用相同 plan 與 POS，key 不變；新詞條附加後保留目前 scroll position。
- 開關空結果分組或開關候選預覽不改 key，不重設位置。
- 切走再返回工作台時，只要候選身份沒有改變，保留元件仍持有的內捲位置。

候選身份必須來自現有 plan／POS 狀態，不以目前第一個詞條、結果數量或 DOM 內容推測。

## 元件邊界

### `WorkbenchPage`

- 建立 primitive、可比較的 `scrollResetKey`。
- key 只反映候選查詢身份；載入頁數與 loading 狀態不參與。
- 將 key 傳給 `CandidateGrid`。

### `CandidateGrid`

- 擁有 viewport ref。
- `scrollResetKey` 改變時把 viewport 捲動位置重設為頂部。
- 渲染 `candidate-scroll`，把現有候選分組和載入按鈕放入其中。
- 不改分組、卡片、載入與預覽事件。

### CSS

- 設定響應式最高高度與 `overflow-y: auto`。
- 隱藏可視捲動條，但保留捲動能力。
- 不阻止 scroll chaining。

## 驗證

新增或擴充 client seam，確認：

- `candidate-scroll` 同時包住 `candidate-groups` 與 `candidate-load-more`。
- viewport 可聚焦並有可讀標籤。
- `scrollResetKey` 由工作台傳入候選元件。
- key 改變時重設 `scrollTop`。
- CSS 包含寬／窄屏最高高度、`overflow-y: auto` 與三種捲動條隱藏規則。
- CSS 不對 `candidate-scroll` 使用會阻止整頁接手的 overscroll 規則。
- 候選排序、載入、POS 與套用相關 seam 保持不變。

驗證命令包括相關 smoke、workbench 回歸、client lint 與 production build。

## 非目標

- sticky 分組標題
- 虛擬化候選卡片
- 自動無限載入
- 顯示捲動進度或自訂捲動條
- 保存內捲位置到跨重新載入的持久儲存
