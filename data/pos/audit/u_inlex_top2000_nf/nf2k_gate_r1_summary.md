# u_inlex Essay top-2000 non-fragment gate r1 (G1)

**Sample:** `nf2k_gate_r1.tsv` (n=100)  
**Universe:** 1992 formal promotions (`u-inlex-nf2k`)  
**Threshold:** (OK+SOFT)/n ≥ 0.90  

## Counts

| verdict | n | % |
|---------|--:|---:|
| OK | 96 | 96% |
| SOFT | 2 | 2% |
| BAD | 2 | 2% |
| **ok_rate** | **98/100 = 0.98** | |

**PASS**

## BAD fixes

| literal | was | fix | reason |
|---------|-----|-----|--------|
| 僅供參考 | v + idiom | **x**, family 空 | 套語標記，非動詞／熟語傘 |
| 煞 | a,n,r,v | **a,v** | 四標過寬 |

## SOFT

三個字 · 實戰

## Batch stats

| metric | value |
|--------|------:|
| formal applied | 1992 |
| keep `u` | 8（已標 fragment） |
| SSOT `u` before → after | 10251 → **8259** |
| formal/all | **0.637** |
| formal/(all−fragment) | **0.637** |

### keep-u fragment tags

clause-slice: 我溝、將你、實會、自已  
opaque: 關斗、拉西  
residual (pending full-word alias): 牴、魍  
