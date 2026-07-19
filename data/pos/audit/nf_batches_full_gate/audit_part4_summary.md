# nf_batches_full_gate POS quality audit — part4

**File:** [`audit_part4.tsv`](audit_part4.tsv)  
**Batch:** `u-inlex-nf4` · n=100  
**Rules:** `n/v/a/r/x`；multi only if both common；wrong→BAD+`fix_pos`；borderline→SOFT  
**Date:** 2026-07-19  

## Counts

| verdict | n | % |
|---------|--:|---:|
| OK | 97 | 97% |
| SOFT | 1 | 1% |
| BAD | 2 | 2% |
| **total** | **100** | 100% |

**ok_rate = (OK+SOFT)/n = 98/100 = 0.98**

**PASS** (0.98 ≥ 0.90)

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 大有文章 | a,n | a | stative 謂語形；n 假陽（同 滿意 a,n→a／別有用心 a） |
| 音訊全無 | a,v | a | stative 形（同 杳無音訊 a）；v 假陽會毒同動詞閘 |

## SOFT

| literal | pos | note |
|---------|-----|------|
| 放不下心 | a,v | 主標 v；a 由定語化邊緣，multi 可留閘 |

## OK patterns worth keeping

- **Clear n / 專名／書名／器物：** 七言絕句、乘龍快婿、十三太保、博客寫手、參考材料、可移植性、向巴平措、國際法院、城市熱島、多國部隊、多重人格、奇風異俗、心腹大患、急性腸炎、成語典故、戰術導彈、文學巨匠、春秋時代、格蘭芬多、樂府詩集、樑上君子、民間習俗、油料作物、滔天大罪、獨立思想、現在分詞、理學博士、生日卡、空氣阻力、糖醋里脊、終生伴侶、聖盧西亞、自動鉛筆、良辰吉日、薩摩耶犬、蘇打餅乾、超前意識、軍事顧問、通用電器、遠洋漁業、野戰部隊、金髮女郎、門牌號碼、隋唐演義、骨牌效應、黑芝麻糊、弗蘭西斯
- **Clear v / 成語謂語：** 一親芳澤、不予置評、俯首稱臣、兄弟鬩牆、匍匐前進、含笑九泉、好言相勸、寬以待人、恢復常態、排起長隊、揚名立萬、收買人心、改弦易轍、沾不上邊、消聲匿跡、直搗黃龍、與民同樂、虛席以待、衝口而出、謹言慎行、迷途知返、面授機宜
- **Clear a / stative 成語：** 人心叵測、人心難測、公私分明、名不符實、心中有鬼、文筆流暢、毫無效果、氣度不凡、波譎雲詭、舟車勞頓、衣不蔽體、貌不驚人、餘情未了、魂不附體
- **Clear r：** 平心而論
- **True dual multi：** 停薪留職 `n,v`；威震天下／寧缺勿濫／故步自封／無處可尋／立杆見影／胸懷大志／身懷六甲 `a,v`；立身處世／野外求生 `n,v`；陰盛陽衰 `a,n`；天打雷劈 `v,x`（動／咒罵語氣）

## Error patterns (BAD)

1. **假陽 multi 過寬** (2/2)
   - stative 成語加假 n：`大有文章` a,n → a
   - stative 成語加假 v：`音訊全無` a,v → a（對齊 `杳無音訊` a）

## Gate impact note

本批全部為 **high-trust 閘用**（`u-inlex-nf4;review;agent-label`）。2 條 BAD 會令同詞性硬閘假陽相交：假 n（大有文章）／假 v（音訊全無）。SOFT 1 條可留閘。優先 `project_pos_audit apply` 本 TSV 兩列 BAD 後，本抽樣 ok_rate 可升至 **0.99–1.00**。

## Files

| path | role |
|------|------|
| `data/pos/audit/nf_batches_full_gate/audit_part4.tsv` | filled verdicts (overwrite) |
| `data/pos/audit/nf_batches_full_gate/audit_part4_summary.md` | this summary |
