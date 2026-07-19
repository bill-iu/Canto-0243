# P2 gate reconfirm r2 — high-trust 熟語

**File:** `data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r2.tsv`  
**Round:** 2（seed 20260721；universe 328；n=50）  
**Threshold:** ok_rate = (OK+SOFT)/n **> 0.90**  
**Scope:** high-trust 熟語 ∩ gate；rules: n/v/a/r/x/u；particles→x；stative→a；multi only if both common；family 真熟語留 idiom

## Result

| verdict | n | % |
|---------|--:|---:|
| OK | 45 | 90% |
| SOFT | 0 | 0% |
| BAD | 5 | 10% |

**ok_rate = 45/50 = 0.9000 → FAIL**（需 > 0.90；本輪恰 = 0.90 未過）

## BAD — 全部（family 皆真熟語，留 idiom；只修 pos）

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 受之有愧 | n | v | 之字格假陽 n；謂語成語／謙辭 |
| 急人之難 | n | v | 之字格假陽 n；謂語成語「急人之所難」 |
| 持之有故 | n | v | 之字格假陽 n；謂語成語（持之有故，言之成理） |
| 言之有據 | n | v | 之字格假陽 n；謂語成語 |
| 隨之而來 | n | v | 之字格假陽 n；謂語／後接短語 |

## Error patterns

1. **之字格假陽 n on 謂語**（5/5 BAD）— `len4-noun-heuristic` + `p2-idiom:之字格` 把 VP 成語標成 n；同 r1 已修類：`求之不得`→v、`言之尚早`→v、`趨之若鶩`→v、`拒之門外`→v。
2. **本輪無 AABB `u` 欠標** — r1 主要殘留類已不在本 seed 抽樣（或已修）。
3. **已修確認 OK**（本抽樣）：`忽然之間` r、`拒之門外` v、`言之尚早` v、`趨之若鶩` v、`除此之外` r、`中規中矩` a、`無影無蹤` a。

## Family

- 本批 50 條 **無假陽 熟語**（fix_family 無需清空）。
- 時間名物之字格（`一夕之間`／`俯仰之間`）主標 n 可接受（對照 r1 `一念之間` OK；有別於純副 `忽然之間`→r）。

## Apply note

`project_pos_audit apply` 本 TSV 5 列 BAD（`fix_pos=v`；family 保持 idiom）後，本抽樣 ok_rate 可升至 **1.00**。

建議另掃 high-trust ∩ `family=idiom` ∩ `pos=n` ∩ note 含 `之字格`，批量覆核謂語／副成語（`X之Y` 非名物頭）。

```text
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r2.tsv --dry-run
```
