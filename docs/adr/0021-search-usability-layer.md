# Search usability layer (查詢語意解釋)

Creators face powerful but position-sensitive anchor syntax (`+`, `=`). Phase C adds a **search usability layer**: server-authoritative **查詢語意解釋** driven by `normalize_and_parse` → `build_match_spec` → **left-to-right slot scan** of `MatchSpec`, rendered below the search field (debounced live input). Parser and dispatch behavior are unchanged (100% backward compatible).

## Architecture

1. **Parse** — `normalize_and_parse(q)` → `ParsedQuery` (unchanged).
2. **Spec** — `build_match_spec_for_parsed(parsed)` → `MatchSpec` (same registry as **查詢分派** / position match).
3. **Explain** — walk `width` slots 0..n−1; merge `mask` wildcards/literals with `slots` constraints; special branches for `EqualsSpan`, prefix-wildcard equals, hybrid ref, compounds, and no-spec fallbacks.
4. **Warnings** — positional confusion hints (e.g. `23o` vs `23+o`) stay **below** the summary; never replace it.

Kinds without `MatchSpec` (word lookup, digit code, relation lookup, jyutping fragment, hybrid-tail equals alias, unmatched) use the shortest action sentence from `ParsedQuery` alone.

## Creator copy rules

- Positions: **第 N 個字** (not 格／槽).
- Wildcards: **任意字**.
- Code digits: **同 {digit} 同音**.
- Phoneme anchors: **同「{字}」同韻** / **同聲**; jyutping fragments: **同{片段} 同韻母** / **同聲母**.
- **等號查詢** (whole word): one line — 整詞同「…」同韻／同聲 + **押韻標註** (單押／雙押／…; N 字 = N押, no cap).
- **前綴通配等號查詢**: 首個字任意；第 2…n 個字同「參考詞」同韻／同聲 + 押韻標註 (not whole-word rhyme alone).
- Left-code whole-word equals (e.g. `0449窮困潦倒=`): rhyme label follows reference word length; code constraints in a separate clause.
- Relation lookup: **近義詞** / **反義詞** (not 近義關係／反義關係).

**Considered:** per-`ParsedQuery` isinstance handlers — rejected after grill (drift from **比對規格建構**). Client-side parse duplicate — rejected. Natural-language intent input — deferred. Visual anchor builder (phase B) — deferred; will reuse this endpoint.