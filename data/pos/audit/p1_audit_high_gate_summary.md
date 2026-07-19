# P1 high|gate POS audit summary

**Sample:** `data/pos/audit/p1_sample_high_gate.tsv` (n=50)  
**Stratum:** high|gate — high-trust tags for hard gate + creator display  
**Date:** 2026-07-18

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 35 | 70% |
| SOFT | 2 | 4% |
| BAD | 13 | 26% |
| **total** | **50** | 100% |

## Top error patterns (BAD)

1. **verb-suffix heuristic false positive** (ends in 好/上/下/來/過 → forced `v`) — **12/13 BAD**
   - Adverbs mis-tagged `v`: 原來、只好、從來、越來 → **r**
   - Function / limit words: 也好、以上、咗下 → **x**
   - Nouns (place / abstract): 天下、手上、牀上 → **n**
   - Stative / degree-adj: 幾好、更好 → **a** (keep stative as a)
2. **Segmentation residue** — **1/13 BAD**
   - 我過 → **u** (not a clear lexical verb; verb-suffix on 過)

## SOFT (not wrong primary)

| literal | pos | note |
|---------|-----|------|
| 唔好 | v | Primary v OK for prohibition; both a+v common → suggest `a,v` |
| 跟住 | v | Primary v OK for “follow”; sequential “then” also common → suggest `v,r` |

## OK patterns worth keeping

- True V+result/aspect compounds: 做好、兜過、對住、拖住、掛住、行開、話過、諗住、講完、返起、下去、看好
- Closed-class `x`: 五、千、及、各、的、此、而且、與
- Reviewed multi-tags: 句 `n,x`, 可能 `a,r`, 真實 `a`, 報仇 `v`
- Legitimate multi: 多 `a,r`, 是 `v,x`, 才 `r,x`, 唔係 `v,x`, 能夠 `v,x`, 需要 `n,v`
- Clear r: 一齊、再、即刻、更
- Clear n: 社會主義

## Gate impact note

All BAD rows are currently **high** trust and thus in **閘用詞類**. Wrong primary `v` will falsely pass same-POS with real verbs and clash with correct a/r/n/x peers. Priority fix batch: verb-suffix two-char list ending in 好/上/下/來 (exclude true resultatives like 做好／看好).
