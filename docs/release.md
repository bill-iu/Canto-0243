# Release 維護 checklist

決策背景：[ADR-0008](adr/0008-release-publishing-tiers.md)、[ADR-0018](adr/0018-split-channel-release.md)。領域詞彙：[CONTEXT.md](../CONTEXT.md) § 分渠道發佈、全量發佈、詞庫發佈。

## 現行：分渠道全量發佈

| 渠道 | 機器 | 產物 | 腳本 |
|------|------|------|------|
| **Windows** | 本機 Windows | `canto-0243-portable.zip`、`lyrics.db`、`words-lexicon.json` | `scripts/release-windows-local.ps1` |
| **macOS Intel** | Intel MacBook（fork 同步建置） | `canto-0243-portable-macos-x86_64.tar.gz` | `scripts/release-macos-local.sh` |

**同一 GitHub Release tag**（例如 `v1.7.0`）；fork 只作建置工作區，**上傳目標為 upstream**（`bill-iu/Canto-0243`）。

**arm64** tar 過渡期**不提供**；Release notes 寫清楚。

### 步驟 1 — Windows（先 Publish）

```powershell
# 前置：lyrics.db 在 repo 根目錄；gh auth login
powershell -ExecutionPolicy Bypass -File scripts/release-windows-local.ps1 -Tag v1.7.0 -Upload
```

會：build zip → export lexicon → 建立／更新 Release → 上傳三件。Release notes 預設註明 macOS x86_64 待補、arm64 暫無。

可選：`-NotesFile path\to\notes.md`、`-SkipReadmeSync`、`-Draft`（少數情況先 draft）。

### 步驟 2 — Intel MacBook（補 x86_64 tar）

```bash
# fork clone：同步 upstream main，確認 lyrics.db 與 tag 一致
git fetch upstream && git checkout main && git merge upstream/main

# 建置 + 本機 smoke（可選）
bash scripts/release-macos-local.sh --tag v1.7.0 --test

# 只上傳 tar 到 upstream（勿覆寫 Windows 的 db/json）
export GH_REPO=bill-iu/Canto-0243   # 或 gh 預設已指 upstream
bash scripts/release-macos-local.sh --tag v1.7.0 --arch x86_64 --upload --tar-only
```

MacBook 須 `gh auth` 對 upstream 有 **contents: write**。

### 步驟 3 — 詞庫發佈（可選，程式不變時）

**前置**：該 tag 已有 **zip + x86_64 tar**（唔要求 arm64）。

```bash
gh release upload v1.7.0 lyrics.db --clobber
# GitHub → Actions → Release (lexicon) → target_tag: v1.7.0
```

### 驗收（macOS）

| 路徑 | 做法 |
|------|------|
| **下載隔離** | 從 Release 下載 x86_64 tar → 解壓 → 雙擊 `.app` → Gatekeeper：**仍要開啟** |
| **本機建置** | `release-macos-local.sh --tag vNEXT --test` → 雙擊 `dist/canto-0243-portable/Canto-0243.command` |

兩邊都通再視為該版 macOS 可交付。

## CI（保留）

| Workflow | 觸發 | 用途 |
|----------|------|------|
| `ci.yml` | push `main`、PR | unit tests |
| `release-lexicon.yml` | `workflow_dispatch` | 詞庫 export + 上傳 db/json |

已停用：`release-full.yml`、`release-macos-intel-beta.yml`（見 ADR-0018）。

## 手動 fallback（無腳本）

1. `scripts/build-portable.ps1` / `scripts/build-portable.sh`
2. `python scripts/export_words_lexicon.py -o dist/words-lexicon.json`
3. `gh release create` / `gh release upload` 同上表資產名

## 常見問題

**Q：只改了 `app/`，要全量嗎？**  
要。須 rebuild 各平台 Portable 並 bump semver（新 tag）。

**Q：ingest 完只想換詞庫？**  
在同一最新 semver 上做詞庫發佈；須 zip + x86_64 tar 已在該 tag。

**Q：Release 已出 zip 但未有 macOS，可以詞庫發佈嗎？**  
不可以。須等 MacBook 補 x86_64 tar。

**Q：Intel Mac 可以建 arm64 嗎？**  
不可以。arm64 須 M 系列 Mac 或日後另設渠道。

**Q：Release 後可刪 `dist/` 嗎？**  
可以。正式資產以 GitHub Release 為準。
