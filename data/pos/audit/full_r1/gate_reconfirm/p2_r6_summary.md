# P2 gate reconfirm r6 — high-trust 熟語

**File:** `data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r6.tsv`  
**Round:** 6（post partial `zhi-n-restore`）  
**Threshold:** ok_rate = (OK+SOFT)/n **> 0.90**  
**Scope:** high-trust 熟語 ∩ gate；rules: n/v/a/r/x/u；particles→x；stative→a；multi only if both common；family 真熟語留 idiom

## Result

| verdict | n | % |
|---------|--:|---:|
| OK | 33 | 66% |
| SOFT | 0 | 0% |
| BAD | 17 | 34% |

**ok_rate = 33/50 = 0.6600 → FAIL**（需 > 0.90）

## BAD — 全部（family 皆真熟語，留 idiom；只修 pos）

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 一國之主 | v | n | zhi-n 過修；人物名物；r2/p2 曾 OK n |
| 七分之一 | v | n | zhi-n 過修；分數名物；r4 曾 OK n |
| 地主之誼 | v | n | zhi-n 過修；禮誼名物；r2 曾 OK n |
| 女流之輩 | v | n | zhi-n 過修；人物類稱；p2_idiom 曾 OK n |
| 強弩之末 | v | n | zhi-n 過修；比喻狀態名物；r4 曾 OK n |
| 後事之師 | v | n | zhi-n 過修；教訓名物；p0 曾 OK n |
| 意料之外 | r | n | zhi-n 過修；抽象處所名物；r4 曾 OK n |
| 斷袖之癖 | v | n | zhi-n 過修；癖好名物；r4 曾 OK n |
| 沙漠之狐 | v | n | zhi-n 過修；綽號／人物名物 |
| 無恥之徒 | v | n | zhi-n 過修；人物名物（同好事之徒） |
| 無稽之談 | v | n | zhi-n 過修；言論名物；p0 曾 OK n |
| 牢獄之災 | v | n | zhi-n 過修；災禍名物（同殺身之禍） |
| 藏身之處 | v | n | zhi-n 過修；處所名物（同用武之地） |
| 貪天之功 | n | v | restore 過修；動核 VO 謂語（不可貪天之功） |
| 長平之戰 | v | n | zhi-n 過修；戰役事件名物；r2/r4 曾 OK n |
| 首善之區 | v | n | zhi-n 過修；處所名物 |
| 齊人之福 | v | n | zhi-n 過修；福分名物；r3 曾 OK n |

## Error patterns

1. **`zhi-n-fix` 殘留 · 真名物之字格仍 v**（15/17 BAD）— partial restore 只回了少數（`傳家之寶`／`無米之炊`／`肌膚之親`／`養生之道` 等），本抽樣大量名物頭仍停在 v：
   - 人物／徒／輩／狐：`一國之主`、`女流之輩`、`無恥之徒`、`沙漠之狐`
   - 誼／癖／談／災／師／末／福：`地主之誼`、`斷袖之癖`、`無稽之談`、`牢獄之災`、`後事之師`、`強弩之末`、`齊人之福`
   - 處／區／戰／分數：`藏身之處`、`首善之區`、`長平之戰`、`七分之一`
2. **`zhi-n-fix` 過修 · 抽象處所 n→r**（1/17）— `意料之外` 當純副；實為「出乎…」處所 NP（r4 OK n；有別 `相比之下`／`一氣之下` 真副／連接）。
3. **`zhi-n-restore` 過修 · 謂語 VO→n**（1/17）— `貪天之功`：動核「貪+天之功」，應 v（同 `拒之門外`／`求之不得`），restore 誤回 n。
4. **restore 已對確認 OK**（本抽樣）：`傳家之寶` n、`無米之炊` n、`肌膚之親` n、`養生之道` n。
5. **謂語／副／stative 正確 OK**：`召之即來` v、`置之不理` v、`收之桑榆` v、`隨之而來` v、`行之有效` a、`相比之下` r、`一夕之間` r、`俯仰之間` r。
6. **未誤修真名物 OK**：`一面之交`／`君子之交`／`莫逆之交`／`弦外之音`／`不毛之地` n。
7. **AABB／ABAC／AABC／x** 本輪無 BAD（`一個二個` x 同 p0/p3 OK）。

## Family

- 本批 50 條 **無假陽 熟語**（fix_family 無需清空）。
- 真名物之字格應回 n；謂語之字格留 v；stative 留 a；純副／連接留 r。
- restore 白名單勿含動核 VO（`貪天之功` 類）。

## Apply note

`project_pos_audit apply` 本 TSV 17 列 BAD（`fix_pos` 已填；family 保持 idiom）後，本抽樣 ok_rate 可升至 **1.00**。

**優先：** 擴大 `zhi-n-restore` — 掃 high-trust ∩ `family=idiom` ∩ note 含 `zhi-n-fix` ∩ `pos=v`（或 r），只對 **名物頭** 回 `n`：
- 頭／尾為 主／誼／輩／末／師／癖／狐／徒／談／災／處／戰／區／福／分… 且句法為 NP 賓／主 → n
- `意料之外`／`意料之中` 類抽象處所 → n（勿當純副）
- **勿** restore 真謂語：`X之即Y`、`置之`／`處之`／`為之`／`言之有`、`收之`、`隨之而來`、`貪天之功`（VO）等
- **勿** 把 stative（`行之有效`）或純副（`相比之下`／`一夕之間`）回 n

```text
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r6.tsv --dry-run
```
