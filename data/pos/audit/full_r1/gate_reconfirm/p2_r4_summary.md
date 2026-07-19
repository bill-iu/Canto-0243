# P2 gate reconfirm r4 — high-trust 熟語

**File:** `data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r4.tsv`  
**Round:** 4（post bulk 之字格 n→v/r）  
**Threshold:** ok_rate = (OK+SOFT)/n **> 0.90**  
**Scope:** high-trust 熟語 ∩ gate；rules: n/v/a/r/x/u；particles→x；stative→a；multi only if both common；family 真熟語留 idiom

## Result

| verdict | n | % |
|---------|--:|---:|
| OK | 47 | 94% |
| SOFT | 0 | 0% |
| BAD | 3 | 6% |

**ok_rate = 47/50 = 0.9400 → PASS**（> 0.90）

## BAD — 全部（family 皆真熟語，留 idiom；只修 pos）

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 取之不盡 | n | a | 之字格假陽 n；謂語 stative「用之不竭」＝形（同來之不易） |
| 少之又少 | n | a | 之字格假陽 n；謂語 stative「極少」＝形（同 r3） |
| 行之有效 | n | a | 之字格假陽 n；謂語 stative「有效」＝形 |

## Error patterns

1. **之字格假陽 n on stative 謂語**（3/3 BAD）— bulk n→v/r 已清動／副殘留，但 `len4-noun-heuristic` 仍把 **形／stative** 成語標 n。
   - **stative a**（3）：`取之不盡`、`少之又少`、`行之有效` — 同 r1 `來之不易`→a、r3 `略識之無`→a。
2. **本輪無 AABB `u` 欠標** — full_r1／p1 已清（本抽樣 AABB／ABAC 皆 a／a,r／v）。
3. **bulk／先前修確認 OK**（本抽樣）：`忽然之間` r、`急人之難` v、`言之過早` v、`隨之而來` v。
4. **無 v/r 假陽 n 殘留** — 與 r2（5 BAD 全 v）／r3（7 BAD 含 v/r/a）對照，r4 bulk 後謂語動／副已對，只剩 stative a。

## Family

- 本批 50 條 **無假陽 熟語**（fix_family 無需清空）。
- 真名物之字格（`一字之差`／`七年之癢`／`傳家之寶`／`弦外之音`／`有識之士`／`長平之戰`／`點頭之交` 等）主標 n 正確。
- 時間／空間名物（`有生之年`／`眉宇之間`／`意料之中`／`意料之外`）n 可；有別於純副框架 `忽然之間`→r。

## Apply note

`project_pos_audit apply` 本 TSV 3 列 BAD（`fix_pos=a`；family 保持 idiom）後，本抽樣 ok_rate 可升至 **1.00**。

建議另掃 high-trust ∩ `family=idiom` ∩ `pos=n` ∩ note 含 `之字格`，批量覆核 **stative 謂語**（`X之不Y`／`X之又X`／`行之有效` 類非名物頭）→ a。

```text
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r4.tsv --dry-run
```
