## Agent skills

Agent 與維護者流程見 `docs/agents/`；貢獻與 PR 見 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)。

### Coding style (Ponytail)

本 repo 採用 [Ponytail](https://github.com/DietrichGebert/ponytail) lazy senior dev 模式：YAGNI、刪減優於新增、能一行就不寫十行。Cursor 規則見 [`.cursor/rules/ponytail.mdc`](.cursor/rules/ponytail.mdc)（`alwaysApply: true`）。刻意簡化處以 `ponytail:` 註解標記升級路徑；信任邊界驗證、防資料遺失、安全與無障礙不省略。

### Issue tracker

Issues live in GitHub Issues for `ICE-U-code/Canto-0243` (use the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Five canonical triage roles use the default label strings (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` and `docs/adr/` at the repo root when present. See `docs/agents/domain.md`.
