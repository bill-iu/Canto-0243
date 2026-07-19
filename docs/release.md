# Release 維護 checklist

## Release source rule

Before any `redeploy Pages`, release tag refresh, or release asset rebuild, `origin/dev` must already be merged into `origin/main`. If not, merge `dev -> main` first, update `origin/main`, then tag or dispatch workflow from the latest `main` commit.

This rule keeps the public Pages build, release tag, and portable assets on one source commit. `pages.yml`, `scripts/release-windows-local.ps1`, and `scripts/release-macos-local.sh` enforce it.

決策背景：[ADR-0044](adr/0044-portable-delivery-and-release.md)、[ADR-0059](adr/0059-portable-release-fingerprint-update-notice.md)。領域詞彙：[CONTEXT.md](../CONTEXT.md) § **發佈主理**、**發佈補件**、**分渠道發佈**、**全量發佈**、**發佈詞庫快照**、**套件發佈指紋**、**套件更新提示**。

**貢獻者**：合併 PR 後**唔需要**執行下列發佈；由具 upstream `gh` 權限嘅維護者依角色發佈。

## 現行維護編排

| | **發佈主理** | **發佈補件** |
|---|-------------|-------------|
| 領域職責 | 建立／刷新 tag、Release notes、上傳 zip（新 tag 一併上傳庫） | 只上傳 macOS tar 至同一 tag |
| 現行常用腳本 | `scripts/release-windows-local.ps1` | `scripts/release-macos-local.sh` |
| 現行常用建置環境 | Windows 本機 | macOS（x86_64） |
| 上傳目標 | upstream Release | 同一 upstream tag |

**arm64** tar 過渡期**不提供**；Release notes 寫清楚。

## v1.1.0 一次性本地 RC

`v1.1.0` 唔經 `/beta/` 或 prerelease。先將 `dev` 經 PR 合入 `main`，再喺
Windows 由乾淨、等同 `origin/main` 嘅 `main` 建候選：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/v1_1_0_rc.ps1 -Mode Build
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/v1_1_0_rc.ps1 -Mode Verify
```

`Build` 固定只認 `v1.1.0`，同輪產生詞庫、Windows zip、正式路徑 PWA
archive 同 `dist/v1.1.0-rc-manifest.json`。manifest 綁 source commit、固定 gate、
檔案大小與 SHA-256。任何程式、DB 或產物改動後都要整批重建、重新驗收。

維護者完成本機 PWA build preview、離線測試及 portable 異路徑解壓 smoke 後，
先明確批准上傳。上傳只消費已驗收檔案，唔 build：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/v1_1_0_rc.ps1 -Mode UploadDraft
```

此一次性 RC 命令只跑直接證明產物可用嘅短 gates：v1.1.0 合約、POS 自檢、
PWA／portable build、Pages 封裝，以及 portable 異路徑 readiness／search／shutdown
smoke。依維護者決定，唔跑全量 smoke、seam、guide、typecheck、lint 同 golden
parity；最終互動驗收由維護者上傳前喺本機完成。

此步建立／刷新 draft、核對遠端 asset size，並 dispatch
`pages-v1.1.0.yml`。確認正式 Pages 已載入同一 `v1.1.0`／DB fingerprint 後：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/v1_1_0_rc.ps1 -Mode Finalize -PagesVerified
```

`Finalize` 只將已部署嘅 draft 轉正式 Release；唔重建。Intel macOS tar 之後依
步驟 2 補入同一 tag。呢套入口、manifest 同 Pages workflow **只限 v1.1.0**；
後續版本沿用一般 release 工具，唔改參數重用本入口。

### semver：新 tag vs 刷新（分級）

見 CONTEXT **全量發佈**。摘要：

| 情況 | 做法 |
|------|------|
| **必須新 tag**（schema／查詢行為大改、大規模刪收錄、破壞快取假設、刻意大改；例 `v1.0.9`→`v1.1.0`） | bump **新 semver**；本機 `build-db` 後全量上傳（含 **發佈詞庫快照**） |
| **可同一 tag 換庫快照**（標音／合併修正、少量增刪讀音或字面、短窗熱修） | **刷新同一 tag** + `build-db` + `-WithLexicon` 覆寫 `lyrics.db`／`words-lexicon.json`；**須同時重打並上傳 Portable zip／tar**（寫入 **套件發佈指紋**；見 ADR-0059） |
| 程式 bugfix／打包修正（庫不變） | **刷新同一 tag**（`git tag -f` + 重傳 zip／tar）；**唔** `build-db`；**唔**覆寫庫資產 |
| 主理刷新 tag 後 | 發佈補件 **必須** checkout 該 tag、重 build、覆寫 tar |

`lyrics.db` **唔**入 git；以本機檔或 Release **發佈詞庫快照** 為準。獨立「只換庫」workflow **已退役**。

### 分平台可交付

主理已 Publish zip、macOS tar 未補時：Windows 創作者可下載 zip；跨平台驗收仍須 zip + x86_64 tar 齊。

## 步驟 0 — Portable 產品 UI（每次打 zip／tar 前）

下一正式 portable release **只**帶 `/app` client 殼（`client/dist-portable`）。共享 mjs／CSS SSOT 在 repo 的 **`shared/`**，唔當創作者入口。

```bash
cd client && npm ci && npm run build:portable
# 可選：node scripts/portable-host-build-self-check.mjs
```

`scripts/portable_bundle.ps1`／`build-portable.sh` 會檢查 `client/dist-portable/index.html`；缺則失敗。

## 步驟 1 — 新 tag（換庫／可感知變更）

```powershell
# 前置：本機重建詞庫（只喺庫有變時）
#   python scripts/bootstrap_data.py
#   python -m ingest build-db
# 前置：步驟 0（build:portable）已成功
powershell -ExecutionPolicy Bypass -File scripts/release-windows-local.ps1 -Tag v1.7.0 -Upload
```

會：確保有 `lyrics.db` → build zip（寫 **套件發佈指紋**）→（**新 Release**）export lexicon → 建立 Release → 上傳 **zip + lyrics.db + words-lexicon.json + portable-manifest-windows.json**。

可選：`-NotesFile path\to\notes.md`、`-SkipReadmeSync`、`-Draft`。

## 步驟 1b — 刷新同一 tag（程式-only）

```powershell
git tag -f v1.0.0 HEAD
git push -f origin v1.0.0
# 本機有 lyrics.db 就用；冇就自動從該 tag Release 下載（唔 build-db）
powershell -ExecutionPolicy Bypass -File scripts/release-windows-local.ps1 -Tag v1.0.0 -Upload -SkipReadmeSync
```

會：重打 zip（刷新指紋）；預設 **上傳 zip + portable-manifest-windows.json**（程式-only；唔覆寫庫）。  
同 tag 換庫快照：加 `-WithLexicon` 覆寫 `lyrics.db`／`words-lexicon.json`（須本機已 `build-db`，且須重打套件）。

**唔好**喺刷新時刪除 Release 上嘅 `lyrics.db`。

## 步驟 2 — 發佈補件（macOS）

```bash
export GH_REPO=bill-iu/Canto-0243   # fork clone 時必設

git fetch upstream --tags
git checkout v1.7.0

bash scripts/release-macos-local.sh --tag v1.7.0 --test
# 上傳：必從 Release 下載 lyrics.db（唔用 stale 本機 copy）；只上傳 tar
bash scripts/release-macos-local.sh --tag v1.7.0 --arch x86_64 --upload
```

須 `gh auth` 對 upstream 有 **contents: write**。

## 步驟 3 — Pages（PWA）

見 [pwa.md](pwa.md)：從 **同一 tag** Release 下載 `lyrics.db` 再 deploy。同 tag 換庫快照後須 redeploy Pages；大換庫用新 tag。

## 驗收（macOS）

下載 tar → 解壓 → 雙擊 `Canto-0243.command`（若 Gatekeeper 擋：系統設定 → 隱私與安全性 → 仍要開啟）。

## 退役說明

- **詞庫發佈**（只換 db／json）：已取消；勿再跑 `release-lexicon.yml`。
- 大換庫 = 新 semver **全量發佈**；細換庫 = 同 tag + `-WithLexicon`（見分級表）。
