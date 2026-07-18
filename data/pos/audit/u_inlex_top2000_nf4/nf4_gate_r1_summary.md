# u_inlex Essay top-2000 non-fragment batch 4 (nf4) G1 gate r1

**Sample:** n=100 · **Universe:** 2000 (`u-inlex-nf4`)  
**ok_rate = 0.99** (95 OK + 4 SOFT + 1 BAD) · **PASS**

## BAD

| literal | was | fix | reason |
|---------|-----|-----|--------|
| 五福臨門 | x | **a** | 祝福語，非助詞 |

## SOFT

話雖如此 · 黎明時分 · 作者不詳 · 世界大同

## Batch

| metric | value |
|--------|------:|
| formal applied | 2000 |
| keep u | 0 |
| SSOT u | 4248 → **2248** |
| formal/(all−fragment) | **0.902** |
