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

## 長期（CI 落地後）

| 類型 | 觸發 | Workflow |
|------|------|----------|
| 全量發佈 | push tag `v*.*.*` | `release-full.yml` |
| 詞庫發佈 | `workflow_dispatch` 或 `v*-lexicon` tag | `release-lexicon.yml` |

CI 契約同 ADR-0008：全量 matrix 全綠才發 Release；詞庫只更新 db／json asset。

## 常見問題

**Q：只改了 `app/` 或 `frontend/`，要全量嗎？**  
要。創作者 Portable 內嵌程式；須 rebuild zip／`.app` 並 bump semver（或至少新 full tag）。

**Q：ingest 完只想換詞庫，要 bump semver 嗎？**  
不必。在同一最新 semver 上做詞庫發佈即可。

**Q：Windows build 約要幾耐？**  
pre-build venv 路徑約 1–1.5 分鐘（視 pip cache）。兩平台各跑一次。
