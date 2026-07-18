# nf_batches_full_gate POS quality audit — part3

**Sample:** `data/pos/audit/nf_batches_full_gate/audit_part3.tsv` (n=100)  
**Batch / universe:** `u-inlex-nf3`（Essay top-2000 non-fragment formal · universe 1999）  
**Threshold:** ok_rate = (OK+SOFT)/n ≥ 0.90  
**Date:** 2026-07-19  
**Rules:** n/v/a/r/x；multi only if both common；wrong → BAD+`fix_pos`；borderline → SOFT

## Counts

| verdict | n | % |
|---------|--:|---:|
| OK | 97 | 97% |
| SOFT | 2 | 2% |
| BAD | 1 | 1% |
| **total** | **100** | 100% |

**ok_rate = (OK+SOFT)/n = 99/100 = 0.99**

**PASS** (0.99 ≥ 0.90)

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 隨時歡迎 | a,v | v | a 假陽；歡迎為動核，不受程度副修飾；套語亦偏 v |

## SOFT（borderline 可留閘）

| literal | pos | note |
|---------|-----|------|
| 捷報頻傳 | a,v | 主謂事件偏 v；a 定語薄可留閘 |
| 縱橫捭闔 | a,v | 主 v／權謀義；a 定語薄可留閘 |

## OK patterns worth keeping

- **Clear n / 名物／專名／術語：** 交感神經、勞動條件、參考消息、反式脂肪、司法制度、國際音標、地震預報、堂吉訶德、太僕寺旗、太陽電池、子宮頸癌、守恆定律、忌日、戰國時代、探明儲量、模擬信號、氣象預報、環氧乙烷、生產工具、皰疹病毒、社會青年、神龍汽車、稀土金屬、約束條件、絕代佳人、網絡語言、臨牀實驗、道德品質、醫學檢驗、長足進步、開發週期、高清晰度、麥田怪圈
- **Clear n idiom：** 前塵往事、天賜良緣、孤家寡人、心肝寶貝、金玉良言、金童玉女、音容笑貌、魚與熊掌
- **Clear v / v-idiom：** 一刀兩斷、全心投入、喜極而泣、坐井觀天、尋歡作樂、打草、把酒言歡、捷足先登、樂極生悲、止跌回升、矢口否認、知恩圖報、窮追不捨、羣雄逐鹿、自取其辱、自掏腰包、苦中作樂、行萬里路、誓不罷休、費盡心機、逼上梁山、遊戲人間、隨大流、首開紀錄
- **Clear a / a-idiom：** 動人心魄、口無遮攔、大腹便便、天寒地凍、心胸狹窄、殘缺不全、氣勢如虹、玉樹臨風、神通廣大、粗心大意、表裏不一
- **Clear r：** 一年到頭
- **True multi：** 一式兩份 `n,r`；亂成一團／倒背如流／呲牙咧嘴／山崩地裂／戰無不勝／招人喜歡／昏迷不醒／表露無遺／迷惑不解／魚死網破 `a,v`；平白無故 `a,r`；愛理不理／知趣 `a,v`；神經錯亂／鐵石心腸 `a,n`；科學普及／自我檢討 `n,v`；筆直 `a,r`；週末愉快 `a,x`（套語）

## Error patterns (BAD)

1. **假陽 a on r+v 套語** (1/1) — 隨時歡迎：程度副測試失敗，動核 歡迎 → 只 `v`

## Gate / apply note

- **修 pos 1 條**（`隨時歡迎` → `v`）→ 可 `project_pos_audit apply`
- SOFT 2 條：保留現標（不升不降）
- 本輪 **PASS**（ok_rate **0.99**）

## Files

| path | role |
|------|------|
| `data/pos/audit/nf_batches_full_gate/audit_part3.tsv` | 100 列已填 verdict（overwrite） |
| `data/pos/audit/nf_batches_full_gate/audit_part3_summary.md` | 本摘要 |
