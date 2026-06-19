# Release 維護 checklist

決策背景：[ADR-0008](adr/0008-release-publishing-tiers.md)、[ADR-0018](adr/0018-split-channel-release.md)。領域詞彙：[CONTEXT.md](../CONTEXT.md) § **發佈主理**、**發佈補件**、**分渠道發佈**、**分平台可交付**、**發佈詞庫快照**、**全量發佈**、**詞庫發佈**。

**貢獻者**：合併 PR 後**唔需要**執行下列發佈；由具 upstream `gh` 權限嘅維護者依角色發佈。貢獻者用邊部 OS 開發無關。

## 現行維護編排

領域上係 **發佈主理**／**發佈補件** 兩個角色（見 CONTEXT）；下表係**而家常用**嘅腳本同環境對應，可隨維護者調整。

| | **發佈主理** | **發佈補件** |
|---|-------------|-------------|
| 領域職責 | 建立 tag、Release notes、上傳 zip + 詞庫資產 | 只上傳 macOS tar 至同一 tag |
| 現行常用腳本 | `scripts/release-windows-local.ps1` | `scripts/release-macos-local.sh` |
| 現行常用建置環境 | Windows 本機 | macOS（x86_64；須能跑 `build-portable.sh`） |
| 上傳目標 | upstream Release | 同一 upstream tag |
| 詞庫發佈 | ✅ | ❌（腳本硬拒） |

**arm64** tar 過渡期**不提供**；Release notes 寫清楚。

### semver：新 tag vs 刷新

| 情況 | 做法 |
|------|------|
| 創作者可感知變更（行為、介面、詞庫覆蓋、API） | bump 新 semver |
| 打包／建置修正、內部重構、體感不變 | 發佈主理可 **刷新同一 tag**（`git tag -f` + `--clobber` 重傳）；notes 可不改 |
| 主理刷新 tag 後 | 發佈補件 **必須** checkout 該 tag、重 build、覆寫 tar |

`lyrics.db` **唔保證**在 tag commit 內；以 Release 上 **發佈詞庫快照** 為準（主理 upload 後，補件從 Release 下載對齊）。

### 分平台可交付

主理已 Publish zip、macOS tar 未補時：Windows 創作者可下載 zip；**詞庫發佈**與跨平台驗收仍須 zip + x86_64 tar 齊。

## 步驟 1 — 發佈主理（現行：Windows 腳本）

```powershell
# 前置：lyrics.db 在 repo 根目錄（可為本機 ingest，唔一定要 commit）；gh auth login
powershell -ExecutionPolicy Bypass -File scripts/release-windows-local.ps1 -Tag v1.7.0 -Upload
```

會：build zip → export lexicon → 建立／更新 Release → 上傳 zip + db + json。

可選：`-NotesFile path\to\notes.md`、`-SkipReadmeSync`、`-Draft`。

**刷新同一 tag**（語意不變）：

```powershell
git tag -f v1.0.0 HEAD
git push -f origin v1.0.0
powershell -ExecutionPolicy Bypass -File scripts/release-windows-local.ps1 -Tag v1.0.0 -Upload -SkipReadmeSync
```

## 步驟 2 — 發佈補件（現行：macOS 腳本）

```bash
export GH_REPO=bill-iu/Canto-0243   # fork clone 時必設；gh 預設已指 upstream 可省略

git fetch upstream --tags
git checkout v1.7.0                   # 必須對齊 tag 指向之 commit，唔好用 main 尖端代替

# 建置 + 本機 smoke（可選；唔 upload）
bash scripts/release-macos-local.sh --tag v1.7.0 --test

# 上傳：腳本會驗證 Release 已存在、HEAD==tag、從 Release 下載 lyrics.db，只上傳 tar
bash scripts/release-macos-local.sh --tag v1.7.0 --arch x86_64 --upload
```

須 `gh auth` 對 upstream 有 **contents: write**。

`--tar-only` 仍接受（與 `--upload` 同義）；`--draft`／`--notes-file` 已移除——請由發佈主理建立 Release。

## 步驟 3 — 詞庫發佈（可選，程式不變）

**執行者**：發佈主理。**前置**：該 tag 已有 **zip + x86_64 tar**。

```powershell
# 主理機：ingest 後（近義橋規則變更時見 docs/ingest-bridge-ant.md）
python -m ingest expand-antonyms-syn-bridge --fresh   # 可選；品質閘門更新後
# 詞條標音勘誤累積套用後見 docs/lexicon-corrections.md
python -m ingest apply-lexicon-corrections --apply   # 可選；改 db + export/json + README 詞條數
gh release upload v1.7.0 lyrics.db --clobber
python scripts/export_words_lexicon.py -o dist/words-lexicon.json
gh release upload v1.7.0 dist/words-lexicon.json --clobber
```

或 GitHub → Actions → **Release (lexicon)** → `target_tag: v1.7.0`（CI 備援）。

主理刷新 tag 後，發佈補件須重跑步驟 2，使 tar 與 tag commit 一致。

## 驗收（macOS）

| 路徑 | 做法 |
|------|------|
| **下載隔離** | 從 Release 下載 x86_64 tar → 解壓 → 雙擊 `Canto-0243.command` → Gatekeeper：**仍要開啟** |
| **本機建置** | `release-macos-local.sh --tag vNEXT --test` → 雙擊 `dist/canto-0243-portable/Canto-0243.command` |

兩邊都通再視為該版 macOS 可交付。

## Draft → Publish 前 smoke（全量發佈）

**前置**：該 tag 已有 zip + x86_64 tar + db／json（Draft 可見即可）。

| 平台 | 做法 |
|------|------|
| **Windows** | 從 **Draft Release** 下載 zip（唔用本機 `dist/`）→ 解壓 → `START.bat` → 瀏覽器開查韻頁 |
| **macOS** | 從 **Draft Release** 下載 x86_64 tar → 解壓 → `Canto-0243.command` |

**詞庫行為**（詞庫變更大時必做）：對 2–3 個近義字（例：哀愁、悲傷、憂傷）各查 `字面!`，確認有合理反義、無明顯 hub 噪音。維護者可先用 `python -m ingest report` 對照 `ant_syn_bridge ant rows` 與 checkpoint。

**Publish**：Win + Mac smoke 都通 → GitHub Release 頁 **Publish release**。

## CI（保留）

| Workflow | 觸發 | 用途 |
|----------|------|------|
| `ci.yml` | push `main`、PR | unit tests |
| `release-lexicon.yml` | `workflow_dispatch` | 詞庫 export + 上傳 db/json（備援） |

已停用：`release-full.yml`、`release-macos-intel-beta.yml`（見 ADR-0018）。

## 手動 fallback（無腳本）

1. `scripts/build-portable.ps1` / `scripts/build-portable.sh`
2. `python scripts/export_words_lexicon.py -o dist/words-lexicon.json`
3. 主理：`gh release create`／`upload` zip + db + json；補件：只 `upload` tar 到已存在 Release

## 常見問題

**Q：只改了 `app/`，要全量嗎？**  
要。須 rebuild 各平台 Portable。創作者可感知變更 → bump 新 semver；純打包修正 → 可刷新同一 tag。

**Q：ingest 完只想換詞庫？**  
**詞庫發佈**（發佈主理）；須 zip + x86_64 tar 已在該 tag。Portable zip／tar 唔重建。若只更新近義橋反義，先依 [ingest-bridge-ant.md](ingest-bridge-ant.md) 重跑並驗收。

**Q：近義橋 ingest 中斷點？**  
重新執行 `expand-antonyms-syn-bridge`（無 `--fresh`）會 resume checkpoint；從頭重跑用 `--fresh`。唔好手動刪 lock 檔。

**Q：Release 已出 zip 但未有 macOS tar，可以詞庫發佈嗎？**  
不可以。須等發佈補件上傳 x86_64 tar。

**Q：主理刷新咗 tag，補件 tar 要重做嗎？**  
要。即使 mac 專用程式碼冇變，tar 必須對應 tag 指向之 commit。

**Q：Intel Mac 可以建 arm64 嗎？**  
不可以。arm64 須 M 系列 Mac 或日後另設編排。

**Q：Release 後可刪 `dist/` 嗎？**  
可以。正式資產以 GitHub Release 為準。
