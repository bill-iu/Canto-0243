# u_inlex gate POS quality audit (r1)

**Sample:** `data/pos/audit/u_inlex/u_inlex_gate_r1.tsv` (n=99)  
**Universe:** in-lexicon still-`u` Essay-top-ish batch agent labels (`u-inlex-agent`) formal promotions  
**Threshold:** ok_rate = (OK+SOFT)/n **≥ 0.90**  
**Date:** 2026-07-19  

## Counts

| verdict | n | % |
|---------|--:|---:|
| OK | 91 | 91.9% |
| SOFT | 5 | 5.1% |
| BAD | 3 | 3.0% |
| **total** | **99** | 100% |

**ok_rate = 96/99 = 0.9697**

**PASS**

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 九成 | n,r,x | n,r | x 假陽：比例/程度非助詞 |
| 傅 | n,v | n | 主用名詞/姓；v 古罕用 |
| 臺 | n,x | n | 主用名詞；x 假陽 |

## SOFT

係路 · 天黑 · 早前 · 耀 · 老死
