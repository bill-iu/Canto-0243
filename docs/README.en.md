# Canto-0243

<p align="center">
  <a href="../README.md">繁體中文</a> · <a href="README.zh-Hans.md">简体中文</a> · <b>English</b>
</p>

Writing Cantonese lyrics often means not knowing which characters are available, or needing to swap characters quickly among **same-tone, rhyming, and near-synonym** options while matching 0243 codes and Jyutping. The traditional approach—flipping through dictionaries, rhyme books, and thesaurus tables, manually trying whether another character fits—is slow and easy to miss good options. [0243.hk](https://0243.hk) is one of the best Cantonese lyric lookup sites in recent years, but it can still hit 502 Bad Gateway, spin forever while loading, or lack a feature you need—all of which slow you down.

**Canto-0243** (**ONE·搵·韻**) is an offline Cantonese lyric lookup workbench I built with several AI agents (Cursor, Codex, Grok Build, GitHub Copilot). It lists matching **word entries** in seconds using **394052／02493 tone codes**, **Jyutping**, **rhyme／initial rules**, and **synonym／antonym relations**. **0243 search** has three tiers: **0243 mode** (loose), **02493 mode** (strict, `4↔5` only), and **394052 mode** (6 tones—strict tone-3 digit `4` vs tone-5 digit `5`). For example: type `23就` for same-code syllables with a rhyme match on 「就」; `香港=` for whole-word rhyme with 「香港」; `~開心` or switch to **near／antonym mode** for synonyms and antonyms; `~~`／`!!` for common two-character near-synonym／antonym compounds. Unzip and run—lexicon and relation data stay on your machine, no internet required.

**License**: Full bundle (program, `lyrics.db`, `words-lexicon.json`) under [Canto-0243 License](../LICENSE) (CC BY-NC-SA 4.0 + additional terms; **open source**). Upstream data: [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).  
**Stack**: FastAPI · SQLAlchemy · SQLite (offline single-machine) · PWA frontend (Service Worker / Web App Manifest; Vite + vanilla HTML/JS, with OPFS / wa-sqlite for offline database access)  
**Domain glossary**: [`CONTEXT.md`](../CONTEXT.md) · Contributing: [`docs/CONTRIBUTING.md`](CONTRIBUTING.md)

---

## Latest release

<!-- version:en -->
Current version: **v1.0.7**
<!-- /version:en -->

<!-- words-count:en -->
Current word entries: **445,022** (`lyrics.db` · `words` table)
<!-- /words-count:en -->

**Get started now (two equally important options)**

**Canto-0243 mobile** (open in your browser, no install, add to home screen, fully offline)  
👉 https://bill-iu.github.io/Canto-0243/

**Offline portable** (Windows / macOS, zero-install, unzip and run)  
Download latest: [canto-0243-portable.zip](https://github.com/bill-iu/Canto-0243/releases) / macOS tar  
Full releases and lexicon files: [GitHub Releases](https://github.com/bill-iu/Canto-0243/releases)

Feedback welcome on [GitHub Issues](https://github.com/bill-iu/Canto-0243/issues).

---

## Features

* **0243 search (three tiers)**: **0243 mode** `mode=m1` (full loose variants) · **02493 mode** `mode=m2` (`4↔5` loose only) · **394052 mode** `mode=m3` (strict 6-tone codes; lexicon stores 394052 with tone 3=`4`, tone 5=`5`).
* **Rich query syntax**: plain Chinese · plain digits · **Jyutping queries** · **plus anchors** (`23+好=`) · **rhyme／initial anchors** (`就=`) · **serial rhyme／initial anchors** · **four-character partial rhyme／initial anchors** (`窮?潦倒=`) · **prefix wildcard equals** · whole-word equals／code sandwich.
* **Near／antonym**: **near／antonym mode** `mode=syn` full-column UI (no Jyutping); or in **0243 search mode** use `~word`／`!word`, antonym compounds `!!`, near-synonym compounds `~~`.

---

## Quick start

**Pick one way to begin**:

- **Canto-0243 mobile**: Open https://bill-iu.github.io/Canto-0243/ directly; add to home screen for fully offline use. The header has a **Search guide**.

- **Offline portable**: Download and unzip from [Releases](https://github.com/bill-iu/Canto-0243/releases). Windows: double-click `Canto-0243.exe` (or `START.bat`); macOS: double-click `Canto-0243.command`.

Developers who clone need `lyrics.db` (see [`docs/CONTRIBUTING.md`](CONTRIBUTING.md)).

---

## Common syntax examples

| Example | Description |
|---------|-------------|
| `就` | All readings for this character |
| `你好` | Lookup this word |
| `23` | Same-code matches |
| `就=` | Rhymes with 「就」 |
| `23就` | Code + tail rhymes with anchor |
| `香??` | Mask query |
| `香港=` | Whole-word rhyme |
| `?+就=` | Last slot rhymes with 「就」 |
| `~開心` | Near-synonyms |
| `!!` / `~~` | Antonym／near-synonym compounds |

For full examples and all syntax, tap **Search guide** in the app header.

---

## Maintainer notes

Lexicon rebuild, releases, and more: [`docs/CONTRIBUTING.md`](CONTRIBUTING.md) and [`docs/release.md`](release.md).

---

## About the developer

**Bill IU (姚程馭)** — actor, Cantonese musical theatre lyricist, and extremely amateur programmer.

---

## Canto-0243 license & use

You may use this tool for anything you want—including Cantonese lyric writing, rhyme lookup, character substitution, and as part of **commercial creative work** (songs, scripts, published lyrics)—subject to the restrictions below:

* **You may not** repackage, resell, or ship it as a competing standalone product.
* **You may not** offer this tool as a **paid API**, subscription, or metered query／inference service (free self-hosting or free public access is different, but attribution terms still apply).
* Any public fork, improvement, or derivative must **use the same license** (or substantially equivalent terms) and keep the **Canto-0243** name in a reasonable, visible place. If you run a public site, web app, or API (including free), show e.g. “Powered by Canto-0243” linking to the official repo.
* If you run **commercial software** or a **paid inference service** and want to embed this tool, contact the copyright holder or open an Issue on the official repo for written permission.

Apart from the above, this license is in practice [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/) plus additional restrictions. Full legal text: [`LICENSE`](../LICENSE).

Please keep the name **Canto-0243** in any future fork or distribution!

---

## Acknowledgements & third-party licenses

### Project thanks

Early in development—with almost no programming background—the author benefited from **[ivorhoulker](https://github.com/ivorhoulker)** as advisor: design and implementation guidance plus many valuable suggestions. Without that help, **Canto-0243** would not exist.

Thanks also to **Professor Wong Chi-wah**, inventor of **0243 theory**, for the theoretical foundation of digitized Cantonese lyric writing; and to **Daniel Tam**, developer of [0243.hk](https://0243.hk), whose site solved many lyricists’ problems and inspired this tool.

### Data & corpus thanks

Canto-0243 integrates several open dictionaries, corpora, and near／antonym resources. We thank the teams and projects below (read each upstream license before redistribution; summary in [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)):

* **Rime Cantonese** (single-char `char.csv`, essay frequency): [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) and [rime/rime-cantonese](https://github.com/rime/rime-cantonese), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Give them a star!
* **Cilin synonyms**: via [yaleimeng/Final_word_Similarity](https://github.com/yaleimeng/Final_word_Similarity)／[liao961120/cilin](https://github.com/liao961120/cilin), **MIT**.
* **Guotong near／antonym dictionary**: [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary) (`dict_synonym.txt`, `dict_antonym.txt`), [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE)—primary **antonym** source for this project.
* **words.hk Cantonese word list**: [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/), **non-commercial open license** (see [words.hk /hoifong](https://words.hk/base/hoifong/)).
* **Multi-character reading upstream** (maintainer-built `lyrics.db`): [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/) (non-commercial open license), [Kaifang Dictionary · Cantonese](https://kaifangcidian.com/xiazai/) ([CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)), Rime Cantonese supplement sources ([CC BY 4.0](https://github.com/rime/rime-cantonese/blob/main/LICENSE-CC-BY)), [HSK 3.0 word list](https://github.com/elkmovie/hsk30) (MIT), and maintainer curated sources.

Building or redistributing lexicons from these sources requires complying with each license; some impose **non-commercial** or **attribution** terms. Optional sources (e.g. COW) are off by default—see `data/syn_ant/sources.yaml`.

---

## Related documents

| Document | Contents |
|----------|----------|
| [`README.md`](../README.md) | Traditional Chinese (GitHub homepage) |
| [`docs/README.zh-Hans.md`](README.zh-Hans.md) | Simplified Chinese documentation (written Chinese) |
| [`docs/README.en.md`](README.en.md) | English documentation (this file) |
| [`LICENSE`](../LICENSE) | Canto-0243 License (program and word-entry bundle) |
| [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) | Third-party data licenses |
| [`docs/CONTRIBUTING.md`](CONTRIBUTING.md) | Contributing & repo-root conventions |
| [`CONTEXT.md`](../CONTEXT.md) | Domain glossary |
| [`WORKLOG.md`](../WORKLOG.md) | Change log |
| [`AGENTS.md`](../AGENTS.md) | Agent collaboration notes |

---

**Last updated**: 2026-07-11 (v1.0.7: pingze search mode, unified search-mode profiles, mobile/portable alignment)
