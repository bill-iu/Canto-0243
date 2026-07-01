# Third-party notices

Canto-0243 **program code** is under [Canto-0243 License](LICENSE). **Data files**
listed below are fetched, bundled, or maintainer-built separately; each retains its
upstream license.

## Bundled in git (tier 1)

| Dataset | Path | Upstream | License / terms |
|---------|------|----------|-----------------|
| Rime single-char | `data/rime/char.csv` | [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Essay frequency | `data/essay/essay-cantonese.txt` | [rime/rime-cantonese](https://github.com/rime/rime-cantonese) | [CC BY 4.0](https://github.com/rime/rime-cantonese/blob/main/LICENSE-CC-BY) |
| Curated compound antonyms | `data/syn_ant/compound_antonyms.txt` | Canto-0243 project | Same as program (Canto-0243 License) |
| Curated common words | `data/lexicon/curated_common.txt` | Canto-0243 project | Same as program (Canto-0243 License) |

## Fetched by bootstrap (tier 2)

Produced by `python scripts/bootstrap_data.py` (not committed by default).

| Dataset | Path (after fetch) | Upstream | License / terms |
|---------|-------------------|----------|-----------------|
| Cilin synonym groups | `data/cilin/new_cilin.txt` | [yaleimeng/Final_word_Similarity](https://github.com/yaleimeng/Final_word_Similarity) (via [liao961120/cilin](https://github.com/liao961120/cilin) API) | **MIT** |
| Guotong thesaurus | `data/thesaurus/dict_*.txt` | [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary) | [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE) |
| ChineseAntiword antisem | `data/antonym/antisem.txt` | [liuhuanyong/ChineseAntiword](https://github.com/liuhuanyong/ChineseAntiword) | **No explicit license** — fetch for local use; attribution required; verify before redistribution |
| words.hk wordlist | `data/lexicon/raw/words_hk/` (manifest) | [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/) | **Public domain** (credit [words.hk](https://words.hk/) appreciated) |

```bash
pip install -r requirements-dev.txt   # optional: cilin export
python scripts/bootstrap_data.py
```

## Maintainer-built lexicon (tier 3)

**詞條庫** `lyrics.db` is **not** shipped in git. Maintainers run a full rebuild from
per-source manifests (`data/lexicon/sources.yaml`) via `python -m ingest build-db`.
Upstream lexicons below supply raw inputs; merged output is under [Canto-0243 License](LICENSE).
Verify upstream terms before enabling additional sources.

| Upstream | Link | License / terms |
|----------|------|-----------------|
| Rime single-char | [rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| words.hk 粵典詞表 | [wordslist](https://words.hk/faiman/analysis/wordslist/) | **Public domain** (credit [words.hk](https://words.hk/) appreciated) |
| 開放詞典 · 粵語詞典 | [下載](https://kaifangcidian.com/xiazai/) | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| Maintainer curated | `data/lexicon/curated_lexicon.json` | Same as program (Canto-0243 License) |

## Optional syn/ant sources

Default ingest uses `current_static` in `data/syn_ant/sources.yaml`. Additional
sources (e.g. Chinese Open Wordnet / COW) are **disabled by default** and require
maintainer-local raw files; see manifest for license and `local_only` flags.
