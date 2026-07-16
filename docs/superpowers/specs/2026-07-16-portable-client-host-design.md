# Portable 餵 client 宿主 — 設計

**日期**：2026-07-16  
**狀態**：已核准（2026-07-16）· 實作計劃見 [`../plans/2026-07-16-portable-client-host.md`](../plans/2026-07-16-portable-client-host.md)  
**地圖**：[維護成本地圖：UI 收斂與後段引擎熱檔](https://github.com/bill-iu/Canto-0243/issues/83)  
**決策依據**：[#84](https://github.com/bill-iu/Canto-0243/issues/84)、[#85](https://github.com/bill-iu/Canto-0243/issues/85)、[#86](https://github.com/bill-iu/Canto-0243/issues/86)、[#87](https://github.com/bill-iu/Canto-0243/issues/87)

## 1. 目標與非目標

### 目標（第 (1) 段結束時）

- Portable 創作者開啟的 UI 來自 **`client` 的 `PORTABLE_HOST` 建置產物**，不再以 `frontend/index.html` 為入口。
- 該宿主使用本機 **`/words/search`** 與 **`/ready`**；**不**註冊 Service Worker、**不**初始化 OPFS／sql.js 瀏覽器查詢引擎。
- **chrome-tabs** 僅在 portable 宿主可用；PWA 維持 pill。
- **關係補錄／詞庫勘誤** 在 portable 宿主可用（本機 API）；PWA 繼續不暴露（既有 `PWA_VIEWS`）。
- 查詢語意／教學範例：**Portable↔PWA parity／guide 閘綠**。
- 發佈 **單一切斷**：下一個正式 portable release 只含新殼入口。
- Repo 內 **`frontend/` 暫留作共享 SSOT**（mjs／CSS）；不當產品入口殼。

### 非目標

- #86 第 (2)(3) 段（清平行殼模組、遷共享、刪 `frontend/` 目錄）
- #87 引擎熱檔拆分（排在第 (1) 段綠燈**之後**）
- 單引擎／Pyodide、PWA 改用 chrome-tabs、功能霧內新產品功能
- 借機變更查詢語意或雙端 explain 創作者文案

### 成功尺

- **必須同**：查詢結果／教學範例雙端綠（既有 parity／guide 契約）。
- **允許異**：chrome-tabs vs pill、就緒閘文案與進度模型、無 SW／install banner、多讀音徽章跟已送出查詢（對齊地圖 #84）。

## 2. PR 切分（方案 1）

| PR | 範圍 | 第 (1) 段綠燈？ |
|----|------|----------------|
| **PR1** | 基建最小切片：建置變體、API 搜尋、`/ready` 閘、FastAPI／launch／bundle 掛新 dist | 否（缺 tabs／維護者／正式切斷） |
| **PR2** | chrome-tabs 僅 `PORTABLE_HOST` | 部分 |
| **PR3** | 維護者工具搬入 portable | 部分 |
| **PR4** | 發佈／文件／CI 切斷＋第 (1) 段收口驗收 | **是**（全綠燈） |

PR1～PR2 之間 Portable 暫用 pill 可接受。

## 3. PR1 技術形態

### 建置

- Vite／env 旗標：`PORTABLE_HOST=1`（名稱可微調，語意固定）。
- 產出目錄約定：**`client/dist-portable/`**（與 PWA 的 `client/dist/` 分離，避免互相覆寫）。
- 此 build：**不**啟用 VitePWA／SW；**不**初始化瀏覽器詞庫開庫與 `QueryEngine`。
- 預設 `npm run build`／Pages：**不變**。

### 執行期（僅 portable 束）

- **搜尋**：建置期分支使 `useSearch`（或等價薄層）走 `GET /words/search/…`，參數／分頁對齊現行 Portable API。
- **就緒**：輪詢 `GET /ready`，解鎖語意跟現行 Portable 契約（非 PWA 下載／OPFS 閘）。
- **Meta**：對齊現有 `canto-portable`、`canto-lexicon-version` 注入（FastAPI 伺 HTML 或建置等效）。
- **分頁 UI**：暫用 pill；chrome-tabs → PR2。
- **維護者 view**：PR1 可繼續隱藏；→ PR3。

### 伺服／啟動／打包

- 靜態掛載前綴：**`/app/`**（內容＝`client/dist-portable`）。不再以 `frontend/` 目錄樹作為產品 UI 掛載源。
- `local_launch.HTML_SUFFIX` → `/app/index.html`（或該束實際 index 檔名）。
- Portable bundle 腳本改複製 `client/dist-portable`（及運行所需資產），**不再**把整棵 `frontend/` 當產品 UI 打進 zip。
- No-cache middleware 範圍改跟 `/app/`。
- 缺 dist 時啟動應**明確失敗**（錯誤訊息指出需先 `PORTABLE_HOST` build），禁止靜默回退舊殼。

### PR1 驗收

- `PORTABLE=1` 本機啟動 → 開啟 `/app/` → `/ready` 解鎖 → 核心查詢有結果。
- PWA build／既有 Pages CI 無回歸。
- 不要求本 PR 達第 (1) 段全綠燈。

## 4. PR2–PR4

### PR2 — chrome-tabs

- 僅 `PORTABLE_HOST` 啟用；狀態層繼續用共享 `query-tabs-state` 等；只換分頁列 UI。
- 驗收：多 tab 開合／還原／URL 不差於現行 Portable 預期。

### PR3 — 維護者工具

- 關係補錄、詞庫勘誤進 `client` portable（本機 API）；PWA 無入口。
- 驗收：portable 可走完現行主路徑。

### PR4 — 切斷與收口

- release／README／CI／煙霧改指 `/app/`＋`dist-portable`。
- 下一正式 portable release **不再**帶舊 `frontend` 入口。
- 跑完 #86 第 (1) 段綠燈清單；在地圖或實作 epic 留「第 (1) 段完成」備註。

## 5. 之後（點名，非本 spec 細設計）

- #86 第 (2)：清 Portable 殼專用模組（見研究筆記 §6 清單），共享仍留 `frontend/`。
- #86 第 (3)：共享遷中立目錄後才刪 `frontend/`。
- #87：雙端 `jyutping_anchor`／`query_explain` 按職責拆；第 (1) 段綠燈後才動。

## 6. 參考

- 研究：`docs/research/2026-07-16-frontend-client-shell-overlap.md`
- ADR-0044（Portable）、ADR-0045（PWA）、ADR-0022（300 行軟限）
- `CONTEXT.md` §就緒閘、§免安裝交付、§搜尋教學驗收
