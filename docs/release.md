# Release 維護 checklist

## Release source rule

Before any `redeploy Pages`, release tag refresh, or release asset rebuild, `origin/dev` must already be merged into `origin/main`. If not, merge `dev -> main` first, update `origin/main`, then tag or dispatch workflow from the latest `main` commit.

This rule keeps the public Pages build, release tag, and portable assets on one source commit. `pages.yml`, `scripts/release-windows-local.ps1`, and `scripts/release-macos-local.sh` enforce it.

決策背景：[ADR-0068](adr/0068-desktop-pyapp-delivery.md)（**Desktop + PyApp**）、[ADR-0044](adr/0044-portable-delivery-and-release.md)、[ADR-0059](adr/0059-portable-release-fingerprint-update-notice.md)。舊 venv.pack 運送見歷史 [ADR-0067](adr/0067-portable-venv-pack-transport.md)。領域詞彙：[CONTEXT.md](../CONTEXT.md) § **Desktop 套件**、**免安裝交付**、**發佈主理**、**分渠道發佈**、**全量發佈**、**套件發佈指紋**、**套件更新提示**。

**貢獻者**：合併 PR 後**唔需要**執行下列發佈；由具 upstream `gh` 權限嘅維護者依角色發佈。

## 現行維護編排

| | **發佈主理** | **發佈補件** |
|---|-------------|-------------|
| 領域職責 | 建立／刷新 tag、Release notes、上傳 zip（新 tag 一併上傳庫） | 只上傳 macOS tar 至同一 tag |
| 現行常用腳本 | `scripts/release-windows-local.ps1` | `scripts/release-macos-local.sh` |
| 現行常用建置環境 | Windows 本機 | macOS（x86_64） |
| 上傳目標 | upstream Release | 同一 upstream tag |

**arm64** tar 過渡期**不提供**；Release notes 寫清楚。

## v1.1.0 一次性本地 RC — **已退役**

`scripts/v1_1_0_rc.ps1`／`v1_1_0_rc.py`／`pages-v1.1.0.yml` 為歷史候選入口，
**唔再作現行發佈路徑**。`v1.1.0` 與之後版本一律：

1. PR `dev` → `main` 合併  
2. 本機乾淨 `main`（= `origin/main`）  
3. **步驟 0** `client` `npm run build:portable`  
4. **步驟 1** `scripts/release-windows-local.ps1 -Tag v1.1.0 -Upload`（需庫則先 `build-db`）  
5. Pages：`gh workflow run pages.yml`（或 repo 現行 Pages workflow）  

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

## 步驟 0 — Desktop 產品 UI（每次打 zip／tar 前）

下一正式 **Desktop** release **只**帶 `/app` client 殼（`client/dist-portable`）作側車。共享 mjs／CSS SSOT 在 repo 的 **`shared/`**，唔當創作者入口。建置腳本：`scripts/build-desktop.ps1`／`.sh`（需 **Rust/cargo** + Python 3.11；PyApp 首次對創作者要網）。

```bash
cd client && npm ci && npm run build:portable
# 可選：node scripts/portable-host-build-self-check.mjs
```

`scripts/desktop_bundle.ps1`／`build-desktop.*` 會檢查 `client/dist-portable/index.html`；缺則失敗。

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

## 步驟 2 — 發佈補件（macOS Desktop / PyApp）

產物：`canto-0243-desktop-macos-{arch}.tar.gz`（**唔再**上傳 legacy `portable-macos` tar）。需 **Rust/cargo**。

```bash
export GH_REPO=bill-iu/Canto-0243   # fork clone 時必設
source "$HOME/.cargo/env"

git fetch origin --tags
git checkout v1.7.0

# 或：bash scripts/macos-tar.sh --tag v1.7.0 --test
bash scripts/release-macos-local.sh --tag v1.7.0 --test
# 上傳：必從 Release 下載 lyrics.db；只上傳 Desktop tar + manifest
bash scripts/release-macos-local.sh --tag v1.7.0 --arch x86_64 --upload
```

須 `gh auth` 對 upstream 有 **contents: write**。詳見 [macos-maintainer.md](macos-maintainer.md)。

## 步驟 3 — Pages（PWA）

見 [pwa.md](pwa.md)：從 **同一 tag** Release 下載 `lyrics.db` 再 deploy。同 tag 換庫快照後須 redeploy Pages；大換庫用新 tag。

## 驗收（macOS）

下載 `canto-0243-desktop-macos-*.tar.gz` → 解壓 → 雙擊 **`Canto-0243.app`**（**首次可需網**裝 CPython 3.11）。Gatekeeper **只對 `.app` 一次**（右鍵打開／仍要開啟）；唔使對 runtime 再放行（ADR-0070）。

## 退役說明

- **詞庫發佈**（只換 db／json）：已取消；勿再跑 `release-lexicon.yml`。
- 大換庫 = 新 semver **全量發佈**；細換庫 = 同 tag + `-WithLexicon`（見分級表）。
