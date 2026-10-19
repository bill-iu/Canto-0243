# Canto-0243

<p align="center">
  <a href="../README.md">繁體中文</a> · <a href="README.zh-Hans.md">简体中文</a> · <b>English</b>
</p>

Writing Cantonese lyrics often means not knowing which characters are available, or needing to swap characters quickly among **same-tone, rhyming, and near-synonym** options while matching 0243 codes and Jyutping. The traditional approach—flipping through dictionaries, rhyme books, and thesaurus tables, manually trying whether another character fits—is slow and easy to miss good options. [0243.hk](https://0243.hk) is one of the best Cantonese lyric lookup sites in recent years, but it can still hit 502 Bad Gateway, spin forever while loading, or lack a feature you need—all of which slow you down.

**Canto-0243** (**ONE·搵·韻**) is an offline Cantonese lyric lookup workbench I built with several AI agents (Cursor, Codex, Grok Build, GitHub Copilot). It lists matching **word entries** in seconds using **394052／02493 tone codes**, **Jyutping**, **rhyme／initial rules**, and **synonym／antonym relations**. **0243 search** has three tiers: **0243 mode** (loose), **02493 mode** (strict, `4↔5` only), and **394052 mode** (6 tones—strict tone-3 digit `4` vs tone-5 digit `5`). For example: type `23就` for same-code syllables with a rhyme match on 「就」; `香港=` for whole-word rhyme with 「香港」; `ZP` for a level/oblique tone sequence (automatically switches to 394052 mode); `~開心` or switch to **near／antonym mode** for synonyms and antonyms; `~~`／`!!` for common two-character near-synonym／antonym compounds. After the initial download and setup, lexicon and relation data stay on your machine for offline use.

**License**: Full bundle (program, `lyrics.db`, `words-lexicon.json`) under [Canto-0243 License](../LICENSE) (CC BY-NC-SA 4.0 + additional terms; **open source**). Upstream data: [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).  
**Stack**: FastAPI · SQLAlchemy · SQLite (offline single-machine) · React + Vite (shared PWA and Desktop interface; Service Worker / Web App Manifest; OPFS / wa-sqlite for offline PWA database access)

**Domain glossary**: [`CONTEXT.md`](../CONTEXT.md) · Contributing: [`docs/CONTRIBUTING.md`](CONTRIBUTING.md)

---

## Latest release

<!-- version:en -->
Current version: **v1.1.2**
<!-- /version:en -->

<!-- words-count:en -->
Current word entries: **181,735** (`lyrics.db` · `words` table)
<!-- /words-count:en -->

**v1.1.2 lexicon update**

* Three batches add **536 expressions** (76 + 261 + 199), covering general Chinese, lyric phrases, and colloquial Cantonese, including 「迎風起」「花開花落」「只差一點」「講清楚」. Of the latest 199 additions, 168 have evidence in multiple songs and 31 have Essay colloquial evidence; see the [third-batch review](lexicon-supplement-b03.md).
* Remove **27 confirmed incorrect readings** (11 in this batch), restore 7 readings or codes for existing expressions, and correct 9 codes in the earlier supplement. Supported reading variants are retained.
* 「善良」 is `sin6 loeng4` (`20`) and no longer appears under `40`; 「圖書館」 is `tou4 syu1 gun2` (`039`) and no longer appears under `439`. 「迎風起」 has code `039`; search `033起` in **0243 loose mode** to find it.

The PWA, Windows, and macOS Desktop use the same lexicon for this release. See the [full release notes](release-notes/v1.1.2.md) and [supplementary lexicon and reading review](lexicon-supplement.md) (Traditional Chinese).

**Get started now (two equally important options)**

**Canto-0243 mobile** (open in your browser, no install, add to home screen; works offline after the initial download)

👉 https://bill-iu.github.io/Canto-0243/

**Desktop offline edition** (Windows / macOS, no installer; the first launch downloads CPython 3.11, then works offline)

Download latest: [Windows Desktop zip](https://github.com/bill-iu/Canto-0243/releases/latest/download/canto-0243-desktop.zip) / [macOS Intel tar](https://github.com/bill-iu/Canto-0243/releases/latest/download/canto-0243-desktop-macos-x86_64.tar.gz) (no arm64 bundle in this release)

Full releases and lexicon files: [GitHub Releases](https://github.com/bill-iu/Canto-0243/releases)

Feedback welcome on [GitHub Issues](https://github.com/bill-iu/Canto-0243/issues).

---

## Features

* **0243 search (three tiers)**: **0243 mode** `mode=m1` (full loose variants) · **02493 mode** `mode=m2` (`4↔5` loose only) · **394052 mode** `mode=m3` (strict 6-tone codes; lexicon stores 394052 with tone 3=`4`, tone 5=`5`).
* **Rich query syntax**: plain Chinese · plain digits · **Jyutping queries** · **level/oblique tone sequences** (`PZ` / `ZP`, automatically switches to m3) · **plus anchors** (`23+好=`) · **rhyme／initial anchors** (`就=`) · **serial rhyme／initial anchors** · **four-character partial rhyme／initial anchors** (`窮?潦倒=`) · **prefix wildcard equals** · whole-word equals／code sandwich.
* **Near／antonym**: **near／antonym mode** `mode=syn` full-column UI (no Jyutping); or in any **0243 search tier** use `~word`／`!word`, antonym compounds `!!`, near-synonym compounds `~~`. Returning from near／antonym mode restores your previous search tier.

---

## Quick start

**Pick one way to begin**:

- **Canto-0243 mobile**: Open https://bill-iu.github.io/Canto-0243/ directly; add to home screen for fully offline use. The header has a **Search guide**.

- **Desktop offline**: Download and extract from [Releases](https://github.com/bill-iu/Canto-0243/releases). Windows: double-click `Canto-0243.exe`; macOS Intel: double-click **`Canto-0243.app`**. If Gatekeeper blocks it, right-click the `.app` and choose Open, or select Open Anyway in Privacy & Security. The first launch needs internet.

**Update to this release**: Reopen the PWA and complete its lexicon update. For Desktop, download the latest complete bundle and open the new app.

Developers who clone need `lyrics.db` (see [`docs/CONTRIBUTING.md`](CONTRIBUTING.md)).

---

## Common syntax examples

| Example | Description |
|---------|-------------|
| `就` | All readings for this character |
| `你好` | Lookup this word |
| `23` | Same-code matches |
| `45` | Distinguish tones 3 and 5 in 394052 mode |
| `ZP` | Level/oblique tone sequence; automatically switches to 394052 mode |
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

The Desktop interface is served locally at **`/app/`** from `client/dist-portable` (`cd client && npm run build:portable`). Shared UI source lives in **`shared/`**. Build Windows bundles with `scripts/build-desktop.ps1` (Rust/cargo required).

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

Early in development—with almost no programming background—the author benefited from [ivorhoulker](https://github.com/ivorhoulker) as advisor, with design and implementation guidance plus many valuable suggestions.

Thanks also to **Professor Wong Chi-wah**, inventor of **0243 theory** (whose support we are honoured to have), for the theoretical foundation of digitized Cantonese lyric writing; and to **Daniel Tam**, developer of [0243.hk](https://0243.hk), whose site solved many lyricists’ problems and inspired this tool.

### Data & corpus thanks

This app exists thanks to outstanding work by linguists, open-source maintainers, and community contributors. We are proud to integrate data from the following (aligned with the in-app About page; read each upstream license before redistribution):

* [words.hk (粵典)](https://words.hk/): **non-commercial open license** (see [words.hk /hoifong](https://words.hk/base/hoifong/)).
* [Rime Cantonese supplement sources](https://github.com/CanCLID/rime-cantonese-upstream): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
* [Cantonese.md xiehouyu literals](https://github.com/daimaruhk/Cantonese.md): [CC0 1.0](https://github.com/daimaruhk/Cantonese.md/blob/main/LICENSE-DATA) (term／answer + Jyutping only; no full glosses).
* [Unicode Unihan 17.0.0](https://www.unicode.org/Public/17.0.0/ucd/Unihan.zip): [Unicode License v3](https://www.unicode.org/license.txt), using `kCantonese`／`kCheungBauer` to supplement readings for already-admitted literals.
* [HSK 3.0 word list](https://github.com/elkmovie/hsk30): [MIT](https://opensource.org/licenses/MIT).
* [Kaifang Dictionary · Cantonese](https://kaifangcidian.com/xiazai/): [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/).
* [Cilin synonyms](https://github.com/yaleimeng/Final_word_Similarity): [MIT](https://opensource.org/licenses/MIT).
* [Guotong near／antonym dictionary](https://github.com/guotong1988/chinese_dictionary): [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE).
* [Project supplementary lexicon](lexicon-supplement.md): maintainer-reviewed general Chinese, lyric phrases, colloquial Cantonese, and reading corrections; [Canto-0243 License](../LICENSE).
* [Project near-antonyms](../LICENSE): maintainer-reviewed synonym／antonym pairs (LLM-assisted drafting); [Canto-0243 License](../LICENSE).

Full third-party license list: [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md).

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

---

**Last updated**: 2026-10-19 (v1.1.2 supplementary lexicon, reading corrections, and PWA/Desktop update instructions)
