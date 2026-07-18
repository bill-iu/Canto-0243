# GATE-ONLY reconfirm audit (post full_r1)

**Dir:** `data/pos/audit/full_r1/gate_reconfirm/`  
**Seed:** 20260720 (manifest)  
**Threshold:** ok_rate = (OK+SOFT)/n > 0.90  
**Date:** 2026-07-19  
**Scope:** gate samples only；rules: n/v/a/r/x/u；particles→x；stative→a；multi only if both common；熟語 only if fixed expression

## Per-phase summary

| phase | n | OK | SOFT | BAD | ok_rate | pass |
|-------|--:|---:|-----:|----:|--------:|:----:|
| p0 | 124 | 123 | 0 | 1 | **0.9919** | ✅ PASS |
| p1 | 50 | 49 | 0 | 1 | **0.9800** | ✅ PASS |
| p2 | 50 | 36 | 0 | 14 | **0.7200** | ❌ FAIL |
| p3 | 60 | 56 | 1 | 3 | **0.9500** | ✅ PASS |

**Overall gate reconfirm:** p0/p1/p3 PASS；**p2 FAIL**（殘留 AABB `u` 欠標 + 之字格／之下格假陽 n）.

## P0 — campaign gate (n=124)

| verdict | n | % |
|---------|--:|---:|
| OK | 123 | 99.2% |
| SOFT | 0 | 0% |
| BAD | 1 | 0.8% |

**ok_rate = 123/124 = 0.9919 → PASS**

### BAD

| literal | was | fix_pos | fix_family | reason |
|---------|-----|---------|------------|--------|
| 拒之門外 | n + idiom | v | *(keep idiom)* | 之字格假陽 n；謂語成語「拒絕／擋於門外」；n 會毒同名詞閘 |

### Notes

- full_r1 已修並喺本抽樣確認 OK：`忽然之間` n→r、`為之動容`／`處之泰然` n→v、多數 true-nv／canto-heuristic 主標。
- `一夕之間` 留 n（時間名物之字格；與純副 `忽然之間` 區分）。
- family 空但 pos 正確者（如 `不知不覺` r）唔計 BAD（唔影響閘用詞類）。

---

## P1 — Essay Top-5000 ∩ gate (n=50)

| verdict | n | % |
|---------|--:|---:|
| OK | 49 | 98% |
| SOFT | 0 | 0% |
| BAD | 1 | 2% |

**ok_rate = 49/50 = 0.9800 → PASS**

### BAD

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 驚訝 | a,n | a | stative 形；n 假陽會毒同名詞閘 |

### Notes

- high gate 主標乾淨：封閉類 x、真 n,v、粵語詞（嘢／老豆／靚／收埋）均 OK。
- medium cow-multi 僅 `驚訝` 一條假陽 n（同 r1/r2 stative 模式）。

---

## P2 — high-trust 熟語 (n=50)

| verdict | n | % |
|---------|--:|---:|
| OK | 36 | 72% |
| SOFT | 0 | 0% |
| BAD | 14 | 28% |

**ok_rate = 36/50 = 0.7200 → FAIL**（≤ 0.90）

### BAD — 全部（family 皆真熟語，留 idiom；只修 pos）

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 一氣之下 | n | r | 之下格假陽 n；一氣之下＝副 |
| 乾乾淨淨 | u | a | AABB 清晰形；u 欠標 |
| 來之不易 | n | a | 之字格假陽 n；謂語 stative＝形 |
| 冒冒失失 | u | a,r | AABB 形／副；u 欠標 |
| 反之亦然 | n | r | 非名；連接／回指副 |
| 婆婆媽媽 | u | a | AABB 清晰形；u 欠標 |
| 孤孤單單 | u | a | AABB 清晰形；u 欠標 |
| 層層疊疊 | u | a | AABB 清晰形；u 欠標 |
| 彼此彼此 | u | r | ABAB 套語副；u 欠標 |
| 恩恩愛愛 | u | a | AABB 清晰形；u 欠標 |
| 恭恭敬敬 | u | a,r | AABB 形／副；u 欠標 |
| 林林總總 | u | a | AABB 清晰形；u 欠標 |
| 求之不得 | n | v | 之字格假陽 n；謂語成語 |
| 踉踉蹌蹌 | u | a,r | AABB 形／副；u 欠標 |

### Error patterns

1. **AABB／ABAB high-trust 仍 `u`**（10/14）— family 已審熟語，但 pos 未升五主類；同批 `安安穩穩`／`從從容容`／`空空蕩蕩` 等 full_r1 已補 a/r，殘留欠標。
2. **之字格／之下格假陽 n on 謂語／副**（4/14）— `來之不易`→a、`求之不得`→v、`一氣之下`→r、`反之亦然`→r。

### Family

- 本批 50 條 **無假陽 熟語**（fix_family 無需清空）。
- full_r1 已修確認 OK：`忽然之間` r。

### Apply note

優先 `project_pos_audit apply` 本 TSV 14 列 BAD（`fix_pos` 已填；family 保持 idiom）後，p2 gate 抽樣 ok_rate 可升至 1.00。建議另掃 high-trust ∩ `pos=u` ∩ `family=idiom` 批量補 AABB。

---

## P3 — Essay 5001–20000 ∩ gate (n=60)

| verdict | n | % |
|---------|--:|---:|
| OK | 56 | 93.3% |
| SOFT | 1 | 1.7% |
| BAD | 3 | 5.0% |

**ok_rate = (56+1)/60 = 0.9500 → PASS**

### BAD

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 下雪 | n,v | v | 天氣動；n 假陽會毒同名詞閘 |
| 結交 | n,v | v | 只係動；n 假陽會毒同名詞閘 |
| 解決問題 | n | v | len4-noun 假陽；「解決+問題」VP＝動 |

### SOFT

| literal | was | note |
|---------|-----|------|
| 定額 | n,v | 主 n；v 弱可接受 |

### Notes

- true-nv／名詞短語／粵語動補大多 OK。
- 殘留 BAD 為 cow-multi 假 n 與 len4-noun 吃進 VP（可批次修）。

---

## Combined BAD inventory（全 4 檔）

| phase | literal | was | fix_pos | reason |
|-------|---------|-----|---------|--------|
| p0 | 拒之門外 | n | v | 之字格謂語假陽 n |
| p1 | 驚訝 | a,n | a | stative；n 假陽 |
| p2 | 一氣之下 | n | r | 之下格＝副 |
| p2 | 乾乾淨淨 | u | a | AABB u 欠標 |
| p2 | 來之不易 | n | a | 謂語 stative |
| p2 | 冒冒失失 | u | a,r | AABB u 欠標 |
| p2 | 反之亦然 | n | r | 回指副 |
| p2 | 婆婆媽媽 | u | a | AABB u 欠標 |
| p2 | 孤孤單單 | u | a | AABB u 欠標 |
| p2 | 層層疊疊 | u | a | AABB u 欠標 |
| p2 | 彼此彼此 | u | r | ABAB u 欠標 |
| p2 | 恩恩愛愛 | u | a | AABB u 欠標 |
| p2 | 恭恭敬敬 | u | a,r | AABB u 欠標 |
| p2 | 林林總總 | u | a | AABB u 欠標 |
| p2 | 求之不得 | n | v | 謂語成語 |
| p2 | 踉踉蹌蹌 | u | a,r | AABB u 欠標 |
| p3 | 下雪 | n,v | v | 天氣動；n 假陽 |
| p3 | 結交 | n,v | v | 只係動；n 假陽 |
| p3 | 解決問題 | n | v | VP 假名 |

**Total BAD:** 19（p0:1 + p1:1 + p2:14 + p3:3）

---

## Recommend next

```text
# dry-run then apply BAD+fix_pos（family 由列上 family 欄保留 idiom）
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p0_gate_sample.tsv --dry-run
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p1_gate_sample.tsv --dry-run
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p2_gate_sample.tsv --dry-run
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/gate_reconfirm/p3_gate_sample.tsv --dry-run
```

1. **p2 必先 apply** 14 BAD（否則 high-trust 熟語閘用 pos 仍大量 `u`／假 n）。
2. p0/p1/p3 各 1–3 BAD 可一併 apply，進一步收斂假 multi。
3. apply 後可對 p2 再抽一輪 gate 確認 ok_rate > 0.90。

## Files

| path | role |
|------|------|
| `p0_gate_sample.tsv` | P0 gate verdicts (n=124) |
| `p1_gate_sample.tsv` | P1 gate verdicts (n=50) |
| `p2_gate_sample.tsv` | P2 high-trust 熟語 verdicts (n=50) |
| `p3_gate_sample.tsv` | P3 gate verdicts (n=60) |
| `summary.md` | this report |
| `manifest.json` | sample seed／universe |
