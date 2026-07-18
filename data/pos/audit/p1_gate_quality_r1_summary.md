# P1 gate POS quality audit (r1)

**Sample:** `data/pos/audit/p1_gate_quality_r1.tsv` (n=50)  
**Universe:** 735 P1 mother-body literals with 閘用詞類  
**Seed:** 20260719  
**Threshold:** ok_rate ≥ 0.90  
**Date:** 2026-07-19

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 45 | 90% |
| SOFT | 1 | 2% |
| BAD | 4 | 8% |
| **total** | **50** | 100% |

**ok_rate = (OK+SOFT)/n = 46/50 = 0.92**

**PASS** (0.92 ≥ 0.90)

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 價值 | n,v | n | 只係名；v 假陽會毒同動詞閘 |
| 包括 | n,v | v | 只係動；n 假陽會毒同名詞閘 |
| 滿意 | a,n | a | stative 形；n 假陽會毒同名詞閘 |
| 被人 | v | x | 被+人施事短語／被動標記，非獨立動 |

## SOFT（multi 可留閘，主標略偏）

| literal | pos | note |
|---------|-----|------|
| 出席 | n,v | 主標動；名物化 n 薄但閘用 multi 可 |

## OK patterns worth keeping

- Clear n: 一拳、下身、同人、回覆日期、家姐、幼稚園、床、社會主義、符紙
- Clear v / V+suffix: 傾下、加上、嚟、夾住、接住、搞
- Clear a / r: 淺、開心、即刻、太、很、更、的確、非常
- Closed-class x / multi-x: 二、八、丫、並 `r,x`、仲 `r,x`、冇 `v,x`、小 `a,x`、果 `n,x`、離 `v,x`
- True n,v duals: 出口、失敗、懷疑、放棄、檢查、準備、破壞、突破、紀念、組織、道
- Reviewed multi: 好 `a,r`、必要 `a,n`

## Error patterns (BAD)

1. **假陽 n/v on pure single-class** (3/4) — COW/`true-nv` 升格過寬  
   - 價值 → 只 n  
   - 包括 → 只 v  
   - 滿意 → 只 a（stative 留 a）
2. **被動前綴假陽 v** (1/4) — 被人 非獨立動詞 → x

## Gate impact note

本批全部為 **閘用詞類**（high／medium）。4 條 BAD 會在同詞性硬閘／同桶交集產假陽：假 v 與真動詞相交、假 n 與真名詞相交、被人 當 v 與真動詞相交。優先改上表 4 列後再 round-2 抽樣。
