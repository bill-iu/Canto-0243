# Full-system POS audit — P2 熟語 (full_r1)

**Sample:** `data/pos/audit/full_r1/p2_idiom_sample.tsv` (n=168)  
**Universe:** 879 pattern-based len4 `family=idiom` literals  
**Seed:** 20260720 (manifest)  
**Threshold:** ok_rate > 0.90  
**Date:** 2026-07-19  
**Scope:** family=idiom quality；high|gate 另查主標 pos

## Strata (from manifest)

| stratum | universe | sample |
|---------|--------:|-------:|
| high\|gate\|idiom | 228 | 50 |
| high\|u\|idiom | 186 | 50 |
| low\|low\|idiom | 18 | 18 |
| low\|u\|idiom | 447 | 50 |
| **total** | **879** | **168** |

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 148 | 88.1% |
| SOFT | 6 | 3.6% |
| BAD | 14 | 8.3% |
| **total** | **168** | 100% |

**ok_rate = (OK+SOFT)/n = 154/168 = 0.9167**

**PASS** (0.9167 > 0.90)

## BAD detail（全部）

### A. 清 family（非熟語 · `fix_family` 空）

| literal | stratum | pattern | reason |
|---------|---------|---------|--------|
| 哈哈哈哈 | high\|u | AABB | 純擬聲重疊笑聲，非固定說法 |
| 亞美尼亞 | low\|low | AxxA | 國名／專名（Armenia），非熟語 |
| 匆匆離去 | low\|low | AABC | 普通描寫 VP「匆匆+離去」 |
| 彈道導彈 | low\|low | AxxA | 軍事技術 NP（ballistic missile） |
| 核糖核酸 | low\|low | ABAC | 生物化學術語 NP（RNA） |
| 空空導彈 | low\|low | AABC | 軍事技術 NP（air-to-air missile） |

### B. 閘用主標 pos 錯（真熟語 · `fix_pos` + `fix_family=idiom`）

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 乘人之危 | n | v | 謂語成語；n 假陽會毒同名詞閘 |
| 付之一炬 | n | v | 謂語成語；n 假陽會毒同名詞閘 |
| 付之東流 | n | v | 謂語成語；n 假陽會毒同名詞閘 |
| 收之桑榆 | n | v | 謂語成語；n 假陽會毒同名詞閘 |
| 為之動容 | n | v | 謂語成語；n 假陽會毒同名詞閘 |
| 言之尚早 | n | v | 謂語成語；n 假陽會毒同名詞閘 |
| 言之成理 | n | v | 謂語成語；n 假陽會毒同名詞閘 |
| 趁人之危 | n | v | 謂語成語；n 假陽會毒同名詞閘 |

## SOFT（borderline 固定語，留 熟語 可）

| literal | stratum | note |
|---------|---------|------|
| 即興之作 | high\|gate | 偏描寫 NP「即興+之作」；固定搭配可留 |
| 生存之道 | high\|gate | X之道 能產；文學固定式可留 |
| 致富之道 | high\|gate | X之道 能產；固定搭配可留 |
| 同工同酬 | low\|u | 勞工原則口號式對舉；固定搭配可留 |
| 新人新事 | low\|u | 時代口號式對舉；固定度中等可留 |
| 晚婚晚育 | low\|u | 計劃生育政策口號式對舉；固定搭配可留 |

## OK patterns (keep)

- Classic 之字格名物：一國之主、一己之見、一箭之仇、一面之交、傳家之寶、喪家之犬、嗟來之食、大雅之堂、天作之合、天淵之別、後顧之憂、必爭之地、有婦之夫、無米之炊、神來之筆、而立之年、莫逆之交、覆盆之冤、象牙之塔、點睛之筆…
- Classic 成語／固定語：一石二鳥、一望無垠、一望無際、一覽無餘、有教無類、無惡不作、喃喃自語、彬彬有禮、無影無蹤、搖搖欲墜、井井有條、息息相關、破罐破摔、雙宿雙飛、飄飄欲仙…
- AABB／ABAB 重疊固定語：含含糊糊、安安穩穩、實實在在、尋尋覓覓、彼此彼此、悠哉悠哉、婆婆媽媽、鬼鬼祟祟、行行企企（粵）、求求其其（粵）…
- ABAC 對舉：小偷小摸、強買強賣、怪模怪樣、或多或少、大徹大悟、大魚大肉、問長問短、礙手礙腳、老夫老妻…
- 有無對：有心無力、有氣無力、無所不能

## Error patterns (BAD)

1. **AxxA／AABC／ABAC 假陽 · 專名／技術 NP** (4) — 亞美尼亞、彈道導彈、空空導彈、核糖核酸 → clear `family`
2. **AABC 假陽 · 普通描寫 VP** (1) — 匆匆離去 → clear `family`
3. **AABB 假陽 · 純擬聲** (1) — 哈哈哈哈 → clear `family`
4. **之字格 + len4-noun · 謂語成語假 n** (8) — 乘／趁人之危、付之一炬／東流、為之動容、收之桑榆、言之尚早／成理 → `fix_pos=v`，保留 `family=idiom`

## Apply note

- **清 family 6 條**：`fix_family` 空 → `project_pos_p2` family-verdicts apply 會清 `family=idiom`
- **修 pos 8 條**：`fix_pos=v` 且 `fix_family=idiom`（避免 family-apply 誤清熟語）→ `project_pos_audit apply`
- SOFT 6 條：保留 `family=idiom`
- 本輪 **PASS**（0.9167 > 0.90）
- 啓發式可考慮：收緊 AxxA 排除國名／導彈類雙端同字技術詞；AABC 排除「AA+離去／包圍」透明搭配；AABB 排除純單字擬聲四連；之字格高信任 gate 對已知謂語成語勿盲套 len4-noun
