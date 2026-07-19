# u_top3000 gate POS quality audit (r1)

**Sample:** `data/pos/audit/u_top3000_gate_r1.tsv` (n=132)  
**Universe:** newly promoted high-trust 閘用詞類 from Essay top-3000 `u`→POS (`stratum=u-top3000|gate`)  
**Threshold:** ok_rate = (OK+SOFT)/n **> 0.90** (strict)  
**Date:** 2026-07-19  
**Rules:** n/v/a/r/x；particles → x；stative → a；multi only if both common；essay fragments must not be formal → BAD+`fix_pos=u`

## Counts

| verdict | n | % |
|---------|--:|---:|
| OK | 121 | 91.7% |
| SOFT | 4 | 3.0% |
| BAD | 7 | 5.3% |
| **total** | **132** | 100% |

**ok_rate = (OK+SOFT)/n = 125/132 = 0.947**

**PASS** (0.947 > 0.90)

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 佈 | n,v | v | 主用動（佈置／分佈）；n 假陽會毒同名詞閘（名物多寫「布」） |
| 依加 | n,r | r | 依家＝而家 時間副；n 假陽會毒同名詞閘 |
| 所講 | n,v | n | 所V 名物化；只 n；v 假陽會毒同動詞閘 |
| 最好的 | a | u | 形+的 切段；非獨立詞位 |
| 請你 | v | u | 動+代 切段（同 問你／叫我） |
| 講句 | v | u | 動+量 切段（同 講個） |
| 講多次 | v | u | 動+副／量 切段（同 講多） |

## SOFT（borderline 可留閘）

| literal | pos | note |
|---------|-----|------|
| 好多嘢 | n | 短語型 NP「好多+嘢」；n 閘可 |
| 張床 | n | 量+名作 NP；essay 常見 n 閘可 |
| 絡 | n,v | 自由詞位薄（網絡／聯絡）；multi 閘可 |
| 錄 | v | 主標 v 可；名物「紀錄／名錄」可補 n |

## OK patterns worth keeping

- **Clear n / 專名／暱稱：** 冷衫、博客、地標、域名、外國、女友、尚健、新浪、河南、湖北、白波、米奇、蘭卡特、阿妹、阿婆、班主任、總經理、螢幕、行爲、觀衆、金字塔、馬甲、氣質、晚飯、神仙、聖誕…
- **Clear v / 粵語動／V+結果：** 做嘢、吹水、抌、郁、落街、放學、敲門、嚇死、打到、走到、食到、認得、知會、註明、構建、變得、訓教、擡高、恥笑
- **Clear a / stative：** 亂、大隻、好睇、嫩、易、暖、瘦
- **Clear r / 粵語副：** 一次過、仍、無幾耐、直程、近年來、頓時
- **Closed-class x / multi-x：** 一架／一臺／十個 `x`；呯 擬聲 `x`；是以／與其 `x`；不會／並無／得以／身爲 `v,x`；卻是／總係／正如／要不／幾耐 `r,x`；之際／內／號 `n,x`；關我事 `v,x`
- **True duals：** 不解 `a,v`、常 `a,r`、平 `a,n`、影／枕／摺／視 `n,v`、大部分／第一次／那天／面上 `n,r`、正面／異樣 `a,n`、淡淡 `a,r`、就行／齊 `a,v`、直落 `r,v`、身處 `n,v`

## Error patterns (BAD)

1. **essay 切段誤升 formal** (4/7) — 最好的、請你、講句、講多次 → `u`  
   （對齊 label policy：形+的／動+代／動+量 唔硬砌主標）
2. **假陽 multi 過寬** (3/7)  
   - 佈 `n,v` → 只 `v`（n 假陽）  
   - 依加 `n,r` → 只 `r`（n 假陽；依家）  
   - 所講 `n,v` → 只 `n`（v 假陽；所V 名物化）

## Apply note

- **修 pos 7 條**（皆有 `fix_pos`）→ `project_pos_audit apply`
- SOFT 4 條：保留現標（不升不降）
- 本輪 **PASS**（0.947 > 0.90）
- 後續 label／promote 可考慮：形+的、動+代、動+量 切段勿入閘；單字 multi 收斂主用（佈、依加／依家、所V）

```text
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/u_top3000_gate_r1.tsv --dry-run
```
