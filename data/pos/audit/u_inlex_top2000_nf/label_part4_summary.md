# u_inlex_top2000_nf label part4

**File:** [`label_part4.tsv`](label_part4.tsv)  
**Batch:** In-lexicon still-u · top2000_nf · part4 · 400 rows (`必不可少`…`機頂盒`)  
**n:** 400  
**Date:** 2026-07-19  

## Policy

- **pos:** closed set `n` 名 · `v` 動 · `a` 形 · `r` 副 · `x` 虛；multi comma-sorted (`a,n` / `n,v` / …)
- **u only** if segmenter fragment / multi-token glue / rare-opaque（唔硬砌主標）
- **family:** 空或 `idiom`（真熟語／成語）；**voice:** 全空
- **note:** 只喺 `u` 行簡註原因

## Counts

| bucket | n | % |
|--------|--:|---:|
| formal (any of n/v/a/r/x) | 396 | 99.0% |
| `u` | 4 | 1.0% |
| **total** | **400** | 100% |

### Tag incidence (row contains tag; multi counted in each)

| tag | rows | % of 400 |
|-----|-----:|---------:|
| n | 262 | 65.5% |
| v | 129 | 32.3% |
| a | 70 | 17.5% |
| r | 32 | 8.0% |
| x | 8 | 2.0% |
| u | 4 | 1.0% |
| **multi** (≥2 tags) | **98** | **24.5%** |

### Single-tag formal

| pos | n |
|-----|--:|
| `n` | 196 |
| `v` | 70 |
| `a` | 23 |
| `r` | 8 |
| `x` | 1 |
| **single subtotal** | **298** |

### Multi-tag

| multi | ~n |
|-------|---:|
| 2-tag (`n,v` / `a,n` / `a,v` / `a,r` / `r,v` / `n,r` / `n,x` / `r,x` / …) | ~90 |
| 3-tag (`a,n,v` · `a,n,r` · `a,r,v` · `a,n,x` · `a,r,x`) | ~8 |
| **multi subtotal** | **98** |

family=idiom: **5** · voice non-empty: **0**

## `u` inventory (4)

| literal | reason |
|---------|--------|
| 實會 | 實+會截斷 |
| 將你 | 介／副+代截斷 |
| 拉西 | 罕／不明 |
| 魍 | 魍魎殘字 |

## family=idiom (5)

必不可少 · 毫無疑問 · 夢寐以求 · 山長水遠 · 順理成章

## Clear formal patterns (keep)

1. **實體／專名 → `n`** — 江門、故宮、湛江、孫悟空、挪威、大嶼山、九龍城、葵涌、華山、米蘭、荷蘭、耶和華；器物／機構（收藏夾、閥門、護膚品、機頂盒、效果圖、表達式、T恤、竈頭）
2. **粵語常用動 → `v`** — 埋手、嚟得切、搞嘢、打風、戲飛、拖手、拍門、郁下、發姣、落機、裝飯、話知、要嚟、忍笑
3. **粵語副／情狀 → `r`** — 慢慢來、一步步、時不時、骨子裏、尚算、極其、硬是、遲遲、點得（`r,v`）；書面副：毫無疑問、順理成章、正要
4. **形** — 淫穢、完備、辛勤、鮮活、虔誠、絢麗、繁瑣、豔麗、光猛、可信、強硬、密集、簡便、清淨、牢固、瀟灑、腥、繽紛
5. **虛** — 招呼套語 歡迎光臨 → `x`；連／否：不然 `r,x`；在內 `r,x`；量／指：寸 `n,x`、某某 `n,x`、朕 `n,x`；擬聲 嘩嘩 `a,r,x`
6. **名動兩用 `n,v`** — 公測、點播、養護、評比、翻唱、代辦、回饋、考勤、小結、倒計時、座談、刊、開局、算命、一覽、嘔吐、打底、插口、歐遊、誓、調教、護髮、通緝、重逢、領悟、託福
7. **形動／形名 multi** — 過不去、持平、癡迷、勞累、在座、孝順、寫意、激死、滋潤、開懷、虐、安樂、傳奇、正版、雙面、紀實、濱海

## Notes / edge

- **將你** 對齊 u_inlex「將我」類介／副+代截斷 → `u`
- **魍**  alone 作 魍魎 殘字 → `u`（唔硬標 n）
- **實會／拉西** 唔發明主標 → `u`
- **開封** → `n,v`（地名／啟封兩用）
- **特約** → `a,n,v`；**個別** → `a,n,r`；**不夠** → `a,r,v`
- **閑** → `a,n,v`（閒義）；**惠** → `a,n,v`
- Fragment rate **1.0%** — top2000_nf in-lex 批次合理；唔發明 POS

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex_top2000_nf/label_part4.tsv` | filled labels (overwrite) |
| `data/pos/audit/u_inlex_top2000_nf/label_part4_summary.md` | this summary |
