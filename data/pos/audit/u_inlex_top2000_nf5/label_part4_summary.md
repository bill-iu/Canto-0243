# u_inlex_top2000_nf5 label part4

**File:** [`label_part4.tsv`](label_part4.tsv)  
**Batch:** In-lexicon still-u · top2000_nf5 · part4 · 343 rows (`罷了`…`可親`)  
**n:** 343  
**Date:** 2026-07-19  

## Policy

- **pos:** closed set `n` 名 · `v` 動 · `a` 形 · `r` 副 · `x` 虛；multi comma-sorted (`a,n` / `a,v` / `n,v` / …)
- **u only** if segmenter fragment / multi-token glue / rare-opaque（唔硬砌主標）
- **family:** 空或 `idiom`（真熟語／成語）；**voice:** 全空
- **note:** 只喺 `u` 行簡註原因（本批無 `u`）

## Counts

| bucket | n | % |
|--------|--:|---:|
| formal (any of n/v/a/r/x) | 343 | 100.0% |
| `u` | 0 | 0.0% |
| **total** | **343** | 100% |

### Tag incidence (row contains tag; multi counted in each)

| tag | rows | % of 343 |
|-----|-----:|---------:|
| v | 169 | 49.3% |
| a | 133 | 38.8% |
| n | 126 | 36.7% |
| r | 10 | 2.9% |
| x | 3 | 0.9% |
| u | 0 | 0.0% |
| **multi** (≥2 tags) | **96** | **28.0%** |

### Single-tag formal

| pos | n |
|-----|--:|
| `v` | 98 |
| `n` | 88 |
| `a` | 58 |
| `r` | 2 |
| `x` | 1 |
| **single subtotal** | **247** |

### Multi-tag

| multi | n |
|-------|--:|
| `a,v` | 51 |
| `n,v` | 17 |
| `a,n` | 16 |
| `a,r` | 6 |
| `n,r` | 2 |
| `a,n,v` | 2 |
| `v,x` | 1 |
| `n,x` | 1 |
| **multi subtotal** | **96** |

family=idiom: **182** · voice non-empty: **0**

## `u` inventory (0)

（無；本批皆可主標 formal，無 segmenter fragment）

## Clear formal patterns (keep)

1. **成語謂語 → `v`／`a,v` + idiom** — 虎視眈眈、直抒己見、騎馬找馬、旋轉乾坤、見縫就鑽、挖肉補瘡、趕盡殺絕、剪草除根…
2. **成語形容／狀態 → `a`／`a,r`／`a,n` + idiom** — 苦不堪言、超羣絕倫、缺心少肺、千篇一律、文質彬彬、金碧輝煌、出神入化、出類拔萃、千真萬確…
3. **成語名物／典故 → `n` + idiom** — 雄心壯志、獨夫民賊、金城湯池、魯魚亥豕、瓊枝玉葉、泰山鴻毛、朽木糞土…
4. **技術／學科複合 → `n`** — 電報掛號、五筆字形、倫琴射線、常態分佈、滑車神經、會厭軟骨、手足口症、等比級數、一次方程式、捲舌元音、國際公制、丙種射線…
5. **現代常用詞** — 退燒／遇害／拍照／毆打／離席 `v`；踏實／開明／頑皮／寬鬆／消極／精明 `a`；老手／高院／故鄉／精品／侍應生 `n`；充其量／特地 `r`；何事 `x`
6. **名動兩用 `n,v`** — 自重、退貨、談笑、休戰、吃喝玩樂、哀號、登山、試管受孕、高談闊論、分居、人工呼吸
7. **單字自由語素** — 雌 `a,n`；貶／卸 `v`；傲 `a`；顯 `a,v`（唔當 fragment）
8. **邊緣套語** — 罷了 `v,x`；等因奉此 `n,x` idiom（公文套語）

## Notes / edge

- **Fragment rate 0%** — top2000_nf5 in-lex 成語／複合／常用詞為主；唔發明 POS
- **中小企** → `n`（SME 縮寫，真詞位）
- **哀的美敦書** → `n`（ultimatum 音譯）
- **開放電路** → `n`（電路術語 open circuit）
- **叛逆／疏離** → `a,n,v`（形／名／動多義）

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex_top2000_nf5/label_part4.tsv` | filled labels (overwrite) |
| `data/pos/audit/u_inlex_top2000_nf5/label_part4_summary.md` | this summary |
