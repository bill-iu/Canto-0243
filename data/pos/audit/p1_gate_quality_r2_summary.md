# P1 gate POS quality audit (r2)

**Sample:** `data/pos/audit/p1_gate_quality_r2.tsv` (n=50)  
**Universe:** 735 P1 mother-body literals with 閘用詞類  
**Seed:** 202607192（獨立於 r1）  
**Threshold:** ok_rate ≥ 0.90  
**Date:** 2026-07-19  
**Prior:** r1 ok_rate 0.92；r1 四條 BAD 已 apply

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 46 | 92% |
| SOFT | 0 | 0% |
| BAD | 4 | 8% |
| **total** | **50** | 100% |

**ok_rate = (OK+SOFT)/n = 46/50 = 0.92**

**PASS** (0.92 ≥ 0.90)

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 呆 | a,v | a | stative 形；v 假陽會毒同動詞閘 |
| 正 | a,r,x | a,r | 形＋副常見（好正／正係）；x 假陽會毒同虛詞閘 |
| 相 | a,n,v | n | 自由詞主要係名「相／影相」；a/v 假陽會毒同形／動詞閘 |
| 相信 | n,v | v | 只係動；n 假陽會毒同名詞閘 |

## SOFT

（無）

## OK patterns worth keeping

- Clear n / 專名：下身、小貞、謙謙、身上、阿南、電話
- Clear v / V+suffix / 情態：不敢、值得、做、做好、到手、失戀、成爲、拖住、搣、留
- Clear a / r：叻、幾好、淺、的確
- Closed-class x / multi-x：之、以、或、所、由、萬、誒、邊度；之前／亦 `r,x`；係咪／可／多謝／把／晒 `v,x`；下下 `r,x`；啱 `a,v`；情願 `a,v`；忙 `a,n`；一刻 `n,r`
- True n,v duals：希望、支持、放棄、進步、道歉、選擇

## Error patterns (BAD)

1. **假陽 multi 過寬** (4/4)
   - cow-multi：呆 `a,v` → 只 a（stative）
   - true-nv 白名單過寬：相信 `n,v` → 只 v
   - canto-heuristic 單字過標：正 多 x；相 多 a/v → 收斂主用

## Gate impact note

本批全部為 **閘用詞類**（high／medium）。4 條 BAD 會令同詞性硬閘假陽相交：假 v（呆）／假 n（相信）／假 x（正）／假 a+v（相）。優先 `project_pos_audit apply` 本 TSV 四列後，閘用品質可再升。

## Confirm pass

獨立抽樣 r2 與 r1 皆 **ok_rate = 0.92 ≥ 0.90** → **確認 P1 閘用詞類品質門檻通過**（殘留 BAD 為可批次修補之假 multi，非系統性主標崩潰）。
