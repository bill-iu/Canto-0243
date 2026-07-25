# Candidate 01：本地化目錄與模式選單 seam 實作計劃

日期：2026-07-26  
狀態：grilling 完成，待實作  
目標分支：`dev`

## Problem Statement

目前 UI 語系選擇、fallback、簡體生成及文案分散於多個 caller。新增
`zh-Hans` 已造成約 30 個程式檔改動，而 client 約有 159 個語系判斷散落在
26 個檔案。模式選單仍以 `lang === 'zh' ? … : English` 選擇多段文案，
令簡體模式錯誤落入英文。

模式選單亦同時知道文案、搜尋 family、Desktop 停止政策、字體設定、功能頁
可見性、DOM 量度、窄屏 scale 與事件抑制。它的 interface 包含大量個別
callback；`mode-menu-fit.ts` 則只有一個 caller，純比例 self-check 沒有覆蓋
真正出錯的 DOM 時序、`visualViewport`、CSS cascade 或窄屏狀態。

本重構要提高本地化與模式選單 module 的 depth、leverage 及 locality，同時
保持 PWA、Desktop、手機與桌面瀏覽器的可觀察行為一致。

## Solution

建立 domain-scoped 本地化 module：

- 繁中為 canonical UI 文案，英文由人手維護。
- 簡中由 OpenCC 在開發／檢查階段生成，生成結果提交 repo。
- 簡中術語例外集中於 canonical override，不手改生成檔。
- CI 驗證生成檔可重現及各 catalog 結構一致。
- 前端正式建置不新增 Python／OpenCC 依賴。
- Caller 只取得所屬 domain 的結構化 catalog，不知道 fallback 或生成
  implementation。
- 簡中與英文在正式版缺漏時 fallback 到繁中；再缺漏才顯示可辨識 key。
- 開發／CI 對缺 key、結構或參數不符直接失敗。

語系預設規則：

- 已保存的使用者選擇永遠優先。
- `zh-Hans`、`zh-CN`、`zh-SG` 預設簡體。
- `zh-Hant`、`zh-HK`、`zh-MO`、`zh-TW` 預設繁體。
- 未標明 script／region 的 `zh` 預設繁體。

模式選單方面：

- 模式選單 catalog 擁有全部可見文案及 ARIA 文案。
- 選單模型集中項目分組、可見性與主機政策。
- 視覺 implementation 只處理呈現和互動。
- 刪除只有單一 caller 的 `mode-menu-fit.ts` seam，將 viewport 量度、
  scale 及 scroll fallback 收回模式選單 implementation。
- 不為本重構新增 Playwright／Vitest；以既有自檢、build 及實際瀏覽器
  viewport smoke 驗證 layout。

## Commits

以下每個提交都必須保持 codebase 可建置、可測試及可回退。不要把多個步驟
壓成單一大型提交。

### Commit 1：鎖定現有語系行為

- 為已保存語系優先、三個合法語系值及既有 domain copy 輸出加入
  characterization tests。
- 覆蓋目前 fallback 的安全行為。
- 不改產品行為或 caller。

### Commit 2：加入語系正規化 module

- 建立語系值與瀏覽器語言正規化的深 module。
- 落實 `zh-Hans/CN/SG`、`zh-Hant/HK/MO/TW` 與裸 `zh` 的決策。
- 保持已保存設定優先。
- 只經 module interface 測試，不測內部 helper。

### Commit 3：建立 domain catalog 基礎

- 建立繁中 canonical、英文 catalog、語系選擇及正式版 fallback 的共用
  implementation。
- 先遷移一個小型 domain 驗證結構化 catalog seam。
- 保留既有 caller interface 作短期 adapter，避免同一提交大面積改 caller。

### Commit 4：把簡中生成改成 deterministic output

- 停止由生成腳本直接改寫手寫原始檔。
- 由繁中 canonical 及集中例外表產生獨立簡中 generated catalog。
- 生成檔帶有不可手改標記並提交 repo。
- 提供只檢查、不改檔的模式，供 CI 驗證生成結果最新。
- 保持一般前端建置不依賴 Python／OpenCC。

### Commit 5：遷移既有 shared i18n modules

- 每次只遷移一個既有 domain。
- 各 domain 改用共用語系正規化及 generated catalog。
- 保留原有可觀察輸出與 lazy-loading 特性。
- 每遷移一個 domain 便執行其既有 self-check。

### Commit 6：遷移模式選單文案

- 建立模式選單的結構化 catalog。
- 移除 inline 繁／英 ternary。
- 補齊簡體的可見文案、說明、ARIA label、Desktop 停止政策及詞庫版本文字。
- 保持快捷鍵、圖示與現有操作行為不變。

### Commit 7：深化模式選單模型

- 將項目分組、可見性、選取狀態及主機政策集中於選單模型。
- 縮小 `App` 與工作台必須知道的選單 interface。
- 不把 DOM、React state 或 navigation implementation 放入 catalog。
- 刪除只搬運常數、且未通過 deletion test 的淺 module。

### Commit 8：收回模式選單 layout implementation

- 刪除 `mode-menu-fit.ts` 及只測比例的 self-check。
- 將 viewport 量度、窄屏 scale、最小 scale、resize listener 及 scroll
  fallback 集中於模式選單。
- 維持現有 visual viewport 行為及 CSS custom property。
- 不新增永久 browser test framework。

### Commit 9：遷移搜尋外框與結果文案

- 將搜尋外框、空結果、結果統計及相關 ARIA 文案遷移至各自 catalog。
- 每次只遷移一個 locality。
- 不改查詢模式、結果排序、詞條 lookup 或顯示資料的繁簡轉換。

### Commit 10：遷移詞條詳情與功能頁文案

- 遷移詞條詳情、About、Guide 及其結構化 copy。
- 保持 Guide lazy load，不把大型 catalog 拉入初始 bundle。
- 驗證三語 catalog 的結構和參數一致。

### Commit 11：遷移工作台及渠道文案

- 遷移工作台、Desktop/PWA banner、更新提示及其他純 UI 文案。
- 保留候選理由、讀音、詞條與使用者資料的現有轉換規則。
- 不改工作台 session、候選 snapshot 或查詢 implementation。

### Commit 12：加入防漂移檢查

- CI 驗證 generated catalog 最新、三語結構完整、參數一致。
- 阻止新增純 UI 文案的 inline 三語分支。
- 允許必要的語系行為分支，例如 `document.documentElement.lang`、locale
  detection 及使用者資料轉換；檢查規則要明確列出這些例外。

### Commit 13：刪除過渡 implementation

- 所有 caller 遷移後刪除舊 source-rewrite generator。
- 刪除不再有 caller 的 adapter、fallback 及淺 interface。
- 以 deletion test 確認被刪 module 的複雜度沒有重現在多個 caller。

### Commit 14：跨渠道驗收及文件收尾

- 執行 TypeScript typecheck、前端 build、Python smoke 及受影響 self-check。
- 在手機窄屏及桌面 viewport 實測三語選單。
- 覆蓋開啟、resize、無裁切、scroll fallback、Escape、outside-click。
- 驗證 PWA 與 Desktop 的語系保存、首次語系選擇及選單行為一致。
- 更新活文件，記錄 canonical、generated catalog、override 及檢查方式。

## Decision Document

- 採 domain-scoped 結構化 catalog，不採全域字串 key 袋。
- 繁中 canonical、英文人手維護、簡中 generated。
- generated catalog 提交 repo；CI 驗證可重現。
- 簡中術語例外集中管理。
- 前端 runtime 不用 OpenCC 轉換 UI 文案。
- 使用者資料及詞條的 runtime 繁簡轉換不屬本重構。
- 已保存語系優先；首次語系按 script／region 判斷。
- 開發／CI 對 catalog 錯誤失敗；正式版安全 fallback。
- 模式選單 layout 只有一個 caller，不保留獨立 fit seam。
- 不為單一選單新增大型 browser test framework。

## Testing Decisions

良好測試只穿過 module interface 驗證外部行為，不依賴 catalog 內部儲存方式、
生成 helper 或 React implementation 細節。

必測 module：

- 語系正規化：保存值、script、region、裸 `zh`、非中文。
- Catalog 選擇：繁中、簡中、英文及正式版 fallback。
- Generated catalog：可重現、例外生效、結構及參數一致。
- 各 domain copy：既有輸出、lazy-loading 及動態參數。
- 模式選單：三語可見文案、ARIA、主機政策與 action 描述。

既有先例：

- shared i18n module 的 self-check。
- client TypeScript self-check scripts。
- Python smoke tests 對 Node self-check 的調用。
- PWA build 及現有渠道 smoke。

Browser smoke viewport 至少包括：

- 窄手機 viewport。
- 一般手機 viewport。
- 桌面 viewport。
- 視窗高度不足、觸發 scroll fallback 的 viewport。

## Out of Scope

- 詞條、搜尋結果及使用者輸入的 runtime 繁簡轉換。
- 查詢語法、MatchSpec、搜尋排序及搜尋效能 implementation。
- 工作台 session、候選 snapshot 或逐字讀音 cache。
- 模式選單的視覺重新設計。
- 新增 Playwright、Vitest 或其他大型測試 harness。
- Candidate 02、03、04、05 的 implementation。
- 本計劃階段建立 GitHub issue。

## Handoff

Luna 實作時：

1. 保持在 `dev`，先同步 `origin/dev`。
2. 按上述提交次序工作；如需合併或改序，先記錄原因。
3. 每個提交只包含該步驟所需檔案，文字檔保持 LF。
4. 每個提交後跑最小相關驗證；Phase 結束跑完整受影響驗證。
5. 完成後 commit 並 push 到 `origin/dev`。
6. 回報提交清單、測試結果、未完成項與任何偏離計劃之處。
7. 不建立 PR 到 `main`；待 sol 完成下一輪 review／grilling。
