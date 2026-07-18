# P3 gate POS quality audit (r1)

**Sample:** `data/pos/audit/p3_gate_quality_r1.tsv` (n=50)  
**Universe:** 546 P3 (Essay ranks 5001–20000) literals with 閘用詞類  
**Seed:** 20260719  
**Threshold:** ok_rate > 0.90  
**Date:** 2026-07-19

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 44 | 88% |
| SOFT | 0 | 0% |
| BAD | 6 | 12% |
| **total** | **50** | 100% |

**ok_rate = (OK+SOFT)/n = 44/50 = 0.88**

**FAIL** (0.88 ≯ 0.90)

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 受山 | v | u | 切詞假陽（受山火等）；非獨立被動動詞 |
| 呆滯 | n,v | a | stative 形；n/v 假陽會毒閘 |
| 提供服務 | n | v | VO「提供+服務」，非名詞；n 假陽會毒同名詞閘 |
| 斷斷續續 | n | a,r | AABB 狀態／情狀；非名（cow-single n 假陽） |
| 減輕 | n,v | v | 只係動；n 假陽會毒同名詞閘 |
| 遵守 | n,v | v | 只係動；n 假陽會毒同名詞閘 |

## SOFT

（無）

## OK patterns worth keeping

- Clear n / len4 compounds: 三分之一、主營業務、人之常情、使用方法、信息中心、各級政府、售後服務、地方政府、培訓中心、專業技術、手提電話、新聞中心、日本政府、服務機構、百貨公司、知識分子、系列產品、諮詢服務、諮詢機構、部分地區、醫療機構、關鍵技術
- Clear v / V+suffix / passive: 低開、問完、搭住、照住、睇開、禁住、趕住、受影響、被困、被騙
- Clear a / r / x: 光明 `a,n`、稍後 `r`、十一五 `x`
- True n,v duals: 交易、保釋、奉獻、搖擺、敗壞、發熱、腐爛、蒸發、購物

## Error patterns (BAD)

1. **cow-multi 假陽 n on pure v / stative** (3/6)
   - 減輕、遵守 → 只 v
   - 呆滯 → 只 a（stative）
2. **len4-noun 假陽 n on VO** (1/6)
   - 提供服務 → v
3. **cow-single + idiom 假陽 n on AABB 情狀** (1/6)
   - 斷斷續續 → a,r
4. **prefix-passive 切詞假陽** (1/6)
   - 受山 → u（非獨立被動動詞）

## Gate impact note

本批全部為 **閘用詞類**（high／medium）。6 條 BAD 會令同詞性硬閘假陽相交：假 v（受山）／假 n（提供服務、減輕、遵守、斷斷續續）／假 n+v（呆滯）。優先 `project_pos_audit apply` 本 TSV 六列後再 round-2 抽樣。

## Confirm pass

**未過門檻**：ok_rate **0.88 ≯ 0.90** → **P3 閘用詞類品質閘 r1 FAIL**；需修 BAD 後重抽 r2。
