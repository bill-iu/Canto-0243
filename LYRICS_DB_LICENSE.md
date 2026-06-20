# Lyrics database license (`lyrics.db` / `words-lexicon.json`)

**Canto-0243 program code** is under [Canto-0243 License](LICENSE) (non-commercial, no repackage, etc.).
**This file applies only to the word-level lexicon data** shipped as:

- `lyrics.db` — SQLite word database  
- `words-lexicon.json` — export of the same readings for the matching release tag  

## Summary

The lexicon is a **mixed compilation**. The **overall distribution terms** for these data files are **Creative Commons Attribution-ShareAlike 3.0** ([CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)), because the compiled database includes **ShareAlike** material (notably **CC-Canto**). You may share and adapt the **database files** under CC BY-SA 3.0 if you attribute sources and pass the same license on derivatives.

**Program behavior, UI, and curated project lists** bundled in the portable zip remain under **Canto-0243 License**, not this file.

## Major upstream sources (non-exhaustive)

See also [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) § maintainer-built multi-char lexicon.

| Source | Link | Role in `lyrics.db` | Upstream license |
|--------|------|---------------------|------------------|
| CC-Canto | [cantonese.org/download](https://cantonese.org/download.html) | Multi-char readings (major SA component) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| words.hk 粵典詞表 | [wordslist](https://words.hk/faiman/analysis/wordslist/) | Multi-char readings | Public domain (credit appreciated) |
| 開放詞典 · 粵語詞典 | [kaifangcidian.com](https://kaifangcidian.com/xiazai/) | Fill gaps | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| Rime / essay / maintainer ingest | See THIRD_PARTY_NOTICES | Single-char & relations pipeline | Per upstream (mostly CC BY 4.0 / project) |
| Maintainer corrections | `data/lexicon/lexicon_corrections.tsv` | Curated fixes | Canto-0243 project curation |

## Your obligations when redistributing `lyrics.db` or `words-lexicon.json`

1. **Attribute** CC-Canto, words.hk, and other sources you used (see THIRD_PARTY_NOTICES).  
2. **ShareAlike**: if you publish a modified lexicon derived from this compilation, license your derivative under **CC BY-SA 3.0** (or compatible SA terms).  
3. **Do not** assume the **application** is CC BY-SA — only these **data files**.

## Transition note

Removing CC-Canto from the default merge pipeline is tracked separately (GitHub issue #9). Until then, **CC BY-SA 3.0 mixed** remains the correct label for release `lyrics.db` assets.
