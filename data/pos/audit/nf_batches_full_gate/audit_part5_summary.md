# nf_batches_full_gate POS quality audit — part5

**File:** `data/pos/audit/nf_batches_full_gate/audit_part5.tsv`  
**Batch:** `u-inlex-nf5`  
**n:** 86  
**Range:** `一枕黃粱`…`鰥寡孤獨`  
**Date:** 2026-07-19  

**Rules:** `n/v/a/r/x`；multi 僅兩棲皆常見；錯標 → BAD+`fix_pos`； borderline → SOFT；SOFT 計入 ok_rate。

## Counts

| verdict | n | % |
|---------|--:|---:|
| OK | 79 | 91.9% |
| SOFT | 2 | 2.3% |
| BAD | 5 | 5.8% |
| **total** | **86** | 100% |

**ok_rate = (OK+SOFT)/n = 81/86 = 0.9419**

**PASS** (0.9419 ≥ 0.90)

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 一枕黃粱 | n,v | n | 成語主作名詞（黃粱夢喻／是一枕黃粱）；v 假陽 |
| 久病成醫 | a,x | v | 謂語成語（真係久病成醫）；非形／非 x |
| 互有勝負 | a,v | v | 主作謂語（雙方互有勝負）；a 假陽 |
| 同工異曲 | a,n | a | 成語主形容（異曲同工之妙）；n 假陽 |
| 白日見鬼 | v,x | v | 動詞成語；x 假陽（非 closed-class） |

## SOFT（primary 可留，升 trust 宜補／留意）

| literal | pos | note |
|---------|-----|------|
| 名聲遠播 | a,v | 主標動謂；定語 a 薄但閘用 multi 可 |
| 年底 | n | 時間詞常作狀語（年底完成／年底見），宜 n,r |

## OK patterns worth keeping

- Clear n / 專名／學科 NP：侍應生、原子半徑、可再生能源、合成石油、地區差價、娑羅雙樹、年度大會、標題音樂、毛毛雨、烏魯木齊、理化因素、理論貢獻、相對速度、統一資源、菲力牛排、西部、輕機關槍、銅管樂器、陳橋兵變、平地
- Clear v / 成語動：不平則鳴、付諸流水、以儆效尤、削足適履、姑息養奸、小試牛刀、惡言傷人、挖肉補瘡、掂斤播兩、撫躬自問、旋轉乾坤、有失、棄邪歸正、知情不報、破案、破舊立新、窮追猛打、縱情聲色、見風是雨、賣身投靠、退燒、遇害、避坑落井、鋤強扶弱、防風固沙、養家活口、凋謝、耗
- Clear a / 成語形：不當、出神入化、動魄驚心、可親、單調、嗜殺成性、心平氣和、氣息奄奄、福壽雙全、綽約多姿、芙蓉出水、荒淫無恥、金碧輝煌、陰鬱、驚愕
- Clear r：否、成年累月
- True multi：一觸即潰 `a,v`、五花大綁 `n,v`、停火 `n,v`、勞碌 `a,v`、整天 `n,r`、登報聲明 `n,v`、萬死一生 `a,n`
- Idiom n：管窺所及、貓鼠遊戲、雄心壯志、風吹草動、鰥寡孤獨

## Error patterns (BAD)

1. **假陽 multi 第二標** (4/5) — agent-label 過寬  
   - 一枕黃粱：假 v（應只 n）  
   - 互有勝負：假 a（應只 v）  
   - 同工異曲：假 n（應只 a）  
   - 白日見鬼：假 x（應只 v）
2. **錯主類 a,x on 謂語成語** (1/5)  
   - 久病成醫 → v

## Gate impact note

本批全部 `trust=high` 閘用標。5 條 BAD 會毒同詞性硬閘：假 v（一枕黃粱）／假 a（互有勝負、久病成醫）／假 n（同工異曲）／假 x（白日見鬼）。優先 `project_pos_audit apply` BAD 五列後再併 batch 級 gate。

## Files

| path | role |
|------|------|
| `data/pos/audit/nf_batches_full_gate/audit_part5.tsv` | 86 列已填 verdict（overwrite） |
| `data/pos/audit/nf_batches_full_gate/audit_part5_summary.md` | 本摘要 |
