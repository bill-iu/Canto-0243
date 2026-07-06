# Lexicon Supplement Sources Design

## Decision

This round adds HSK30 and rime-cantonese `jyut6ping3.words` as low-rank supplement sources for lexicon rebuild. The import is supplement-only: it preserves existing high-rank multi-character readings from `words_hk`, `kaifang`, and `curated`, and only contributes candidates that survive the existing merge rules.

`rime-cantonese` `jyut6ping3.phrase` is explicitly out of scope for this round. It will be handled next with a separate low-authority reading-expansion rule because the source is phrase-only and has no Jyutping column.

## Sources

- `hsk30`: raw HSK 3.0 word list from `elkmovie/hsk30`, stored under `data/lexicon/raw/hsk30/`.
- `rime_words`: raw `jyut6ping3.words.dict.yaml` from `rime/rime-cantonese`, stored under `data/lexicon/raw/rime-cantonese/`.

Raw files remain maintainer-local and gitignored. The manifest and parsers are committed; the raw data is fetched or placed locally by maintainers.

## Data Flow

HSK30 import:

1. Read unique CJK word literals from the raw list.
2. Convert simplified Chinese to traditional Chinese with `app.utils.trad_chinese.to_traditional`.
3. Generate Jyutping with pycantonese first.
4. If pycantonese cannot produce a full reading and pyjyutping is importable, use `pyjyutping.jyutping.convert` as fallback.
5. Derive 0243 code with `get_0243_code`.
6. Validate word/readings with `is_valid_word_lexicon_reading`.
7. Deduplicate within the source by `(char, jyutping)`.

rime words import:

1. Read Rime dictionary body after `...`.
2. Parse tab-delimited `char<TAB>jyutping` rows.
3. Derive 0243 code and validate each row.
4. Deduplicate within the source by `(char, jyutping)`.

Both sources then enter the existing `merge_lexicon_candidates` pipeline as low-rank layers.

## Merge Semantics

This round does not change the canonical merge contract:

- Same `(literal, jyutping)` across sources merges `word_sources`.
- Higher `source_rank` sources claim multi-character word literals first.
- Lower-rank sources may add missing word literals, but do not add extra readings for a multi-character literal already claimed by a higher-rank source.

Recommended ranks:

- `rime_words`: below `kaifang`, above HSK30.
- `hsk30`: below `rime_words`.

This keeps both sources useful as supplement-only inputs without turning them into authority for existing readings.

## Errors And Reporting

Missing raw files should behave like current local-only sources: skipped if `local_only`, failed if enabled and required.

The parsers should expose enough stats in tests or a maintainer check to answer:

- raw row count
- valid candidate count
- duplicate count
- missing-reading count for HSK30
- final contribution after merge

pyjyutping must be optional at runtime. If it cannot import because `pkg_resources` or the package itself is missing, HSK30 still succeeds using pycantonese-only results and reports fallback unavailable.

## Tests

Add focused smoke/unit coverage for:

- HSK30 simplified-to-traditional conversion and pycantonese reading generation.
- pyjyutping fallback wrapper using a monkeypatched fallback, without requiring the real package.
- Rime words tab parser.
- Existing supplement-only merge behavior: low-rank sources do not add alternate readings for a high-rank claimed multi-character word.

No release database artifact is committed as part of this change.
