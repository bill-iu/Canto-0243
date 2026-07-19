# P3 full-system POS audit (full_r1)

**Sample:** `data/pos/audit/full_r1/p3_sample_part{1..4}.tsv` (n=853)  
**Universe:** P3 Essay ranks 5001–20000 (15 000) stratified per `manifest.json`  
**Seed:** 20260720  
**Threshold:** ok_rate > 0.90  
**Date:** 2026-07-19

## Policy

| stratum | rule |
|---------|------|
| gate (high/medium) | primary POS correct for hard gate |
| low draft | primary acceptable, else BAD+fix_pos |
| u | OK if indeterminate/fragment; BAD+fix_pos if clear POS |
| idiom family | clear family if not fixed expression |

## Combined counts

| verdict | n | % |
|---------|---|---|
| OK | 236 | 27.7% |
| SOFT | 88 | 10.3% |
| BAD | 529 | 62.0% |
| **total** | **853** | 100% |

**ok_rate = (OK+SOFT)/n = 324/853 = 0.3798**

**FAIL** (0.3798 ≤ 0.90)

### By stratum (approx. from filled parts)

| stratum | n | OK | SOFT | BAD | ok_rate |
|---------|---|----|------|-----|---------|
| `high\|gate\|idiom` | 5 | 4 | 0 | 1 | 0.800 |
| `high\|gate\|plain` | 50 | 47 | 0 | 3 | 0.940 |
| `high\|u\|idiom` | 8 | 0 | 0 | 8 | 0.000 |
| `high\|u\|plain` | 2 | 2 | 0 | 0 | 1.000 |
| `low\|low\|plain` | 129 | 104 | 14 | 11 | 0.915 |
| `low\|u\|idiom` | 16 | 0 | 0 | 16 | 0.000 |
| `low\|u\|plain` | 593 | 42 | 68 | 483 | 0.185 |
| `medium\|gate\|plain` | 50 | 37 | 6 | 7 | 0.860 |

**Gate-only ok_rate** (`high|gate|*` + `medium|gate|plain`): **(4+47+37+6)/(5+50+50) = 94/105 = 0.8952** → **FAIL** (≤ 0.90; high|gate alone 51/55 = 0.927 PASS)

## Error patterns (BAD)

1. **u under-tag (clear POS)** — ~507  
   Dominant: `no-source;fallback` mass-`u` on recoverable heads (same shape as P1 low|u ~80% recoverable).
2. **cow-multi 形／副誤 n,v（閘用）** — 7  
   medium gate: 互助 r假、固有／激烈／熟練 形誤 n,v、略微 n假、繼承 a假、趕緊 n,v假.
3. **prefix-passive 假陽 → n** — 2  
   受衆、被窩 (high gate).
4. **verb-suffix／否定補語假陽** — 2  
   不掉→u；當下 (low draft) n,r.
5. **low draft primary 錯** — 11  
   cow-single 形誤 n、副誤 n／v 等.
6. **idiom family 假陽** — 1  
   可口可樂 ABAC 品牌 → clear family + n.
7. **cow-single n on 謂語成語** — 1  
   無處不在 → a,v.

## Gate-impact BAD (high/medium gate only)

| literal | stratum | was | fix_pos | reason |
|---------|---------|-----|---------|--------|
| 無處不在 | high\|gate\|idiom | n | a,v | 謂語形／動；非名 |
| 不掉 | high\|gate\|plain | v | u | 否定+掉；非獨立動詞 |
| 受衆 | high\|gate\|plain | v | n | 觀眾／聽衆；prefix-passive 假陽 |
| 被窩 | high\|gate\|plain | v | n | 被褥；prefix-passive 假陽 |
| 互助 | medium\|gate\|plain | r,v | n,v | r 假陽 |
| 固有 | medium\|gate\|plain | n,v | a | 形；n,v 假陽 |
| 激烈 | medium\|gate\|plain | n,v | a | 形；n,v 假陽 |
| 熟練 | medium\|gate\|plain | n,v | a | 形；n,v 假陽 |
| 略微 | medium\|gate\|plain | n,r | r | 副；n 假陽 |
| 繼承 | medium\|gate\|plain | a,v | n,v | a 假陽 |
| 趕緊 | medium\|gate\|plain | n,v | r | 副；n,v 假陽 |

## BAD by stratum (detail)

### high|gate|* + medium|gate|* (11)

見上表。優先 `project_pos_audit apply` 此 11 列。

### high|u|idiom (8) — all BAD+fix_pos

| literal | fix_pos |
|---------|---------|
| 一清二楚 | a,r |
| 嘻嘻哈哈 | a,r |
| 大大小小 | a |
| 實實在在 | a,r |
| 方方面面 | n |
| 有意無意 | r |
| 有所不同 | a,v |
| 老老實實 | a,r |

### low|low|plain BAD (11)

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 不便 | n | a | 形 |
| 在外 | n | r | 副 |
| 均 | v | r | 副 |
| 放寬 | n | v | 動 |
| 有效 | v | a | 形 |
| 正直 | n | a | 形 |
| 無情 | n | a | 形 |
| 當下 | v | n,r | verb-suffix 假陽 |
| 繁忙 | n | a | 形 |
| 自主 | n | a,v | 形／動 |
| 親切 | n | a | 形 |

### low|u|idiom (16) — all BAD+fix_pos

| literal | fix_pos | note |
|---------|---------|------|
| 一生一世 | n,r | |
| 一舉一動 | n | |
| 人來人往 | v,a | |
| 依依不捨 | a,v | |
| 可口可樂 | n | clear family（品牌；ABAC 假陽） |
| 各式各樣 | a | |
| 各種各樣 | a | |
| 哈哈大笑 | v | |
| 唔多唔少 | r | |
| 唔經唔覺 | r | |
| 奄奄一息 | a | |
| 忍無可忍 | v | |
| 有講有笑 | v | |
| 無時無刻 | r | |
| 若隱若現 | a,v | |
| 講開又講 | v | |

### low|u|plain BAD (483)

Full row-level fixes live in the part TSVs (`verdict=BAD` + `fix_pos`).  
Primary classes (approx. share of 483):

| fix_pos family | examples |
|----------------|----------|
| `n` | 事蹟、俄國、地鐵站、張學友、鋁合金、… |
| `v` | 交費、催促、傾偈、擺脫、關機、… |
| `a` | 了不起、嚴格、堅硬、很清楚、… |
| `r` / `r,v` / `x` | 不久、年年、那種、一顆、… |
| multi | 創新 n,v、偏低 a,v、設定 n,v、… |

OK fragments in this stratum (~42): 切詞膠合（他也／將你／小貞到…）、罕異體（埸）等 — `u` justified.  
SOFT (~68): 單字多義、小句截斷、疊稱愛稱 — `u` acceptable until multi-tag review.

## Files

| path | role |
|------|------|
| `data/pos/audit/full_r1/p3_sample_part1.tsv` | filled verdicts (gate + low draft + u start) |
| `data/pos/audit/full_r1/p3_sample_part2.tsv` | filled verdicts (low\|u\|plain) |
| `data/pos/audit/full_r1/p3_sample_part3.tsv` | filled verdicts (low\|u\|plain) |
| `data/pos/audit/full_r1/p3_sample_part4.tsv` | filled verdicts (low\|u end + medium\|gate) |
| `data/pos/audit/full_r1/p3_summary.md` | this summary |

## Note

- Combined ok_rate is **not** a pure gate metric: **593/853 (70%)** is `low|u|plain` fallback `u`.
- Use **Gate-only ok_rate (0.895)** for hard-gate quality; 11 gate BADs are batch-fixable (prefix-passive、cow-multi 形副誤、不掉、無處不在).
- `low|low|plain` draft ok_rate **0.915** passes draft bar.
- Audit-only; SSOT not applied this pass.  
  Apply path when ready:  
  `python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/p3_sample_partN.tsv --dry-run`
