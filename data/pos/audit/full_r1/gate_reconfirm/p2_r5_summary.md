# P2 gate reconfirm r5 — high-trust 熟語

**File:** `data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r5.tsv`  
**Round:** 5（post bulk `zhi-n-fix`）  
**Threshold:** ok_rate = (OK+SOFT)/n **> 0.90**  
**Scope:** high-trust 熟語 ∩ gate；rules: n/v/a/r/x/u；particles→x；stative→a；multi only if both common；family 真熟語留 idiom

## Result

| verdict | n | % |
|---------|--:|---:|
| OK | 32 | 64% |
| SOFT | 0 | 0% |
| BAD | 18 | 36% |

**ok_rate = 32/50 = 0.6400 → FAIL**（需 > 0.90）

## BAD — 全部（family 皆真熟語，留 idiom；只修 pos）

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 一得之愚 | v | n | zhi-n 過修；真名物「愚見」NP |
| 一線之隔 | v | n | zhi-n 過修；間隔名物 NP |
| 九泉之下 | r | n | zhi-n 過修；處所名物（非純副一氣之下） |
| 即興之作 | v | n | zhi-n 過修；作品名物 NP |
| 可造之材 | v | n | zhi-n 過修；人才名物；p0/p2 曾 OK n |
| 垂暮之年 | v | n | zhi-n 過修；年齡名物（同不惑之年） |
| 天壤之別 | v | n | zhi-n 過修；差別名物（同天淵之別） |
| 好事之徒 | v | n | zhi-n 過修；人物名物；p0/p2 曾 OK n |
| 殺身之禍 | v | n | zhi-n 過修；災禍名物；r2/r3 曾 OK n |
| 池魚之殃 | v | n | zhi-n 過修；災殃名物 NP |
| 無米之炊 | v | n | zhi-n 過修；事況名物；p2 曾 OK n |
| 玄之又玄 | v | a | zhi-n 過修；stative「極玄」＝形（同少之又少） |
| 肌膚之親 | v | n | zhi-n 過修；親密名物；r1/r2/r4 曾 OK n |
| 醉翁之意 | v | n | zhi-n 過修；意圖名物 NP |
| 門户之見 | v | n | zhi-n 過修；見解名物；r2/r3 曾 OK n |
| 飽學之士 | v | n | zhi-n 過修；人物名物；r2/r3 曾 OK n |
| 養生之道 | v | n | zhi-n 過修；方法名物；p0 曾 OK n |
| 驚人之舉 | v | n | zhi-n 過修；舉動名物；p2 r1 曾 OK n |

## Error patterns

1. **`zhi-n-fix` 過修 · 真名物之字格 n→v**（16/18 BAD）— bulk 把謂語假陽 n 修好時，一併把 **名物頭** 成語打成 v。
   - 人物／士類：`好事之徒`、`飽學之士`
   - 禍殃／舉措／見解：`殺身之禍`、`池魚之殃`、`驚人之舉`、`門户之見`、`醉翁之意`、`一得之愚`
   - 年／別／材／作／炊／道／隔／親：`垂暮之年`、`天壤之別`、`可造之材`、`即興之作`、`無米之炊`、`養生之道`、`一線之隔`、`肌膚之親`
2. **`zhi-n-fix` 過修 · 處所 n→r**（1/18）— `九泉之下` 當純副；實為黃泉處所 NP（對照 `用武之地`／`葬身之地` 仍 n OK；有別 `一氣之下`／`除此之外` 真副／連接）。
3. **`zhi-n-fix` 過修 · stative→v**（1/18）— `玄之又玄` 應 a（同 r3/r4 `少之又少`／`來之不易`），非 v。
4. **謂語／副已修確認 OK**（本抽樣）：`急人之難` v、`揮之不去` v、`收之桑榆` v、`為之動容` v、`置之不理` v、`處之泰然` v、`言之有物` v、`一氣之下` r、`除此之外` r、`一夕之間` r。
5. **未誤修真名物 OK**：`用武之地`／`葬身之地`／`鼎足之勢` n；`一年四季` n。
6. **AABB／ABAC／有無對** 本輪無 BAD（皆 a／a,r／v）。

## Family

- 本批 50 條 **無假陽 熟語**（fix_family 無需清空）。
- 真名物之字格應回 n；謂語之字格留 v；stative 留 a；純副／連接留 r。

## Apply note

`project_pos_audit apply` 本 TSV 18 列 BAD（`fix_pos` 已填；family 保持 idiom）後，本抽樣 ok_rate 可升至 **1.00**。

**優先：** 回滾／覆核 bulk `zhi-n-fix` — 掃 high-trust ∩ `family=idiom` ∩ note 含 `zhi-n-fix` ∩ `pos=v`（或 r），只對 **非動核／非 stative／非純副** 之字格名物頭回 `n`：
- 頭字為 禍／殃／災／見／意／愚／別／年／材／作／士／徒／舉／道／親／隔／地／勢… 且句法為 NP 賓／主 → n
- 勿回滾真謂語（`X之不Y` 動、`置之`／`處之`／`為之`／`言之有`／`急人之` 等）

```text
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample_r5.tsv --dry-run
```
