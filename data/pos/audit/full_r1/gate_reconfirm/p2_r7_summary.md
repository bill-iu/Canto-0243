# P2 gate reconfirm r7 — high-trust 熟語

**File:** `data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r7.tsv`  
**Round:** 7（post revert bulk `zhi-n-fix` + re-apply audited fixes only）  
**Threshold:** ok_rate = (OK+SOFT)/n **> 0.90**  
**Scope:** high-trust 熟語 ∩ gate；rules: n/v/a/r/x/u；particles→x；stative→a；multi only if both common；family 真熟語留 idiom

## Result

| verdict | n | % |
|---------|--:|---:|
| OK | 49 | 98% |
| SOFT | 0 | 0% |
| BAD | 1 | 2% |

**ok_rate = 49/50 = 0.9800 → PASS**（> 0.90）

## BAD — 全部（family 皆真熟語，留 idiom；只修 pos）

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 召之即來 | n | v | zhi-n-revert 過修；謂語成語（召之即來揮之即去）；r6 曾 OK v；n 假陽會毒同名詞閘 |

## Error patterns

1. **`zhi-n-revert` 過寬 · 真謂語一併回 n**（1/1 BAD）— bulk revert 撤銷錯誤 `zhi-n-fix` 時，把 **已正確** 的謂語之字格也打回 n。本抽樣僅 `召之即來`（對照 r6 OK v／`置之不理` 類）。
2. **audited re-apply／restore 確認 OK**（本抽樣）：
   - r6 名物回 n：`一國之主`、`女流之輩`、`斷袖之癖`、`牢獄之災`
   - r5 名物回 n：`一線之隔`、`天壤之別`
   - r4 stative→a：`取之不盡`
   - r2 謂語→v：`受之有愧`
   - r1 AABB→a：`恩恩愛愛`
   - `zhi-n-restore`：`一臂之力`／`一面之詞`／`不實之詞`／`浩然之氣`／`片面之詞`／`自然之友`／`音樂之聲`
3. **`zhi-n-revert` 正確保留名物 n**（本抽樣）：`一面之緣`、`不祧之祖`、`喪家之犬`、`必由之路`、`經驗之談`、`覆盆之冤`、`養身之道`、`十之八九`（比例名物；副用可兼）
4. **謂語／stative／AABB 本輪無假陽**：`為之動容` v、`趨之若鶩` v、`一瘸一拐` v、`取之不盡` a、`健健康康` a、`從從容容` a,r 等。
5. **未誤修真名物 OK**：`一席之地`／`一面之交`／`立錐之地`／`肺腑之言`／`血肉之軀` 等。

## Family

- 本批 50 條 **無假陽 熟語**（fix_family 無需清空）。
- 真名物之字格留 n；謂語之字格留 v；stative 留 a；AABB／ABAC 已標主類。
- **revert 白名單勿含真謂語**：`X之即Y`（召之即來）、`置之`／`處之`／`為之`／`求之不得`／`趨之若鶩` 等。

## Apply note

`project_pos_audit apply` 本 TSV 1 列 BAD（`fix_pos=v`；family 保持 idiom）後，本抽樣 ok_rate 可升至 **1.00**。

**優先：** 修窄 `zhi-n-revert` — 掃 high-trust ∩ `family=idiom` ∩ note 含 `zhi-n-revert` ∩ `pos=n`，只對 **仍為動核謂語** 者回 `v`：
- `召之即來`／`X之即Y` 類
- 勿再動真名物頭（主／祖／犬／路／談／冤／道／緣／詞／氣…）

```text
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r7.tsv --dry-run
```
