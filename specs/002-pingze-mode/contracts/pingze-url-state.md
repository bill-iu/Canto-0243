# Contract: 平仄模式 URL and tab state

## Canonical URL

```text
?mode=pz&pzmode=m1&q=PZ%3F
```

| Parameter | Values | Rule |
|---|---|---|
| `mode` | `pz` | Activates pingze mode. |
| `pzmode` | `m1`, `m2`, `m3` | Numeric-slot comparison mode. Always emitted with `mode=pz`. |
| `q` | encoded query text | Existing query parameter semantics. |

`mode=pz` without `pzmode` parses as `pzmode=m1`. Invalid or non-pingze mode values ignore `pzmode` and preserve existing URL behavior.

## History and tabs

Every search history frame stores query, mode and optional pzmode. A pz frame always restores both values before search execution. Browser back/forward, tab selection, session restoration and guide example navigation must use the same frame shape, so a pz query never inherits another tab's sub-mode.
