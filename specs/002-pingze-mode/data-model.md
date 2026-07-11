# Data Model: 平仄模式

## PingzeSearchState

Represents a restorable search selection.

| Field | Values | Rules |
|---|---|---|
| `q` | query string | Unchanged user query text. |
| `mode` | existing modes or `pz` | `pz` enables pingze grammar. |
| `pzmode` | `m1`, `m2`, `m3` | Required when `mode=pz`; default `m1` when absent. Ignored otherwise. |

The state is carried by a tab's current history frame, browser history and share URL. It has no database persistence or migration.

## PingzePattern

Represents a pingze-mode query after outer grammar has determined its width and any existing anchors.

| Field | Meaning |
|---|---|
| `width` | Exact number of constrained or unconstrained positions. |
| `slots` | Position-indexed P/Z/number/wildcard conditions. |
| `anchors` | Existing literal, final/rhyme and missing-character conditions retained from the outer grammar. |
| `pzmode` | Numeric-slot comparison mode from PingzeSearchState. |

## Positional constraint extension

| Constraint | Value | Match rule |
|---|---|---|
| `tone_class` | `ping` | Stored 394052 digit is `0` or `3`. |
| `tone_class` | `ze` | Stored 394052 digit is neither `0` nor `3`. |
| existing `code_digit` | digit | Existing selected-mode code-variant rule. |
| existing wildcard/mask | none | The position has no condition. |
| existing anchors | existing values | Existing literal/rhyme/missing-character semantics. |

Constraints combine conjunctively: a candidate must satisfy every condition assigned by the parsed grammar. No new lexicon table or stored field is introduced.
