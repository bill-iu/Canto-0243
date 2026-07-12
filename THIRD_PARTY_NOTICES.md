# Third-party notices

Canto-0243 **program code** is under [Canto-0243 License](LICENSE). **Data files**
listed below are fetched, bundled, or maintainer-built separately; each retains its
upstream license.

## Bundled in git (tier 1)

| Dataset | Path | Upstream | License / terms |
|---------|------|----------|-----------------|
| Rime single-char | `data/rime/char.csv` | [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Rime categorized lexicon | `data/lexicon/raw/rime-cantonese-upstream/*.csv`（不含 `proper_nouns.csv`） | [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Essay frequency | `data/essay/essay-cantonese.txt` | [rime/rime-cantonese](https://github.com/rime/rime-cantonese) | [CC BY 4.0](https://github.com/rime/rime-cantonese/blob/main/LICENSE-CC-BY) |
| Curated compound antonyms | `data/syn_ant/compound_antonyms.txt` | Canto-0243 project | Same as program (Canto-0243 License) |
| Project antonym pairs (AI-assisted) | `data/syn_ant/project_antonyms.tsv` (+ `project_antonyms.meta.json`) | Canto-0243 project; drafted with generative AI assistance (e.g. Grok via Cursor), maintainer-reviewed before release | Same as program (Canto-0243 License). Output attributed per xAI Brand Guidelines / applicable Cursor terms. **Not** a redistribution of guotong or other third-party antonym lexicons. |
| Curated common words | `data/lexicon/curated_common.txt` | Canto-0243 project | Same as program (Canto-0243 License) |

## Fetched by bootstrap (tier 2)

Produced by `python scripts/bootstrap_data.py` (not committed by default).

| Dataset | Path (after fetch) | Upstream | License / terms |
|---------|-------------------|----------|-----------------|
| Cilin synonym groups | `data/cilin/new_cilin.txt` | [yaleimeng/Final_word_Similarity](https://github.com/yaleimeng/Final_word_Similarity) (via [liao961120/cilin](https://github.com/liao961120/cilin) API) | **MIT** |
| Guotong thesaurus | `data/thesaurus/dict_*.txt` | [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary) | [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE) — includes near-synonym and antonym pairs (`dict_antonym.txt`) |
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
| Rime categorized words | [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Rime phrase supplements（legacy、非預設） | [rime/rime-cantonese `jyut6ping3.phrase`](https://github.com/rime/rime-cantonese) | [CC BY 4.0](https://github.com/rime/rime-cantonese/blob/main/LICENSE-CC-BY) |
| HSK 3.0 word list | [elkmovie/hsk30](https://github.com/elkmovie/hsk30) | [MIT](https://github.com/elkmovie/hsk30/blob/main/LICENSE) |
| words.hk 粵典詞表 | [wordslist](https://words.hk/faiman/analysis/wordslist/) | **Public domain** (credit [words.hk](https://words.hk/) appreciated) |
| 開放詞典 · 粵語詞典 | [下載](https://kaifangcidian.com/xiazai/) | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| Maintainer curated | `data/lexicon/curated_lexicon.json` | Same as program (Canto-0243 License) |

## Project-owned antonym pairs (AI-assisted)

Direct antonym edges may also come from the project-owned list above
(`source=project_ant` in `word_relations`). Seeds are lexicon literals
(priority: has-synonym / no-direct-antonym, essay Top-K); upstream antonym
files are **not** used as few-shot expansion sources. Overlap with third-party
antonym lists may be measured for quality monitoring only. Guotong antonyms
and project antonyms **coexist**; when the same pair appears in both, build
merge prefers `project_ant`.

## Optional syn/ant sources

Default ingest uses `current_static` in `data/syn_ant/sources.yaml` plus the
project antonym list when present. Additional sources (e.g. Chinese Open
Wordnet / COW) are **disabled by default** and require maintainer-local raw
files; see manifest for license and `local_only` flags.
