# u_pattern S2 gate r1

**Sample:** `u_pattern_s2_gate_r1.tsv` (n=3 = full universe)  
**Threshold:** ≥0.90  

## Counts

| verdict | n |
|---------|--:|
| OK | 2 |
| BAD | 1 |
| **ok_rate** | **0.667** |

Universe only 3 rows after prior campaigns exhausted AABB／ABAC／… — **batch too small for 90% campaign gate**; treated as **full audit** of S2 yield.

## BAD

| literal | fix | reason |
|---------|-----|--------|
| 電解電容 | n, family 空 | 技術並列 NP；p2 曾 clear；唔入熟語 |

## OK

全心全意 · 數一數二  

## Manual add

| literal | pos | note |
|---------|-----|------|
| 統購統銷 | n | 政策術語；idiom_pattern 刻意排除；仍 u → formal n |

## S2 takeaway

- `u_repair` dry-run：**0** new（規則位已清）  
- 模式熟語 still-u：**3** ABAC → 2 OK + 1 BAD fix  
- 餘 ~6.5k 非 fragment 四字 `u` 多為「一刀兩斷」類固定語／書面詞，**唔再係 cheap pattern** → 下一刀 Essay 非 fragment agent 標  
