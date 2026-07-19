# u-repair gate POS quality audit (r1)

**Sample:** `data/pos/audit/u_repair_gate_r1.tsv` (n=50)  
**Universe:** newly promoted high-trust 閘用詞類 from `u-repair` (`stratum=u-repair|gate`)  
**Threshold:** ok_rate = (OK+SOFT)/n **> 0.90**  
**Date:** 2026-07-19  
**Rules:** n/v/a/r/x/u；AABB mostly a；particles → x；stative → a；multi only if both common；family 真熟語留 idiom

## Counts

| verdict | n | % |
|---------|--:|---:|
| OK | 39 | 78% |
| SOFT | 7 | 14% |
| BAD | 4 | 8% |
| **total** | **50** | 100% |

**ok_rate = (OK+SOFT)/n = 46/50 = 0.92**

**PASS** (0.92 > 0.90)

## BAD detail

| literal | was | fix_pos | fix_family | reason |
|---------|-----|---------|------------|--------|
| 巴巴多斯 | a,r | n | *(empty — clear 熟語)* | 國名 Barbados；AABC／aabc-u 假陽；非熟語 |
| 層層包圍 | a,r | v | *(empty — clear 熟語)* | 普通描寫 VP「層層+包圍」；同 匆匆離去 類 AABC 假陽 |
| 爸爸媽媽 | a | n | — | 親屬並列名；aabb-u 假 a 會毒同形閘 |
| 男男女女 | a | n | idiom（留） | 人稱集合名；同 風風雨雨→n；a 假陽會毒同形閘 |

## SOFT（borderline 可留閘）

| literal | pos | note |
|---------|-----|------|
| 不三不四 | a,v | 主標 a；v 薄（不X不Y 啓發式 multi 可） |
| 呼呼大睡 | a,r | 偏動；a,r 情狀 multi 閘可 |
| 好好睇睇 | a | 粵 AABB 偏動能產；a 可 |
| 完完全全 | a | 偏副 r；AABB mostly a 可 |
| 時時刻刻 | a | 偏副 r；AABB mostly a 可 |
| 溝溝坎坎 | a | 可名物 n；AABB a 情狀可 |
| 草草了事 | a,r | 偏動；情狀 a,r 閘可 |

## OK patterns worth keeping

- **canto-u-map 清晰單標／multi**：中國 `n`、出街／搞掂 `v`、十分／啱啱 `r`、唔使 `v,x`、着 `v,x`、靚仔／靚女 `a,n`
- **AABB → a**（啓發式正確）：吃吃喝喝、唧唧喳喳、嘰嘰喳喳、密密麻麻、磕磕巴巴、紛紛揚揚、縫縫連連、遮遮掩掩、閃閃縮縮、蝦蝦霸霸、高高興興
- **AAAA → x**：啊啊啊啊
- **AABC stative a,r**：忿忿不平、憤憤不平、振振有詞／辭、息息相關、洋洋自得、源源不絕、歲歲平安、躍躍欲試、遙遙領先、嘖嘖稱奇
- **有無對／不X不Y → a（或 a,v）**：有備無患、有恃無恐、有始有終、無怨無悔、無私有弊、不吐不快、不醉不歸

## Error patterns (BAD)

1. **AABC 假陽 · 國名** (1) — 巴巴多斯 → `n`，清 `family`
2. **AABC 假陽 · 透明 AA+V 描寫 VP** (1) — 層層包圍 → `v`，清 `family`（對照 匆匆離去）
3. **AABB 假陽 a · 集合／親屬名物** (2) — 爸爸媽媽、男男女女 → `n`（對照 風風雨雨）

## Apply note

- **修 pos 4 條**（皆有 `fix_pos`）→ `project_pos_audit apply`
- **清 family 2 條**（巴巴多斯、層層包圍：`fix_family` 空）→ `project_pos_p2` family-verdicts apply  
  - 男男女女：`fix_family=idiom` 留熟語  
  - 爸爸媽媽：本無 family
- SOFT 7 條：保留現標（不升不降）
- 本輪 **PASS**（0.92 > 0.90）
- 啓發式可考慮：AABC 排除國名／「AA+包圍／離去」透明 VP；AABB 排除親屬並列／人稱集合名物（爸爸媽媽、男男女女）勿盲套 a

```text
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/u_repair_gate_r1.tsv --dry-run
python -m ingest.project_pos_p2 family-verdicts --verdicts data/pos/audit/u_repair_gate_r1.tsv --dry-run
```
