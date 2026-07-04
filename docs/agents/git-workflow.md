# Git workflow: `dev` → `main`

整合分支 **`dev`** 係 Cursor／Grok Build 嘅預設工作分支；**`main`** 只經 PR 合併。

## Agent 預設行為

1. **開工前**：`git checkout dev` → `git pull origin dev`（若 `dev` 未存在則由 `main` 建立並 push）。
2. **改完**：commit 到 `dev`，`git push origin dev`。
3. **唔好**直接 commit／push 到 `main`，亦唔好喺 `main` 上改檔。
4. **合併**：用戶確認無問題後，開 PR：`dev` → `main`（`gh pr create --base main --head dev`）。

## 維護者

- 日常開發與 agent 產出：跟 `dev`。
- 發佈與穩定基線：`main`（見 [release.md](../release.md)）。
- 需要 hotfix 時可開 `fix/*` 分支，目標仍係 PR 入 `main`；合併後將 `main` 同步回 `dev`（`git checkout dev; git merge main; git push`）。

## Release / Pages source rule

任何 `redeploy Pages`、refresh release tag、或 rebuild release asset 前，必須先確認 `origin/dev` 已經 merge 到 `origin/main`。若未合入，先完成 `dev -> main` 合併並更新 `origin/main`，再從 `main` 最新 commit 建 tag、刷新 release，或 dispatch Pages workflow。

`pages.yml`、`scripts/release-windows-local.ps1`、`scripts/release-macos-local.sh` 會拒絕未合併的 release source；這是為了避免 PWA 部署了 `main` 舊內容，而 release asset 卻來自 `dev` 新內容。
