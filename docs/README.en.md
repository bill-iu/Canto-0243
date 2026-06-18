# Canto-0243

<p align="center">
  <a href="../README.md">繁體中文</a> · <a href="README.zh-Hans.md">简体中文</a> · <b>English</b>
</p>

Writing Cantonese lyrics often means hunting for the right character—same tone, rhyming fit, or a near synonym—while matching 0243 codes and Jyutping. Flipping through dictionaries, rhyme books, and thesaurus tables by hand is slow and easy to miss good options. [0243.hk](https://0243.hk) is an excellent online Cantonese rhyme finder, but outages, endless loading, or missing features can still stall your workflow.

**Canto-0243** (**ONE·搵·韻**) is an offline Cantonese lyric lookup workbench built with AI agents. It lists replaceable **word entries** in seconds using **0243／02493 tone codes**, **Jyutping**, **rhyme／initial rules**, and **synonym／antonym relations**. Type `23就` for same-code syllables with a rhyme match on 「就」; `香港=` for whole-word rhyme with 「香港」; `~開心` or **near／antonym mode** for synonyms and antonyms; `~~`／`!!` for common two-character near-synonym／antonym compounds. Unzip and run—lexicon and relation data stay on your machine.

**License**: [Canto-0243 License](../LICENSE) (CC BY-NC-SA 4.0 + additional terms; **not OSI-open source**). Third-party data: [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).  
**Stack**: FastAPI · SQLAlchemy · SQLite (offline single-machine) · vanilla HTML/JS frontend  
**Domain glossary**: [`CONTEXT.md`](../CONTEXT.md) · Contributing: [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## Latest release

<!-- words-count:en -->
Current word entries: **193,289** (`lyrics.db` · `words` table)
<!-- /words-count:en -->

Official offline data bundle: **[Canto-0243 v1.6.4](https://github.com/bill-iu/Canto-0243/releases/tag/v1.6.4)** (`canto-0243-portable.zip`, macOS `tar.gz`, `lyrics.db`, `words-lexicon.json`). Feedback welcome on [GitHub Issues](https://github.com/ICE-U-code/Canto-0243/issues).

---

## Features

* **0243／02493 code search**: **0243 mode** `mode=m1` (0243 equivalence variants) and **02493 mode** `mode=m2` (02493 codes; distinguishes entering-tone variants).
* **Rich query syntax**: plain Chinese · plain digits · **Jyutping queries** · **Jyutping anchors** · code+character (`23就`) · wildcards · **serial rhyme／initial anchors** (`04困=49倒=`, `23就=`) · **prefix wildcard equals** (`?香港=`) · equals rhyme／initial (`香港=`, `2=我3`) · rhyme／initial anchors (`就=`, `?*就=`, `?港=?`).
* **Near／antonym**: **near／antonym mode** `mode=syn` full-column UI (no Jyutping); or in **0243 search mode** use `~word`／`!word`, antonym compounds `!!`, near-synonym compounds `~~`.
* **Lexicon & admission**: lexicon port raw lookup + **admission decisions**; multi-character lexicon readings or syllable-concatenated readings.
* **Relation data**: **static thesaurus port** (Cilin／Guotong near-synonyms／antisem); runtime and ingest share the same rules.
* **Result ranking**: within each match tier **plain Chinese** → **essay frequency** → **curated** → **pron_rank** → surface form (see [`CONTEXT.md`](../CONTEXT.md) § search result ranking).

---

## Quick start

### 1. Download & install (end users)

For the full offline experience, use the official portable package—**no** git clone or manual DB setup.

1. Download **`canto-0243-portable.zip`** from [GitHub Releases](https://github.com/ICE-U-code/Canto-0243/releases) (pin to [`Canto-0243 v1.6.4`](https://github.com/bill-iu/Canto-0243/releases/tag/v1.6.4)).
2. Extract the entire folder (e.g. `canto-0243-portable`).
3. Launch by platform:
   * **Windows**: extract and double-click **`START.bat`** (no Python install).
   * **macOS**: download `canto-0243-portable-macos-arm64.tar.gz` or `canto-0243-portable-macos-x86_64.tar.gz` for your chip, then double-click **`Canto-0243.app`**. If blocked: **right-click → Open** on **`.app`** or **`Open Canto-0243.command`** (once each). On **Sequoia 15**, if you only see a malware dialog (Done / Move to Trash): tap **Done** → **System Settings → Privacy & Security** → scroll down → **Open Anyway** (Canto-0243) → double-click again.
   * **Linux**: `chmod +x START.sh && ./START.sh` (system Python 3.10+ required).

**Requirements**: **Zero-install** on Windows／macOS (bundled runtime). Linux still needs Python 3.10+.

| Entry | URL |
|-------|-----|
| Frontend (search guide in header) | http://127.0.0.1:8000/frontend/index.html |
| API docs | http://127.0.0.1:8000/docs |
| Health check | http://127.0.0.1:8000/ |

The package includes `lyrics.db` and static near／antonym data. Troubleshooting: see `README.txt` in the extracted folder.

### 2. How to use

**Three modes** (header segmented control):

| Mode | `mode` | Purpose |
|------|--------|---------|
| **0243 mode** (loose) | `m1` | 0243 code equivalence variants |
| **02493 mode** (strict) | `m2` | 02493 codes; finer entering-tone distinction |
| **Near／antonym** | `syn` | Chinese-only near／antonym columns (no Jyutping) |

**Syntax families** (all work in **0243 search mode** unless noted):

* **Surface／digits／Jyutping**: type `你好`, `23`, `nei hou`.
* **Position & wildcards**: `香??`, `?你?`, `3_`, `23?`.
* **Serial rhyme／initial anchors**: left-to-right scan—each digit is one syllable code; `{code}{char}=` rhyme, `{code}={char}` initial (e.g. `23就=`, `04困=49倒=`, `?3人=?`).
* **Prefix wildcard equals**: `?{word≥2}=` first syllable wildcard + whole-word rhyme template (e.g. `?香港=`).
* **Digits + tail character**: `23就` (tail rhymes with 「就」), `23@就` (literal tail fixed), `23*就` (longer slot).
* **Equals anchors**: `=` **after** anchor compares rhyme (`就=`, `?*就=`); `=` **before** anchor compares initial (`?=就`); whole-word rhyme `香港=`, code-sandwich `2=我3`.
* **Jyutping anchors**: Jyutping replaces a reference character inside mask-family queries (`?syut?` middle syllable, `23o` rhyme on **last slot** after digits, `3hon4` first-slot syllable, etc.); **not** a full Jyutping lookup; **near／antonym mode** does not accept them.
* **Near／antonym relation queries**: `~開心`, `!你`, `33!開心`.
* **Antonym compounds**: `!!`, `33!!`, `!!你`, `33!!你` (e.g. 生死, 是非).
* **Near-synonym compounds**: `~~`, `33~~`, `~~你`, `33~~你` (e.g. 朋友, 恐懼); **not** in near／antonym mode.

The in-app **Search guide** has clickable examples; the cheat sheet below matches that page for offline reference.

### 3. Git clone (developers)

A clone **does not** include a full `lyrics.db`. To run `python main.py` locally, download `lyrics.db` from Releases into the repo root, or rebuild via the Maintainer pipeline below.

```bash
pip install -r requirements.txt
python main.py
```

Or use `./start.sh` (creates venv and opens the browser—you still need `lyrics.db`).

**Bundled with the repo** (tier 1, see Data sources): essay frequency, curated common words, antonym／near-synonym compound lists, and bundled static near／antonym files. **Rime `char.csv` and antisem are not in git**—after clone run `python scripts/bootstrap_data.py` (tier 2).

---

## Maintainer: rebuild lexicon & near／antonym data

Outputs are local／gitignored—**do not** commit. See [CONTRIBUTING.md](CONTRIBUTING.md).

```bash
pip install -r requirements-dev.txt
python scripts/bootstrap_data.py
# 1. Build multi-character lexicon readings from upstream tables (see THIRD_PARTY_NOTICES § multi-character readings)
# 2. Import words table (also syncs README word-entry total):
python scripts/ingest/import_data.py
# 3. Near／antonym ingest:
python -m ingest report
python -m ingest normalize --source current_static
python -m ingest build-relations
```

Optional relation sources (off by default): `data/syn_ant/sources.yaml`.

### Official data release (four artifacts)

Check [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) before redistribution. **Do not** commit large artifacts to git.  
**Full release** vs **lexicon-only release** tiers and checklists: [release.md](release.md) ([ADR-0008](adr/0008-release-publishing-tiers.md)).

| Asset | Purpose |
|-------|---------|
| `lyrics.db` | Full **word-entry store** (`words` + `word_relations`) |
| `canto-0243-portable.zip` | Windows zero-install (`START.bat`, bundled venv) |
| `canto-0243-portable-macos-arm64.tar.gz` | macOS zero-install **`Canto-0243.app`** (Apple Silicon) |
| `canto-0243-portable-macos-x86_64.tar.gz` | macOS zero-install **`Canto-0243.app`** (Intel) |
| `words-lexicon.json` | **Lexicon-reading** sidecar |

```bash
python scripts/export_words_lexicon.py -o dist/words-lexicon.json
python scripts/update_readme_words_count.py
# After large README.md edits, regenerate Simplified written Chinese:
# python scripts/gen_readme_zh_hans.py
# Windows:
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
# macOS (Canto-0243.app tar.gz):
bash scripts/build-portable.sh
# Upload all four to GitHub Release (portable must include zip + macOS tar.gz)
```

---

## Query syntax cheat sheet

Matches clickable examples in the frontend **Search guide**.

### Basic lookup

| Example | Description |
|---------|-------------|
| `就` | All readings for this character |
| `你好` | Lookup this word |
| `syut` | Jyutping (no tone digits) |
| `nei hou` | Jyutping (no tone digits) |
| `ming4 baak6` | Jyutping (with tones) |

### 0243／02493 digits

| Example | Description | Mode |
|---------|-------------|------|
| `23` | Same-code matches | 0243 mode |
| `93` | 02493 adds digit 9 | 02493 mode |

**Punctuation equivalence** (normalized at query dispatch): full-width `？` = `?`; `～`／`！` = `~`／`!`; `~~`／`!!` = `～～`／`！！` and mixed forms (e.g. `~～`).

### Mask queries (literals / digits / wildcards)

| Example | Description |
|---------|-------------|
| `香??` | 3-char word; first char is 「香」 |
| `?你?` | 3-char word; middle is 「你」 |
| `_識_` | 3-char word; middle is 「識」 |
| `3_` | 2-char; first syllable matches 3; tail unrestricted |
| `23?` | 3-char; first two syllables match 23; third unrestricted |
| `門0` | 2-char; first is 「門」 + second slot code is 0 |

### Serial rhyme／initial anchors

Left-to-right scan: each digit is one syllable code; `=` always sits to the **right** of the reference character. `{code}{char}=` compares rhyme; `{code}={char}` compares initial. A single `?` can wildcard one slot.

| Example | Description |
|---------|-------------|
| `4困=` | 1-char; rhymes with 「困」 |
| `04困=` | 2-char; slot 2 rhymes with 「困」 |
| `23就=` | 2-char; code 23 + tail rhymes with 「就」 |
| `04困=49倒=` | 4-char; rhyme anchors on slots 2／4 (窮困潦倒) |
| `04=困49=倒` | 4-char; initial anchors on slots 2／4 |
| `?3人=?` | 3-char; middle code 3 + rhymes with 「人」 |
| `?4困=4潦=9倒=` | 4-char; leading wildcard + rhyme anchors |

### Prefix wildcard equals

| Example | Description |
|---------|-------------|
| `?香港=` | First syllable wildcard; remaining syllables rhyme with 「香港」 |
| `?困潦倒=` | First syllable wildcard; rest rhymes with 「困潦倒」 (trailing `=` required) |

### Star anchors (`*`) — pin a slot by literal / rhyme / initial

Use `*` to connect digits and an anchor character. **`=` always sticks to the anchor character**: `就=` means “same rhyme (finals) as 就”; without `=` it means the slot is literally that character. `*=就` is the legacy “same initial” shape.

Three shapes (slot is obvious by where `*` appears):

- **Tail slot**: `{code}*{Han}{optional '='}` / `{code}*= {Han}`  
  Examples: `23*就`, `23*就=`, `23*=就`
- **Middle slot**: `{left_code}*{Han}{optional '='}{right_code}`  
  Examples: `2*就3` (middle literal), `2*就=3` (middle rhymes)
- **Head slot**: `*{Han}{optional '='}{right_code}`  
  Examples: `*門0` (head literal), `*門=0` (head rhymes)

> `門0` still works, but is a **deprecated** alias. Prefer `*門0`.

(Related) Rhyme／initial anchors: `香=?`, `*香=?`, `就=` (`?就=` normalizes), `=就` (`?=就` normalizes), `?*就=`, `?*=就`, `?*港=?` (equivalent to `?港=?` after normalize), `=香?`.

### Jyutping anchors

Within the **mask-family** queries, Jyutping marks a phoneme constraint—**not** a full Jyutping lookup (`syut` looks up a word; `?syut?` anchors the middle slot). **Near／antonym mode** does not accept Jyutping anchors; invalid rhyme fragments are rejected with a hint.

**Wildcard slots**

| Example | Description |
|---------|-------------|
| `?yut?` | 3-char; **middle** rhyme fragment `yut` |
| `?syut?` | 3-char; **middle** full syllable `syut` |
| `?hon` | 2-char; **last slot** full syllable `hon` |

**Digits + Jyutping**

| Example | Description |
|---------|-------------|
| `3hon4` | 2-char; code `34`; **first slot** full syllable `hon` |
| `3?hon4` | 3-char; `{digit}?{syllable}{digit}`; middle syllable |
| `3h4` | 2-char; code `34`; **first slot** initial `h` |
| `23ngo` | 2-char; code `23`; **last slot** full syllable `ngo` |
| `23o` | 2-char; code `23`; **last slot** rhyme `o` (broader than `23ngo`) |
| `23ei0` | 3-char; code `230`; **middle** rhyme `ei` (like `23你=0`) |

In `3hon4` the syllable is on the **first** slot; in `23ngo`／`23o` the Jyutping suffix anchors the **last** slot after the digit run—different shapes, do not mix them up.

### Trailing `=` (whole-word rhyme／code sandwich)

| Example | Description |
|---------|-------------|
| `香港=` | 2-char; whole word rhymes with 「香港」 |
| `大蛋糕=` | 3-char; whole word rhymes with 「大蛋糕」 |
| `34英皇=` | 5-char; prefix code 34 + whole word rhymes with 「英皇」 |
| `2我=3` | 2-char; 23 same-code; first char rhymes with 「我」 |

### Leading `=` (whole-word initial)

| Example | Description |
|---------|-------------|
| `=香港` | 2-char; whole word same initial pattern as 「香港」 |
| `2=我3` | 2-char; 23 same-code; first char same initial as 「我」 |

### Near／antonym

| Example | Description |
|---------|-------------|
| `~開心` | Near-synonyms of 「開心」 |
| `!你` | Antonyms of 「你」 (includes mirror near-synonyms) |
| `33!開心` | 33 same-code + antonyms of 「開心」 |
| `mode=syn` + `開心` | Near／antonym mode (two-column UI) |

### Antonym compounds

| Example | Description |
|---------|-------------|
| `!!` | 2-char antonym compounds (e.g. 生死, 是非) |
| `33!!` | 33 same-code + antonym compound |
| `!!你` | Antonym compound; tail rhymes with 「你」 |
| `33!!你` | 33 same-code + antonym compound + tail rhymes with 「你」 |

### Near-synonym compounds

| Example | Description |
|---------|-------------|
| `~~` | 2-char near-synonym compounds (e.g. 朋友, 恐懼) |
| `33~~` | 33 same-code + near-synonym compound |
| `~~你` | Near-synonym compound; tail rhymes with 「你」 |
| `33~~你` | 33 same-code + near-synonym compound + tail rhymes with 「你」 |

```http
GET /words/search/?q=你好&mode=m1
GET /words/search/?q=23就&mode=m1
GET /words/search/?q=23就=&mode=m1
GET /words/search/?q=04困=49倒=&mode=m1
GET /words/search/?q=?香港=&mode=m1
GET /words/search/?q=香港=&mode=m1
GET /words/search/?q=2=我3&mode=m1
GET /words/search/?q=nei%20hou&mode=m1
GET /words/search/?q=?syut?&mode=m1
GET /words/search/?q=23o&mode=m1
GET /words/search/?q=3hon4&mode=m1
GET /words/search/?q=!你&mode=m1
GET /words/search/?q=~~&mode=m1
GET /words/search/?q=開心&mode=syn
```

---

## Advanced: architecture & deployment

### Architecture overview

```text
query string → query_parse (syntax class · ParsedQuery · build_match_spec)
            → query_dispatch (priority registry → executors)
                   ↓
    position_match · word_lookup_executor · relation_syntax_executor
                   ↓
    domain/lexicon (admission) · domain/thesaurus (static thesaurus) · domain/relations (relation pool／graph)
                   ↓
         words table · word_cache (short-word preload)
                   ↓
         essay_sort · JSON results (plain digits include X-Search-Total)
```

| Layer | Path | Role |
|-------|------|------|
| Domain | `app/domain/lexicon/` | Lexicon port · **admission decisions** |
| Domain | `app/domain/thesaurus/` | **Static thesaurus port** |
| Domain | `app/domain/relations/` | **Near／antonym pool** · **relation graph** · ranking |
| Service | `app/services/query_parse.py` | `parse_query` · `build_match_spec` |
| Service | `app/services/query_dispatch.py` | `search_words` registry |
| Service | `app/services/position_match.py` | Position match · equals／code-sandwich |
| Service | `app/services/*_executor.py` | lookup · `~`/`!` · `!!` · `~~` |

Design principle: domain rules live in `app/domain/`; ingest and runtime share the same ports and pool rules.

### Deployment & database

**Supported product path**: offline single-machine + **SQLite** (`lyrics.db`). New schema is maintained only via SQLite bootstrap／`scripts/db/init_db.py`.

**PostgreSQL**: frozen scaffold, **not** a primary delivery target. Experimental use: `requirements-postgres.txt` and [`CONTEXT.md`](../CONTEXT.md) § product boundary.

### Project layout

```text
Canto-0243/
├── app/                    # API · domain · services · models
├── frontend/               # index.html (search home; relation tab in-app)
├── portable/               # START.bat · START.sh · env.portable
├── data/                   # see Data sources (three tiers)
├── ingest/                 # python -m ingest
├── scripts/                # bootstrap · build-portable · import_data
├── tests/
├── docs/                   # CONTRIBUTING · README.* · release
├── main.py · start.sh      # dev entrypoints
├── README.md               # 繁中（GitHub 首页）
├── LICENSE · THIRD_PARTY_NOTICES.md
├── CONTEXT.md · WORKLOG.md · AGENTS.md · skills-lock.json
└── requirements*.txt
```

### Data sources & licensing

Verify [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) before redistribution. Admission and ranking: [`CONTEXT.md`](../CONTEXT.md) § lexicon & ranking.

| Tier | Description | Examples |
|------|-------------|----------|
| **1 · With repo** | available on clone | `data/essay/`, `data/lexicon/`, `data/syn_ant/`, bundled cilin／thesaurus |
| **2 · bootstrap** | `python scripts/bootstrap_data.py` | rime `char.csv`, antisem |
| **3 · maintainer-built** | gitignored | `lyrics.db`, lexicon-reading JSON |

Default near／antonym pipeline: `data/syn_ant/sources.yaml` (cilin, guotong, antisem, compound lists). Full upstream table: [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

---

## Tests

Currently **225** unittest cases.

```bash
python -m unittest discover -s tests -q
```

Key regressions: plain-Chinese strict code, wildcards, `mode=syn`, equals／code-sandwich, Jyutping, Jyutping anchors, `~~`／`!!` compounds.

---

## Dependencies

| Layer | File | Purpose |
|-------|------|---------|
| Runtime | `requirements.txt` | FastAPI + SQLAlchemy + SQLite |
| Ingest / dev | `requirements-dev.txt` | ingest & legacy scripts |
| PostgreSQL (frozen) | `requirements-postgres.txt` | experimental |

---

## Canto-0243 license & use

You may use this tool for Cantonese lyric writing, rhyme lookup, character substitution, and as part of **commercial creative work** (songs, scripts, published lyrics)—subject to the restrictions below:

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
* **Guotong near／antonym dictionary**: [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary), [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE).
* **ChineseAntiword (antisem)**: [liuhuanyong/ChineseAntiword](https://github.com/liuhuanyong/ChineseAntiword); upstream has **no explicit license**—attribute locally and verify before redistribution.
* **words.hk Cantonese word list**: [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/), **public domain** (thanks [words.hk](https://words.hk/)).
* **Multi-character reading upstream** (maintainer-built `lyrics.db`): [CC-Canto](https://cantonese.org/download.html) ([CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)), [Kaifang Dictionary · Cantonese](https://kaifangcidian.com/xiazai/) ([CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)).

Building or redistributing lexicons from these sources requires complying with each license; some impose **non-commercial** or **attribution** terms. Optional sources (e.g. COW) are off by default—see `data/syn_ant/sources.yaml`.

---

## Related documents

| Document | Contents |
|----------|----------|
| [`README.md`](../README.md) | Traditional Chinese (GitHub homepage) |
| [`README.zh-Hans.md`](README.zh-Hans.md) | Simplified Chinese documentation (written Chinese) |
| [`README.en.md`](README.en.md) | English documentation (this file) |
| [`LICENSE`](../LICENSE) | Canto-0243 License |
| [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) | Third-party data licenses |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contributing & repo-root conventions |
| [`CONTEXT.md`](../CONTEXT.md) | Domain glossary |
| [`WORKLOG.md`](../WORKLOG.md) | Change log |
| [`AGENTS.md`](../AGENTS.md) | Agent collaboration notes |

---

**Last updated**: 2026-06-18 (v1.6.4 · 02493 digit normalize · partial rhyme fix · macOS Open.command · cache prewarm)
