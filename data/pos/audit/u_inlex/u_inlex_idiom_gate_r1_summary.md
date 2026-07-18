# u_inlex idiom_u gate POS quality audit (r1)

**Sample:** `data/pos/audit/u_inlex/u_inlex_idiom_gate_r1.tsv` (n=50)  
**Universe:** `idiom_u_relabel.tsv` promotions (`u-inlex-idiom`)  
**Threshold:** ok_rate = (OK+SOFT)/n **≥ 0.90**  
**Date:** 2026-07-19  

## Counts

| verdict | n | % |
|---------|--:|---:|
| OK | 39 | 78% |
| SOFT | 7 | 14% |
| BAD | 4 | 8% |
| **total** | **50** | 100% |

**ok_rate = 46/50 = 0.92**

**PASS**

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 全始全終 | a,v | r | 自始至終義；副詞性 |
| 各就各位 | a,v | v | 祈使/動作 |
| 逐字逐句 | a,v | r | 方式副 |
| 風言風語 | a,v | n | 閒話名詞 |

## Non-idiom (family empty, OK)

同班同學 · 學士學位 · 電子電路（及 relabel 中 吉爾吉斯 等）
