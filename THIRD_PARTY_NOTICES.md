# Third-party notices

Canto-0243 **program code** is under [Canto-0243 License](LICENSE). **Data files**
listed below are fetched or bundled separately; each retains its upstream license.

| Dataset | Path (after fetch / bundled) | Upstream | License / terms |
|---------|------------------------------|----------|-----------------|
| Rime single-char | `data/rime/char.csv` | [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) |
| Essay frequency | `data/essay/essay-cantonese.txt` | [rime/rime-cantonese](https://github.com/rime/rime-cantonese) | [CC BY 4.0](https://github.com/rime/rime-cantonese/blob/main/LICENSE-CC-BY) |
| words.hk wordlist | `data/raw/words.hk/` (manifest) | [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/) | **Public domain** (credit [words.hk](https://words.hk/) appreciated) |
| Cilin synonym groups | `data/cilin/new_cilin.txt` | [yaleimeng/Final_word_Similarity](https://github.com/yaleimeng/Final_word_Similarity) (via [liao961120/cilin](https://github.com/liao961120/cilin) API) | **MIT** |
| Guotong thesaurus | `data/thesaurus/dict_*.txt` | [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary) | [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE) |
| ChineseAntiword antisem | `data/antonym/antisem.txt` | [liuhuanyong/ChineseAntiword](https://github.com/liuhuanyong/ChineseAntiword) | **No explicit license** — fetch for local use; attribution required; verify before redistribution |
| Curated compound antonyms | `data/syn_ant/compound_antonyms.txt` | Canto-0243 project | Same as program (Canto-0243 License) |
| Curated common words | `data/lexicon/curated_common.txt` | Canto-0243 project | Same as program (Canto-0243 License) |

## Fetching data

```bash
pip install -r requirements-dev.txt   # optional: cilin export
python scripts/bootstrap_data.py
```

Bundled in git (no fetch required): essay corpus, curated lists, test fixtures.

Not bundled: rime `char.csv`, cilin export, guotong dicts, antisem — produced by `bootstrap_data.py`.

## words.hk clean JSON

`data/raw/clean/*.json` (0243-coded lexicon for import) is maintainer-built from
words.hk and other sources; see README § Maintainer.
