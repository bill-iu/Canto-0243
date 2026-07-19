# P2 熟語 (family=idiom) quality audit (r1)

**Sample:** `data/pos/audit/p2_idiom_quality_r1.tsv` (n=50)  
**Universe:** 883 pattern-based len4 idiom-tagged literals  
**Seed:** 20260719  
**Threshold:** ok_rate > 0.90  
**Date:** 2026-07-19

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 44 | 88% |
| SOFT | 5 | 10% |
| BAD | 1 | 2% |
| **total** | **50** | 100% |

**ok_rate = (OK+SOFT)/n = 49/50 = 0.98**

**PASS** (0.98 > 0.90)

## BAD detail

| literal | pattern | fix_family | reason |
|---------|---------|------------|--------|
| 統購統銷 | ABAC | *(empty — clear 熟語)* | 計劃經濟政策術語 NP，非固定說法／成語類熟語 |

## SOFT（ borderline 固定語，留 熟語 可）

| literal | pattern | note |
|---------|---------|------|
| 即興之作 | 之字格 | 偏描寫 NP「即興+之作」；固定搭配可留 |
| 好好睇睇 | AABB | 粵語 AABB 重疊偏能產；固定度薄但可留 |
| 恰恰相反 | AABC | 常見固定搭配；偏副詞組非典成語 |
| 新人新事 | ABAC | 時代口號式對舉；固定度中等可留 |
| 生存之道 | 之字格 | X之道 能產；文學固定式可留 |

## OK patterns (keep)

- Classic 成語／固定語: 一望無垠、一石二鳥、不破不立、奄奄一息、如醉如痴、彈指之間、擒賊擒王、朗朗上口、無影無蹤、竊竊私語、耿耿於懷、自由自在、若即若離、面面相覷、取之不盡、一瘸一拐、先到先得…
- AABB／ABAB 重疊固定語: 叮叮噹噹、含含糊糊、安安穩穩、實實在在、忙忙碌碌、是是非非、跌跌撞撞、彼此彼此
- ABAC 對舉俗語／熟語: 一夫一妻、傻頭傻腦、大喊大叫、徒子徒孫、有名有姓、木口木面、本鄉本土、活龍活現、滑頭滑腦、無仇無怨、老夫老妻、雙宿雙飛、何德何能、全始全終…
- 之字格固定: 大將之風、好事之徒、有婦之夫
- AABC: 上上之策、奄奄一息、朗朗上口、竊竊私語、耿耿於懷、面面相覷

## Error patterns (BAD)

1. **ABAC 假陽 · 政策／技術並列 NP** (1/1) — `統A統B` 命中 ABAC，但是計劃經濟術語，非固定說法 → clear `family`

## Gate / apply note

- BAD 1 條：`fix_family` 空 → `audit-apply` 會清 `family=idiom`
- SOFT 5 條：保留 `family=idiom`（傘形 熟語 可）
- 本輪 **PASS**；ABAC 啓發式可考慮排除明顯政策／制度並列（統購統銷類）若後續 round 再收假陽
