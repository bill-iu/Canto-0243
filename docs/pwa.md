# PWA 發佈（維護者）

本文件描述「PWA 交付渠道」嘅最低成本發佈流程：**先確保 release tag 內有詞庫資料（`lyrics.db`），再部署 Pages**。此順序可避免 Pages workflow 因缺少 `lyrics.db` 而失敗。

## 目標

- PWA 部署位置：GitHub Pages（Project Pages）`/Canto-0243/`
- 詞庫版本：跟 release tag（semver，例如 `v1.0.3`）
- DB 更新：只喺 release 更新（PWA 站點單一 URL，內容隨 release 更新）

## 發佈順序（必做）

### 1) 確保 tag release 已有 `lyrics.db`

- 建立/更新對應嘅 release tag（例如 `v1.0.3`）
- 將 `lyrics.db` 上傳到該 tag 嘅 GitHub Release（同 tag 對齊）

> 註：repo 內已有「詞庫更新」相關 workflow/腳本，可用於更新 release 上嘅 `lyrics.db` 與相關副件（視當前維護流程而定）。

### 2) 部署 PWA 到 GitHub Pages（手動觸發）

1. 到 GitHub Actions
2. 選 **Pages (PWA)** workflow
3. 點 **Run workflow**
4. 輸入 `target_tag`（例如 `v1.0.3`）

workflow 會：
- 從該 tag release 下載 `lyrics.db`
- build `client/`（產出 `lyrics.<tag>.db` 靜態資產）
- deploy 到 GitHub Pages

## 驗證（建議）

部署完成後，用手機：
- 開站一次（在線）→ 等「離線就緒」
- 切飛航模式 → 從主畫面開啟 → 查詢仍可用
- UI 應顯示「詞庫版本：vX.Y.Z」

