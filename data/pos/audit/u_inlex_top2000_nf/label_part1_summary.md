# label_part1 — POS fill summary

**File:** `data/pos/audit/u_inlex_top2000_nf/label_part1.tsv`  
**Rows:** 400 (all filled)  
**Batch rules:** voice empty; family empty or `idiom` only; `u` only if opaque

## Counts

| metric | n |
|--------|---|
| **formal** (pos ≠ u) | **399** |
| **u** | **1** |
| single-tag | 343 |
| multi-tag | 56 |
| family=idiom | 5 |

### pos distribution

| pos | n |
|-----|---|
| n | 162 |
| v | 112 |
| a | 41 |
| n,v | 25 |
| r | 21 |
| a,n | 13 |
| a,v | 8 |
| x | 7 |
| a,r | 6 |
| r,v | 2 |
| u | 1 |
| v,x | 1 |
| n,r | 1 |

## Remaining u

| literal | freq | note |
|---------|------|------|
| 關斗 | 1690 | 罕／不明 |

## family=idiom (5)

| literal | pos |
|---------|-----|
| 一無所知 | v |
| 事到如今 | r |
| 見步行步 | v |
| 僅供參考 | v |
| 告一段落 | v |

## Notes

- Canto statives/degree: 麻麻地 `a`、鬼咁 `r`、靜靜雞 `r`、膽粗粗／熱辣辣／戇居居 `a`、冇心機 `a`
- Canto verbs: 搞到、慳返、淆底、諗落、起上嚟、趕得切、食埋、扎醒、整蠱、扮到、唔知 等 → `v`
- Places/orgs/brands: 韓國、華盛頓、汕頭、三峽、莫斯科、土耳其、肯德基、利賓納、利物浦、天河 等 → `n`
- Closed/particles: 噻、爾、一連串、三位、兩份、呢類、之初 → `x`
- Special note row: `种` = 簡體「種」→ `n,v`
