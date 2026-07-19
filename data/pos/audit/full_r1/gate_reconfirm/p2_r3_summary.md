# P2 gate reconfirm r3 — high-trust 熟語

**File:** `data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r3.tsv`  
**Round:** 3  
**Threshold:** ok_rate = (OK+SOFT)/n **> 0.90**  
**Scope:** high-trust 熟語 ∩ gate；rules: n/v/a/r/x/u；particles→x；stative→a；multi only if both common；family 真熟語留 idiom

## Result

| verdict | n | % |
|---------|--:|---:|
| OK | 43 | 86% |
| SOFT | 0 | 0% |
| BAD | 7 | 14% |

**ok_rate = 43/50 = 0.8600 → FAIL**（需 > 0.90）

## BAD — 全部（family 皆真熟語，留 idiom；只修 pos）

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 一時之間 | n | r | 之字格假陽 n；純副時間框架（同忽然之間） |
| 少之又少 | n | a | 之字格假陽 n；謂語 stative「極少」＝形（同來之不易） |
| 悔之晚矣 | n | v | 之字格假陽 n；謂語成語／套語 |
| 略識之無 | n | a | 之字格假陽 n；謂語 stative「識字不多」＝形 |
| 相比之下 | n | r | 之下格假陽 n；比較連接／附帶副（同除此之外） |
| 置之度外 | n | v | 之字格假陽 n；謂語成語（同拒之門外） |
| 言之有理 | n | v | 之字格假陽 n；謂語成語（同言之有據／言之成理） |

## Error patterns

1. **之字格／之下格假陽 n on 謂語／副／stative**（7/7 BAD）— `len4-noun-heuristic` + `p2-idiom:之字格` 把非名物頭成語標成 n。
   - **謂語 v**（3）：`悔之晚矣`、`置之度外`、`言之有理` — 同 r1/r2 已修類 `求之不得`／`拒之門外`／`言之有據`／`言之成理`。
   - **stative a**（2）：`少之又少`、`略識之無` — 同 r1 `來之不易`→a。
   - **副／連接 r**（2）：`一時之間`、`相比之下` — 同 `忽然之間`→r、`一氣之下`→r、`除此之外`→r。
2. **本輪無 AABB `u` 欠標** — r1 主殘留類已清（本抽樣 `孤孤單單`／`層層疊疊`／`恩恩愛愛` 等已 a）。
3. **已修確認 OK**（本抽樣）：`一氣之下` r、`忽然之間` r、`除此之外` r、`彬彬有禮` a、`無影無蹤` a、`無法無天` a、AABB 批 a/a,r/v。

## Family

- 本批 50 條 **無假陽 熟語**（fix_family 無需清空）。
- 真名物之字格（`一臂之力`／`後起之秀`／`殺身之禍`／`言下之意`／`門户之見` 等）主標 n 正確。
- 時間跨度 NP（`一年四季`）n 可；有別於純副框架 `一時之間`／`忽然之間`→r。

## Apply note

`project_pos_audit apply` 本 TSV 7 列 BAD（`fix_pos` 已填；family 保持 idiom）後，本抽樣 ok_rate 可升至 **1.00**。

建議另掃 high-trust ∩ `family=idiom` ∩ `pos=n` ∩ note 含 `之字格`，批量覆核：
- 謂語／套語（`X之Y` 動核，非名物頭）→ v
- stative 謂語 → a
- `之下`／`之間` 純副／連接 → r

```text
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r3.tsv --dry-run
```
