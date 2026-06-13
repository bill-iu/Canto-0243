# Contributing to Canto-0243

Thank you for helping improve **Canto-0243** (0243 Cantonese rhyme dictionary for lyricists).

## Before you start

1. Read [CONTEXT.md](CONTEXT.md) for domain vocabulary (查詢語法、詞庫、排序).
2. Read [LICENSE](LICENSE) (Canto-0243 License). **This is not an OSI-approved open-source license** (NonCommercial + additional terms).
3. Read [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) if your change touches data or fetch scripts.

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

## Pull requests

- Keep changes focused; match existing style.
- Add or update tests for behaviour changes.
- Do not commit secrets, `.env.local`, `*.db`, or `data/raw/clean/` lexicon dumps.
- Do not commit `skills-lock.json` churn unless intentionally updating agent skills.

## Issues

Use GitHub Issues for bugs, feature ideas, and questions. For security-sensitive reports, describe the impact in the issue (v1 has no separate SECURITY.md yet).

## Naming

Public-facing product name: **Canto-0243**. Forks must retain the name per LICENSE §3.
