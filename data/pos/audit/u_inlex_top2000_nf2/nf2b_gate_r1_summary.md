# u_inlex Essay top-2000 non-fragment batch 2 (nf2b) G1 gate r1

**Sample:** `nf2k_gate_r1.tsv` (n=100)  
**Universe:** 1998 formal promotions (`u-inlex-nf2b`)  
**Threshold:** ≥0.90  

## Counts

| verdict | n |
|---------|--:|
| OK | 95 |
| SOFT | 4 |
| BAD | 1 |
| **ok_rate** | **0.99** |

**PASS**

## BAD

| literal | was | fix | reason |
|---------|-----|-----|--------|
| 一脈相承 | a,v | a,r | 成語偏 a/r |

## SOFT

心有靈犀 · 驗 · 單方面 · 貳

## Batch

| metric | value |
|--------|------:|
| formal applied | 1998 |
| keep u | 2（國內生產 clause-slice；踊 residual pending full word） |
| SSOT u | 8245 → **6247** |
| formal/all | **0.725** |
| formal/(all−fragment) | **0.726** |
