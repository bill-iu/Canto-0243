## Agent skills

Agent 與維護者流程見 `docs/agents/`；貢獻與 PR 見 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)。

唔好無意識改 `skills-lock.json`；只喺有意更新 agent skills 時先改同提交。

### Git Workflow (Dev Branch)
**所有代碼改動必須先 commit+push 到 `dev`，確認後 PR 入 `main`**（見 [`docs/agents/git-workflow.md`](docs/agents/git-workflow.md)）。

**工作流程：**
1. 執行前：`git checkout dev` 並 `git pull origin dev`（如 `dev` 不存在，則從 `main` 建立並推送）
2. 整個任務期間保持在 `dev` 分支
3. 改動後：在 `dev` 提交並 `git push origin dev`
4. **禁止**直接推送到 `main` 或在 `main` 提交
5. 合併到 `main` 前需用戶確認：`gh pr create --base main --head dev`
6. **行尾**：文字檔一律 LF（[ADR-0063](docs/adr/0063-lf-line-endings.md)）。新 clone 跑 `python scripts/install_githooks.py`；commit 前 hook 會自動把 staged CRLF 修成 LF。

### Coding style (Ponytail)

本 repo 採用 [Ponytail](https://github.com/DietrichGebert/ponytail) lazy senior dev 模式：YAGNI、刪減優於新增、能一行就不寫十行。Cursor 規則見 [`.cursor/rules/ponytail.mdc`](.cursor/rules/ponytail.mdc)（`alwaysApply: true`）。刻意簡化處以 `ponytail:` 註解標記升級路徑；信任邊界驗證、防資料遺失、安全與無障礙不省略。CJK 字元程式識別子見 [`CONTEXT.md`](CONTEXT.md) § **程式識別子（canto 字）**（`chars`／`canto`；唔用 `hanzi`）。

### Spec Kit Rules
如需額外的技術上下文、專案結構、shell指令等信息，請讀取 `.specify/` 目錄中的當前計劃（Spec Kit 專用）。

### Issue tracker

Issues live in GitHub Issues for `bill-iu/Canto-0243` (use the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles use the default label strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` and `docs/adr/` at the repo root when present. See `docs/agents/domain.md`.

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->

### Shell search

搜尋用 `rg`（ripgrep，已全域安裝）代替 `grep`；`rg` 預設尊重 `.gitignore`。
