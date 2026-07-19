# P2 gate reconfirm r8 — high-trust 熟語

**File:** `data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r8.tsv`  
**Round:** 8（second independent confirm；post r7 召之即來 n→v apply）  
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
| 眉宇之間 | r | n | zhi-n 過修 r；空間名物 NP（眉間）；r4 曾 OK n；有別純副 `忽然之間`（同 r5 `九泉之下`／r6 `意料之外` 誤 r） |

## Error patterns

1. **`zhi-n-fix` 殘留 · 空間名物誤 r**（1/1 BAD）— bulk 把純副 `忽然之間`／`相比之下` 修成 r 時，一併把 **空間處所 NP** 打成 r。本抽樣僅 `眉宇之間`（r4 OK n；對照 `九泉之下`／`意料之外` 已回 n）。
2. **audited re-apply／restore 確認 OK**（本抽樣）：
   - r5 名物回 n：`一得之愚`、`一線之隔`、`驚人之舉`
   - r7 謂語回 v：`召之即來`
   - r1/p1 AABB／stative：`乾乾淨淨` a、`來之不易` a、`林林總總` a、`踉踉蹌蹌` a,r
   - r3 副：`相比之下` r
   - `zhi-n-restore`：`一面之詞`／`百獸之王`／`養育之恩`
   - full-r1 謂語／副：`付之東流` v、`忽然之間` r、`中規中矩` a、`無影無蹤` a、`斷斷續續` a,r
3. **`zhi-n-revert` 正確保留名物 n**（本抽樣）：`一字之差`、`七年之癢`、`不情之請`、`不祧之祖`、`口舌之爭`、`多事之秋`、`婦人之仁`、`後起之秀`、`心腹之患`、`明日之星`、`未解之謎`、`胯下之辱`、`致富之道`、`象牙之塔`、`黔驢之技`
4. **謂語／stative／AABB／有無對 本輪無假陽**：`召之即來` v、`付之東流` v、`來之不易` a、`有增無減` v、`有心無力` a、`有教無類` v、`真真假假` a、`風風雨雨` n 等。
5. **未誤修真名物 OK**：`弦外之音`／`彈丸之地`／`必爭之地`／`破竹之勢`／`血肉之軀` 等。

## Family

- 本批 50 條 **無假陽 熟語**（fix_family 無需清空）。
- 真名物之字格留 n；謂語之字格留 v；stative 留 a；純副／連接留 r；AABB／ABAC／有無對 已標主類。
- **`zhi-n-fix` 白名單勿含空間處所 NP**：`眉宇之間`／`九泉之下`／`意料之外` 類 → n；僅 `忽然之間`／`俯仰之間`／`一夕之間`／`一時之間`／`相比之下`／`一氣之下` 等純副／連接 → r。

## Apply note

`project_pos_audit apply` 本 TSV 1 列 BAD（`fix_pos=n`；family 保持 idiom）後，本抽樣 ok_rate 可升至 **1.00**。

**優先：** 掃 high-trust ∩ `family=idiom` ∩ note 含 `zhi-n-fix` ∩ `pos=r`，只對 **空間／抽象處所名物** 回 `n`：
- `眉宇之間`／`X宇之間` 類空間 NP
- 已修先例：`九泉之下`、`意料之外`／`意料之中`
- **勿** 回滾真副：`忽然之間`／`俯仰之間`／`一夕之間`／`相比之下`／`一氣之下`／`除此之外`

```text
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r8.tsv --dry-run
```
