# u_inlex label part4

**File:** [`label_part4.tsv`](label_part4.tsv)  
**Batch:** In-lexicon still-u · part4 · 400 rows (`詞語`…`知情`)  
**n:** 400  
**Date:** 2026-07-19  

## Policy

- **pos:** closed set `n` 名 · `v` 動 · `a` 形 · `r` 副 · `x` 虛；multi comma-sorted (`a,n` / `n,v` / …)
- **u only** if segmenter fragment / multi-token glue / rare-opaque（唔硬砌主標）
- **family / voice:** 全空（普通詞；熟語傘另輪）
- **note:** 只喺 `u` 行簡註原因

## Counts

| bucket | n | % |
|--------|--:|---:|
| formal (any of n/v/a/r/x) | 400 | 100% |
| `u` | 0 | 0% |
| **total** | **400** | 100% |

### Tag incidence (row contains tag; multi counted in each)

| tag | rows | % of 400 |
|-----|-----:|---------:|
| n | 230 | 57.5% |
| v | 145 | 36.3% |
| a | 66 | 16.5% |
| r | 50 | 12.5% |
| x | 27 | 6.8% |
| u | 0 | 0% |
| **multi** (≥2 tags) | **108** | **27.0%** |

### Single-tag formal

| pos | n |
|-----|--:|
| `n` | 159 |
| `v` | 82 |
| `a` | 26 |
| `r` | 13 |
| `x` | 12 |
| **single subtotal** | **292** |

### Multi-tag

| multi | ~n |
|-------|---:|
| 2-tag (`n,v` / `n,r` / `a,n` / `a,r` / `a,v` / `r,v` / `n,x` / `r,x` / `v,x` / …) | 99 |
| 3-tag (`a,n,v` · `a,n,r` · `a,r,v`) | 8 |
| 4-tag (`a,n,r,v` 略) | 1 |
| **multi subtotal** | **108** |

## `u` inventory (0)

本批 in-lexicon 實詞／常用虛詞為主，**無**截斷碎片需留 `u`。

## Clear formal patterns (keep)

1. **實體／專名 → `n`** — 迪士尼、甘肅、長安、湘、寧夏、西湖、海口、九龍塘、屯門、大埔、意大利、中國大陸、蘇軾、麥當勞；器物／機構（檯燈、安全帶、防煙門、序列號、證監會、專賣店、直昇機、註冊表）
2. **粵語常用動 → `v`** — 頂硬上、食晏、夾埋、攪到、整親、淨低、練波、郁動、關事、食藥、飲醉、去街、執到、耷低頭、起行、跌低、飲嘢、住響、帶嚟、打冷震、扮嘢、揞、畀錢、唔在乎
3. **粵語副／情狀 → `r`** — 家陣、久唔久、重係（`r,v`）、得個（`r,v`）、走先（`r,v`）、轉個頭（`r,v`）；書面副：必定、大不了、不曾、並非、再三、到頭來、未曾、永不、久而久之
4. **形** — 厚道、優秀、原始、好衰、安穩、清脆、準確、萬能、親愛、誘人、紮實、微弱、有料、精彩、貼身、迷茫、中小、逍遙、好氣、淒涼、狼狽；AABB／重疊 `a,r`（重重、草草、鈴鈴、流流、熊熊、黯然）
5. **虛** — 指示／代／連／嘆／招呼：那裡、那邊、以至於、諸如、各個、嗰位、某些、好啦、呸、哞、麼麼、生日快樂；量／指：呎、畝、部份、首批、本書（`n,x`）
6. **名動兩用 `n,v`** — 漢化、寫真、付費、主編、調度、訪談、封印、推斷、監察、簽、預計、維權、著作、進出口、表揚、上位、伴、傳教、掛牌、分頁、互動、兼職、塞車、失憶、投放、監…
7. **形動／形名 multi** — 難頂、未定、講得啱、唏噓、過癮、死火、流行、知情、未成年、高壓、大頭、弱智、手工、公益、開源、震撼、贊、益

## Notes / edge

- **唔標 family=idiom** 本批（久而久之 只填 `r`；熟語傘另輪）
- **略** → `a,n,r,v`（粗略／策略／略微／省略 皆常）
- **專** → `a,r,v`；**寧** → `a,n,r`；**好夜** → `a,n,r`
- **驚死** → `a,r,v`（驚到死／程度副）
- **理得** → `v`（理得／唔理得 詞幹，作 manage／bother）
- **生日快樂** → `x`（招呼套語，同呸／好啦）
- Fragment rate **0%** — in-lex 批次合理；唔發明 POS

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex/label_part4.tsv` | filled labels (overwrite) |
| `data/pos/audit/u_inlex/label_part4_summary.md` | this summary |
