# P3 gate POS quality audit (r3)

**Sample:** `data/pos/audit/p3_gate_quality_r3.tsv` (n=50)  
**Universe:** 545 P3 (Essay ranks 5001–20000) literals with 閘用詞類  
**Seed:** 202607193（獨立於 r1／r2）  
**Threshold:** ok_rate > 0.90  
**Date:** 2026-07-19  
**Prior:** r1 ok_rate 0.88 FAIL；r2 ok_rate 0.92 PASS；r2 BAD 已見修補（本 r3 含已修之 廢除 `v`）

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 46 | 92% |
| SOFT | 0 | 0% |
| BAD | 4 | 8% |
| **total** | **50** | 100% |

**ok_rate = (OK+SOFT)/n = 46/50 = 0.92**

**PASS** (0.92 > 0.90)

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 一五一十 | x | r | 情狀／方式副（一五一十噉講）；非數詞（numeral 假陽會毒同虛詞閘） |
| 不完 | v | u | 否定+完；非獨立動詞（verb-suffix 假陽，多見於 V 不完） |
| 被告人 | v | n | 法律名詞「被告一方」；prefix-passive 假陽會毒同動詞閘（對照 r2 被害人） |
| 除此之外 | n | r | 連接／附帶說明短語；非名（len4-noun 假陽會毒同名詞閘） |

## SOFT

（無）

## OK patterns worth keeping

- Clear n / len4 compounds: 一些問題、世界經濟、中國社會、什麼問題、信息技術、具體情況、各級政府、售後服務、廣告公司、循環經濟、技術服務、投資公司、操作系統、生產成本、百貨公司、研究中心、社會經濟、突出問題、資本市場、購物中心
- Clear v / V+suffix: 咬住、喫掉、因住、彈開、抽住、挨住、新開、照住、陪住；已修 pure-v 廢除
- Clear a / r / x: 稍後 `r`；numerals 兩百／十二 `x`
- True n,v duals / reviewed multi: 下降、侵犯、償還、回扣、團結、培養、抨擊、支配、減弱、犯罪、貢獻、遊覽、釋放

## Error patterns (BAD)

1. **numeral 假陽 x on 情狀成語** (1/4)
   - 一五一十 → r
2. **verb-suffix 假陽 v on 否定+完** (1/4)
   - 不完 → u
3. **prefix-passive 假陽 v on 被X人 名詞** (1/4)
   - 被告人 → n（同 r2 被害人）
4. **len4-noun 假陽 n on 連接短語** (1/4)
   - 除此之外 → r

## Gate impact note

本批全部為 **閘用詞類**（high／medium）。4 條 BAD 會令同詞性硬閘假陽相交：假 x（一五一十）／假 v（不完、被告人）／假 n（除此之外）。優先 `project_pos_audit apply` 本 TSV 四列後，閘用品質可再升。r2 已修之 廢除 本輪抽中為 **OK**。

## Confirm pass

獨立抽樣 r3 **ok_rate = 0.92 > 0.90**（r2 亦 0.92 PASS；r1 0.88 FAIL）→ **確認 P3 閘用詞類品質門檻通過**（殘留 BAD 為可批次修補之假 numeral／假 suffix／假被動前綴／假 len4-n，非系統性主標崩潰）。
