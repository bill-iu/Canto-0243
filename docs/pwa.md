# PWA 發佈（維護者）

本文件描述「PWA 交付渠道」嘅最低成本發佈流程：**先確保 release tag 內有詞庫資料（`lyrics.db`），再部署 Pages**。此順序可避免 Pages workflow 因缺少 `lyrics.db` 而失敗。

## 目標

- PWA 部署位置：GitHub Pages（Project Pages）`/Canto-0243/`
- 詞庫版本：跟 release tag（semver，例如 `v1.0.3`）
- DB 更新：跟 **新 semver 全量發佈**（換庫開新 tag）；程式刷新同一 tag **唔**覆寫 Release 上嘅 `lyrics.db`

## 發佈順序（必做）

### 0) 確認 release source

`redeploy Pages` 前，必須先確認 `origin/dev` 已經 merge 到 `origin/main`，並從最新 `main` commit 觸發 **Pages (PWA)** workflow。若 `dev` 尚未合入，先 merge `dev -> main`，再 redeploy。

### 1) 確保 tag release 已有 `lyrics.db`

- **新 tag（換庫）**：發佈主理用 `release-windows-local.ps1 -Upload` 首次建立 Release 時會上傳 `lyrics.db`
- **刷新同一 tag（程式-only）**：保留既有 `lyrics.db` 資產；**唔好刪**

獨立「只換庫」workflow 已退役；見 [release.md](release.md)。

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
