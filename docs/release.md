# Release 維護 checklist

決策背景：[ADR-0008](adr/0008-release-publishing-tiers.md)。領域詞彙：[CONTEXT.md](../CONTEXT.md) § 全量發佈、詞庫發佈。

## 過渡期（手動，現行）

### 全量發佈

觸發：程式／`requirements.txt`／依賴／正式 semver 版本。

1. 更新 `lyrics.db`（必要時跑 ingest 管線）
2. `python scripts/export_words_lexicon.py -o dist/words-lexicon.json`
3. `python scripts/update_readme_words_count.py`
4. **Windows**：`powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1`
5. **macOS**：`bash scripts/build-portable.sh`
6. 建立 GitHub Release tag `vMAJOR.MINOR.PATCH`
7. 上傳四件套：`lyrics.db`、`words-lexicon.json`、`canto-0243-portable.zip`、`canto-0243-portable-macos.tar.gz`
8. Release notes 註明全量版本與變更摘要

兩平台 zip／`.app` 須來自**同一 tag** 的 build；若只完成一邊，**不要**發佈該 tag。

### 詞庫發佈

觸發：`lyrics.db` 有實質更新、程式與依賴不變。

**前置**：目標 semver 上已有成功全量 Release（含雙平台 Portable）。

1. 更新 `lyrics.db`（ingest 等）
2. `python scripts/export_words_lexicon.py -o dist/words-lexicon.json`
3. 到該 semver 的 GitHub Release **只替換** `lyrics.db` 與 `words-lexicon.json` asset
4. **不要** rebuild zip／`.app`（除非順便做全量發佈）
5. Release notes 追加一行：`詞庫更新 YYYY-MM-DD`（條目數或簡述可選）

勿在未完成全量的 semver 上單獨發詞庫。

## 長期（CI 已落地）

| 類型 | 觸發 | Workflow |
|------|------|----------|
| PR／push `main` | 自動 | `ci.yml`（unit tests） |
| **全量發佈** | push tag `v*.*.*` | `release-full.yml` |
| **詞庫發佈** | Actions → **Release (lexicon)** → Run workflow | `release-lexicon.yml` |

### 全量發佈（CI）

**前置（本地）** — tag 推送前：

```bash
# 1. 準備 lyrics.db（ingest 等）
# 2. 建立 draft release 並上傳 db
gh release create v1.3.0 --draft --title "Canto-0243 v1.3.0"
gh release upload v1.3.0 lyrics.db

# 3. 等幾秒讓 draft 在 API 同步，再推送 tag（觸發 release-full.yml）
sleep 10
git tag v1.3.0
git push origin v1.3.0
```

CI 會：從同 tag 取 `lyrics.db` → Windows／macOS 各 build portable → export `words-lexicon.json` → 上傳四件套 → **取消 draft（正式發佈）**。

若 Windows 或 macOS build 失敗，**不會** publish（ADR-0008 Q5=A）。

**Release 後可刪本機建置暫存**：`dist/` 內 zip、解壓目錄、export 等皆為本機副產物；正式四件套以 GitHub Release 為準。確認 Release 齊全後可執行 `rm -rf dist/`（Windows：`Remove-Item -Recurse -Force dist`）；下次 build 或 export 會自動重建。

### 詞庫發佈（CI）

**前置**：目標 tag 已有 full Release（含 zip + macOS tar.gz）。

```bash
# 1. 上傳新 lyrics.db 到該 tag
gh release upload v1.2.0 lyrics.db --clobber

# 2. GitHub → Actions → Release (lexicon) → Run workflow
#    target_tag: v1.2.0
```

Workflow 會 export `words-lexicon.json`、上傳 db／json，並在 Release notes 追加「詞庫更新 YYYY-MM-DD」。

### 手動 fallback

CI 不可用時，仍可按上方「過渡期（手動）」checklist 操作。

## 常見問題

**Q：只改了 `app/` 或 `frontend/`，要全量嗎？**  
要。創作者 Portable 內嵌程式；須 rebuild zip／`.app` 並 bump semver（或至少新 full tag）。

**Q：ingest 完只想換詞庫，要 bump semver 嗎？**  
不必。在同一最新 semver 上做詞庫發佈即可。

**Q：Windows build 約要幾耐？**  
pre-build venv 路徑約 1–1.5 分鐘（視 pip cache）。兩平台各跑一次。
