# PWA 發佈（維護者）

本文件描述「PWA 交付渠道」嘅最低成本發佈流程：**先確保 release tag 內有詞庫資料（`lyrics.db`），再部署 Pages**。此順序可避免 Pages workflow 因缺少 `lyrics.db` 而失敗。

## 目標

- PWA 部署位置：GitHub Pages（Project Pages）`/Canto-0243/`
- 詞庫版本：跟 release tag（semver，例如 `v1.0.3`）
- DB 更新：大換庫跟 **新 semver 全量發佈**；細換庫可同一 tag `-WithLexicon` 覆寫；程式-only 刷新 **唔**覆寫庫

## 產物體積（研究結論，v1.1.x）

| 比較 | 約略 |
|------|------|
| `client/dist`（PWA 靜態束） | ~90+ MB 碟上（`lyrics.db` + 可選 `.gz` + static-syn／ranking 等） |
| Desktop zip（strip 後） | ~30 MB 壓縮；UI 側車 alone ~5 MB |

**唔係「PWA build ≈ Desktop build」**：PWA 必須帶 **瀏覽器查詢引擎** 物料；Desktop 已按 ADR-0068 §13 剔除呢啲死重。

在**唔傷就緒閘／查詢 latency** 前提下（grill R1）：

- **唔**為瘦產物刪 static-syn／ranking 或只 ship 單庫檔（相容／效能風險）
- 首訪下載 **唔等於** dist 總 MB：runtime 優先 **gzip 詞庫**（manifest `preferCompressed`）；大 JSON 唔入 workbox precache
- 維護期望：接受 PWA 產物偏大；體積對齊 Desktop **唔**作目標

領域詞：CONTEXT § **靜態客戶端束**、**詞庫壓縮傳輸**、**Desktop 套件**。

## 發佈順序（必做）

### v1.1.0 特例：部署已驗收 artifact

`v1.1.0` 用一次性 `pages-v1.1.0.yml`，唔喺 Actions 重跑 Vite。維護者先依
[release.md](release.md) 建好並驗收本地 RC，再以 `v1_1_0_rc.ps1 -Mode
UploadDraft` 上傳 `canto-0243-pages-v1.1.0.tar.gz`、RC manifest 同 `lyrics.db`。

workflow 固定 checkout `v1.1.0`，驗 source 可達 `main`、manifest hash、archive
同 DB 一致後，先交畀 GitHub Pages 原子部署。部署成功及線上 smoke 通過後，
先用 `-Mode Finalize -PagesVerified` 發布正式 Release。此流程只限 `v1.1.0`。

### 0) 確認 release source

`redeploy Pages` 前，必須先確認 `origin/dev` 已經 merge 到 `origin/main`，並從最新 `main` commit 觸發 **Pages (PWA)** workflow。若 `dev` 尚未合入，先 merge `dev -> main`，再 redeploy。

### 1) 確保 tag release 已有 `lyrics.db`

- **新 tag（換庫）**：發佈主理用 `release-windows-local.ps1 -Upload` 首次建立 Release 時會上傳 `lyrics.db`
- **刷新同一 tag（程式-only）**：保留既有 `lyrics.db`；細換庫加 `-WithLexicon` 先覆寫；**唔好刪**後無得下載

獨立「只換庫」workflow 已退役；見 [release.md](release.md)。

### 2) 一般版本部署 PWA 到 GitHub Pages（手動觸發）

1. 到 GitHub Actions
2. 選 **Pages (PWA)** workflow
3. 點 **Run workflow**
4. 輸入 `target_tag`（例如 `v1.0.3`）

workflow 會：
- 從該 tag release 下載 `lyrics.db`
- build `client/`（產出 `lyrics.<tag>.db` 靜態資產）
- deploy 到 GitHub Pages

一般 workflow 已取消 tag-push trigger，只可由 `main` 手動 dispatch，避免 tag
先於 Release assets 上傳完成時誤跑。`v1.1.0` 唔使用本一般 build workflow。

## 驗證（建議）

部署完成後，用手機：
- 開站一次（在線）→ 等「離線就緒」
- 切飛航模式 → 從主畫面開啟 → 查詢仍可用
