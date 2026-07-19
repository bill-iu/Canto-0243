# P1 medium|gate POS audit summary

**Sample:** `data/pos/audit/p1_sample_medium_gate.tsv` (n=50)  
**Stratum:** medium|gate — mostly `cow-multi`；入硬閘／同桶，**唔**作創作者主展示  
**Date:** 2026-07-18

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 38 | 76% |
| SOFT | 2 | 4% |
| BAD | 10 | 20% |
| **total** | **50** | 100% |

**Gate pass rate (OK+SOFT):** 40/50 = **80%**（< 90% 批級門檻）

## Top error patterns (BAD)

1. **假陽 `n` on pure verb / adj+verb** — **6/10 BAD**  
   COW `n,v` 把非名詞塞入名，毒同名詞閘：
   - 只係動：值得、切、拉 → **v**
   - 形＋動：專心、深入 → **a,v**

2. **假陽 `v` on pure noun / adj+noun** — **3/10 BAD**  
   - 偵探 → **n**（動義用「偵查」）
   - 電話 → **n**（口語動邊緣）
   - 必要 → **a,n**（非動）

3. **錯主類組合** — **1/10 BAD**  
   - 中 `a,n` → **n,v**（自由形弱；補動「中獎／中計」）
   - 類似 `n,v` → **a,v**（形／類似於，非名）— 計上 pattern 1/2 交界

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 中 | a,n | n,v | 自由形弱；名＋動「中獎／中計」 |
| 值得 | n,v | v | 只係動（值得+VP） |
| 偵探 | n,v | n | 名；v 假陽 |
| 切 | n,v | v | 自由詞只係動 |
| 專心 | n,v | a,v | 形＋動，非名 |
| 必要 | n,v | a,n | 形＋名，非動 |
| 拉 | n,v | v | 只係動 |
| 深入 | n,v | a,v | 形＋動，非名 |
| 電話 | n,v | n | 名；v 邊緣 |
| 類似 | n,v | a,v | 形／類似於，非名 |

## SOFT（multi 可留閘，主標略偏）

| literal | pos | note |
|---------|-----|------|
| 提供 | n,v | 主標動；名物化 n 薄，閘用 multi 可 |
| 迎接 | n,v | 主標動；名用薄，閘用 multi 可 |

## OK patterns worth keeping

- 經典名動兩棲：交換、交流、保證、傷害、利用、命令、希望、感覺、打算、申請、破壞、解釋、選擇、變化、轉變…
- 真歧義雙類：制服（衣／ subdu e）、圈、數、派、遊戲、講話、滑雪
- family／voice 全空 — 普通詞正確（非熟語、非語態對）

## Gate impact note

本層全部 **medium** 信任、`cow-multi`，已入 **閘用詞類**。假陽 `n` 令純動／形詞誤與名詞同桶；假陽 `v` 令名詞誤與動詞同桶。COW 多標對真名動兩棲大致可靠，錯批集中在：**非名物化動詞**、**形／副誤標 n,v**、**純名誤加 v**。優先修正上表 10 列後再 `project_pos_audit apply`。
