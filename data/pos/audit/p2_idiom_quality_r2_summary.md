# P2 熟語 (family=idiom) quality audit (r2)

**Sample:** `data/pos/audit/p2_idiom_quality_r2.tsv` (n=50)  
**Universe:** 882 pattern-based len4 idiom-tagged literals  
**Seed:** 202607192 (independent from r1)  
**Threshold:** ok_rate > 0.90  
**Date:** 2026-07-19

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 44 | 88% |
| SOFT | 3 | 6% |
| BAD | 3 | 6% |
| **total** | **50** | 100% |

**ok_rate = (OK+SOFT)/n = 47/50 = 0.94**

**PASS** (0.94 > 0.90)

## BAD detail

| literal | pattern | fix_family | reason |
|---------|---------|------------|--------|
| 在此之後 | 之字格 | *(empty — clear 熟語)* | 普通指示時間短語「在此+之後」，非固定說法 |
| 重重包圍 | AABC | *(empty — clear 熟語)* | 普通描寫搭配「重重+包圍」，非固定說法／成語 |
| 電解電容 | ABAC | *(empty — clear 熟語)* | 電子技術術語 NP（electrolytic capacitor），非固定說法 |

## SOFT（borderline 固定語，留 熟語 可）

| literal | pattern | note |
|---------|---------|------|
| 同工同酬 | ABAC | 勞工原則口號式對舉；固定搭配可留 |
| 大鳴大放 | ABAC | 政治運動口號起源；今亦作固定說法可留 |
| 新人新事 | ABAC | 時代口號式對舉；固定度中等可留 |

## OK patterns (keep)

- Classic 成語／固定語: 一唱一和、一望無垠、一步之遙、不冷不熱、不治之症、予取予求、人中之龍、仁者見仁、女流之輩、實話實説、悶悶不樂、惶惶不安、意料之中、拒之門外、星星之火、朗朗上口、求之不得、浩然之氣、相生相剋、置之不理、而立之年、言之過早、踽踽獨行、身外之物、轉眼之間、鬼鬼祟祟…
- AABB 重疊固定語: 哭哭啼啼、浩浩蕩蕩、白白淨淨、空空蕩蕩、行行企企（粵）
- ABAC 對舉俗語／熟語: 動刀動槍、各色各樣、怪裏怪氣、擠來擠去、救國救民、沒心沒肺、活龍活現、獨來獨往、礙手礙腳、笨手笨腳、自言自語、逛來逛去…
- 有無對: 有意無意

## Error patterns (BAD)

1. **之字格假陽 · 普通指示／能產短語** (1) — `在此之後` 命中 之字格，但是「在此+之後」透明時間短語 → clear `family`
2. **AABC 假陽 · 普通描寫搭配** (1) — `重重包圍` 命中 AABC，但是「重重+包圍」組合描寫，非固定說法 → clear `family`
3. **ABAC 假陽 · 技術並列 NP** (1) — `電解電容` 命中 ABAC，但是電子元件術語，非固定說法 → clear `family`（同 r1 統購統銷類）

## Gate / apply note

- BAD 3 條：`fix_family` 空 → `audit-apply` 會清 `family=idiom`
- SOFT 3 條：保留 `family=idiom`（傘形 熟語 可）
- 本輪 **PASS**（0.94）；與 r1（0.98）獨立種子一致偏高
- 啓發式可考慮：排除明顯技術並列（電解電容類）、排除「在此／自此…之後」類指示 之字格、收緊 AABC 僅保留已固定重疊詞素（奄奄／朗朗／鬼鬼…）而非任意 AA+BC
