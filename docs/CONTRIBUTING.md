# Contributing to Canto-0243

Thank you for helping improve **Canto-0243** (0243 Cantonese rhyme dictionary for lyricists).

## Before you start

1. Read [CONTEXT.md](../CONTEXT.md) for domain vocabulary (查詢語法、詞庫、排序).
2. Read [LICENSE](../LICENSE) (Canto-0243 License). **This is not an OSI-approved open-source license** (NonCommercial + additional terms).
3. Read [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) if your change touches data or fetch scripts.

## License on contributions

By submitting a pull request or otherwise contributing to this repository, you agree that:

- Your contribution is licensed under the **Canto-0243 License**, and
- You grant **IU Ching Ue Bill** the additional rights described in LICENSE §6 (including the right to use your contribution commercially).

If you cannot agree to these terms, please do not contribute.

## Development setup

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python scripts/bootstrap_data.py
python -m unittest discover -s tests -q
```

`__pycache__/` 與 `*.pyc` 為 Python 自動產生的 bytecode 快取，已在 `.gitignore`；**可隨時刪除**，下次 `import` 會重建。請勿提交至 git。

## Pull requests

- Keep changes focused; match existing style.
- Add or update tests for behaviour changes.
- Do not commit secrets, `.env.local`, `*.db`, maintainer-built **詞級標音** import files, or other gitignored data artifacts (see README § 資料來源).
- Do not commit `skills-lock.json` churn unless intentionally updating agent skills.

## Issues

Use GitHub Issues for bugs, feature ideas, and questions. For security-sensitive reports, describe the impact in the issue (v1 has no separate SECURITY.md yet).

## Naming

Public-facing product name: **Canto-0243**. Forks must retain the name per LICENSE §3.

## 源碼根目錄（維護者）

領域定義見 [CONTEXT.md](../CONTEXT.md) § 源碼根目錄。

**應留在根目錄的追蹤檔**：產品入口（`main.py`、`start.sh`、`requirements*.txt`、`alembic.ini`）、`README.md`（繁體中文，GitHub 首頁）、`LICENSE`、`THIRD_PARTY_NOTICES.md`、`CONTEXT.md`、`WORKLOG.md`、`AGENTS.md`（stub）、`skills-lock.json`、`.env.example`、`.gitignore`。英文／简体中文 README 見 `docs/README.en.md`、`docs/README.zh-Hans.md`。

**允許的本機檔（通常 gitignore）**：

| 檔案 | 用途 |
|------|------|
| `lyrics.db` | 開發／打包用詞條庫（Release 下載或 maintainer 自建） |
| `.env.local` · `.env` · `.env.prod` | 本機環境變數 |

**不得堆在根目錄**：

- 任何 `*.log`、`debug-*.log`、`ingest-*.log`
- 建置產物（用 `dist/`；Release 後可整目錄刪除，見 [release.md](release.md)）
- Cursor 暫存（`agent-tools/`、`mcps/`、`commit-msg.txt` 等；已 gitignore）
- 未列入允許清單的資料 dump

日誌請寫入 `logs/`（若腳本支援）或系統暫存區，並定期清理。Portable 交付腳本見 `portable/START.*`；clone 開發用 `./start.sh`（與 Portable 職責分開）。
