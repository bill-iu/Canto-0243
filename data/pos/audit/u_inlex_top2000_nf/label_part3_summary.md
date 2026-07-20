# u_inlex_top2000_nf manual POS — part3

**File:** `data/pos/audit/u_inlex_top2000_nf/label_part3.tsv`
**Universe:** in-lexicon still-`u` · essay top2000 non-fragment · part3 · **400** rows
**Date:** 2026-07-19

**Rules:** `n/v/a/r/x` multi-ok（逗號、字母序 `a,n,r,v,x`）；`u` 僅真正截斷／殘片；`family=idiom` 只標清晰熟語；`voice` 全空；`note` 只標 `u` 理由。

## Counts formal vs u

| bucket | n | % |
|--------|--:|---:|
| formal（非 u） | 398 | 99.5% |
| `u` fragment/opaque | 2 | 0.5% |
| **total** | **400** | 100% |

### Single-tag vs multi

| pos 模式 | n |
|----------|--:|
| `n` only | 196 |
| `v` only | 51 |
| `a` only | 22 |
| `r` only | 9 |
| `x` only | 3 |
| multi（≥2 tags） | 117 |
| `u` | 2 |
| `family=idiom` | 3 |
| voice non-empty | 0 |
| **total** | **400** |

### Tag incidence（row 含該 tag；multi 可重疊）

| tag | rows |
|-----|-----:|
| n | 288 |
| v | 129 |
| a | 64 |
| r | 33 |
| x | 15 |
| u | 2 |
| multi rows | 117 |

### `family=idiom`

| literal | pos |
|---------|-----|
| 豐富多彩 | a |
| 迫不及待 | a,r |
| 實事求是 | a,r |

### `u` keep

| literal | note |
|---------|------|
| 我溝 | 主+動截斷 |
| 自已 | 自己誤寫／殘片 |

## Formal patterns

1. **專名／地名／姓／暱稱 → `n`**：鄧、阮、邢、緬甸、葡萄牙、烏克蘭、北海道、珠三角、順德、加州、馬自達、蜘蛛俠、婷婷、娜娜、妞妞、杭、奎、琦、昊、靖、耿
2. **粵語常用**：錢罌、鎚仔、開波、飛仔、高妹、香口膠、呢個、亂嚟、係咁大、執輸、威水、家下、早排、擘大眼、擺低、整爛、走甩、記低、角落頭、行人路、自動波、魚生、牛扒、粟米片、春袋、暗爽、口花花、手緊、嚟料、降頭、阿爺、流落嚟、飲得、點好
3. **名動 dual → `n,v`**：過關、關懷、防備、減排、提速、排毒、減持、測算、解密、減免、上訪、擴容、警示、製藥、執業、抽查、導購、匯報、升級、指引、操控、永別、聊天、絕育、批示、組團、防汛、收款、競價、首創、分銷、立案
4. **形／副／虛**：適中、愜意、強有力、優美、柔順、煩躁、白皙、猥瑣、懂事、威水；一不小心、當即、前不久、仍未、長期以來、時而、終究、緊接着；呢個、艘、比如、乃是
5. **熟語 family=idiom**：豐富多彩、迫不及待、實事求是

## Policy notes

1. **唔造 POS：** 主+動截斷（我溝）、誤寫殘片（自已）一律 `u`。
2. **multi 從嚴：** 只標兩棲皆常見；主標不清先單標。
3. **family：** 僅真熟語三條；voice 全空。
4. **下一步：** 與 part1–2／4–5 合併後可 `_apply.py` upsert（note 帶 `u-inlex-nf2k`）再抽 gate sample。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex_top2000_nf/label_part3.tsv` | 400 列已填 pos |
| `data/pos/audit/u_inlex_top2000_nf/label_part3_summary.md` | 本摘要 |
