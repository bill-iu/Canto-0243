# label_part1 — POS fill summary

**File:** `data/pos/audit/u_inlex_top2000_nf2/label_part1.tsv`
**Rows:** 400 (all filled)
**Batch rules:** voice empty; family empty or `idiom` only; `u` only if opaque/fragment

## Counts

| metric | n |
|--------|---|
| **formal** (pos ≠ u) | **400** |
| **u** | **0** |
| single-tag | 345 |
| multi-tag | 55 |
| family=idiom | 7 |

### pos distribution

| pos | n |
|-----|---|
| n | 213 |
| v | 82 |
| a | 36 |
| n,v | 23 |
| a,n | 12 |
| a,v | 10 |
| r | 7 |
| x | 7 |
| a,r | 4 |
| n,r | 2 |
| n,x | 1 |
| r,x | 1 |
| v,x | 1 |
| a,n,r | 1 |

### tag incidence (row contains tag)

| tag | rows |
|-----|-----:|
| n | 252 |
| v | 116 |
| a | 63 |
| r | 15 |
| x | 10 |
| u | 0 |

## Remaining u

_None._

## family=idiom (7)

| literal | pos |
|---------|-----|
| 毫不猶豫 | r |
| 層出不窮 | a,v |
| 一天到晚 | r |
| 突如其來 | a |
| 自然而然 | r |
| 一見鍾情 | v |
| 淚流滿面 | a,v |

## Notes

- Canto: 畀心機／發嬲／着緊／睇相／知到／第個／趕唔切／趷／順攤／預咗／雨褸／點搞／走堂／洗衫／腸粉／餐牌／餐檯／阿嬸／鬼仔／衰女 → formal
- Places/orgs/people: 港大／港澳／銀川／南美／舊金山／阿曼／秦始皇／李嘉誠／亞運會／紅十字會 → n
- Closed/x: 第個／貳／孰／早上好／上萬／哎喲／之列／何不(r,x)／省得(v,x)
- Idioms: 毫不猶豫、層出不窮、一天到晚、突如其來、自然而然、一見鍾情、淚流滿面
- multi 從嚴：機動 a,n；現任 a,n；着緊 a,v；簡稱 n,v；一對一 a,n,r 等
- free morphemes (決／獨／玄／萌／責／驗／曝／搗…) 標 formal，唔當 residual u

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex_top2000_nf2/label_part1.tsv` | 400 列已填 pos |
| `data/pos/audit/u_inlex_top2000_nf2/label_part1_summary.md` | 本摘要 |
