# P3 gate POS quality audit (r2)

**Sample:** `data/pos/audit/p3_gate_quality_r2.tsv` (n=50)  
**Universe:** 545 P3 (Essay ranks 5001–20000) literals with 閘用詞類  
**Seed:** 202607192（獨立於 r1）  
**Threshold:** ok_rate > 0.90  
**Date:** 2026-07-19  
**Prior:** r1 ok_rate 0.88 FAIL；r1 六條 BAD 已標（本 r2 含已修之 斷斷續續 `a,r`）

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 45 | 90% |
| SOFT | 1 | 2% |
| BAD | 4 | 8% |
| **total** | **50** | 100% |

**ok_rate = (OK+SOFT)/n = 46/50 = 0.92**

**PASS** (0.92 > 0.90)

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 南開 | v | n | 專名／校名（南開大學等）；verb-suffix 開 假陽會毒同動詞閘 |
| 廢除 | n,v | v | 只係動；n 假陽會毒同名詞閘 |
| 經商 | n,v | v | 只係動；n 假陽會毒同名詞閘 |
| 被害人 | v | n | 受害人／受害者義，名詞；prefix-passive 假陽會毒同動詞閘 |

## SOFT（multi 可留閘，主標略偏）

| literal | pos | note |
|---------|-----|------|
| 食住 | v | 主標動可；名『食宿』義（包食住）常見，升 trust 宜補 n |

## OK patterns worth keeping

- Clear n / len4 compounds: 中山大學、主營業務、人類社會、信息技術、原因之一、專家學者、當地政府、相關部門、科學技術、管理模式、詳細資料、諮詢服務
- Clear v / V+suffix / passive: 勾起、受益、因住、改掉、爆開、癡住、縮開、聽完、被盜、被迫、被逼、頂住、顧住
- Clear a / r / x: 斷斷續續 `a,r`、稍後 `r`；numerals 一百萬／二十／五萬／十九／億萬 `x`
- Reviewed multi: 向上 `v,x`
- True n,v duals: 中斷、估價、剝離、實踐、幹、批准、擴散、統一、航海、複查、辯論、遷移

## Error patterns (BAD)

1. **cow-multi 假陽 n on pure v** (2/4)
   - 廢除、經商 → 只 v
2. **verb-suffix 假陽 v on 專名** (1/4)
   - 南開 → n（開 非動趨）
3. **prefix-passive 假陽 v on 名詞** (1/4)
   - 被害人 → n（對照 r1 被人／受山 類）

## Gate impact note

本批全部為 **閘用詞類**（high／medium）。4 條 BAD 會令同詞性硬閘假陽相交：假 v（南開、被害人）／假 n（廢除、經商）。優先 `project_pos_audit apply` 本 TSV 四列後，閘用品質可再升。

## Confirm pass

獨立抽樣 r2 **ok_rate = 0.92 > 0.90**（r1 為 0.88 FAIL）→ **確認 P3 閘用詞類品質門檻通過**（殘留 BAD 為可批次修補之假 multi／假前綴，非系統性主標崩潰）。
