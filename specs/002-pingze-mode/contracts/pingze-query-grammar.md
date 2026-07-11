# Contract: 平仄模式查詢語法

## Activation

This grammar is active only while search state has `mode=pz`. Outside that mode, P and Z are not pingze tokens and no pingze redirect occurs.

## Slot tokens

| Token | Meaning |
|---|---|
| `P` | One position whose stored 394052 digit is 0 or 3. |
| `Z` | One position whose stored 394052 digit is not 0 or 3. |
| `0`–`9` | One position matched with the selected pzmode's existing numeric-code rules. |
| `?` | Exactly one unconstrained position. |

Slots may appear before, after or between other positions where the existing serial/wildcard grammar permits them. Pattern width equals the number of position slots plus the width required by its existing anchors.

## Composition

`PZ好=` means P at the first position, Z at the second position, then the existing `好=` rhyme-anchor condition. The `好=` portion retains its pre-existing meaning. `?PZ好=` follows the same rule with an unconstrained first position.

Existing valid literal-anchor, rhyme-anchor and missing-character forms retain their established precedence and semantics. Jyutping-anchor forms are invalid in pingze mode and return the dedicated unsupported-Jyutping-anchor hint.

## Failure behavior

- Invalid token combinations in pingze mode return a pingze-specific syntax hint.
- No invalid pingze query silently falls back to Jyutping.
- Normal modes never return a pingze syntax hint solely because a query contains P or Z.
