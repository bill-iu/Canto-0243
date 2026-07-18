# u_top3000 label_part1 POS fill

**File:** `data/pos/audit/u_top3000/label_part1.tsv`  
**Rows:** 500 (essay-frequency still-u batch)  
**Date:** 2026-07-19  

**Rules:** n/v/a/r/x (comma multi-ok); particles／pronouns → x; stative → a; verbs → v; proper names → n; essay fragments (我同／我講／有個／咗個／的人…) → u; family empty unless clear 熟語 (none marked); voice empty.

## Tag incidence (row contains tag; multi counted in each)

| tag | rows | % of 500 |
|-----|-----:|---------:|
| n | 209 | 41.8% |
| v | 99 | 19.8% |
| a | 86 | 17.2% |
| r | 74 | 14.8% |
| x | 115 | 23.0% |
| u | 42 | 8.4% |
| **multi** (≥2 tags) | **125** | **25.0%** |

All multi rows are exactly 2-tag (no 3+).  
family=idiom: 0 · voice non-empty: 0

## Single-tag breakdown

| pos | pure single |
|-----|------------:|
| n | 135 |
| v | 72 |
| a | 43 |
| r | 24 |
| x | 59 |
| u | 42 |
| multi | 125 |
| **total** | **500** |

## u keep (42) — essay fragments / not real lexemes

我同 我講 我望 我見 我要 我個 我會 有個 然 我問 咗個 的人 我話 你講 當我 我的 我知 你的 嘅人 我仲 問我 我點 中的 我用 他的 我將 嘅事 咗去 讓我 我是 我行 咗好 我也 也不 也有 都有 我心 是個 上的 先會 我先 那是

## Notable patterns

- **Names / 阿X:** 陳 阿心 三葉 阿明 阿妹 阿政 嘉琪 阿婆 軒轅 利利 茵 阿文 小熙 鐸 雪琪 星華 阿晴 天凡 星儀 寶萱 小柔 秦 詩詩 嘉浩 傑 嬸 → n
- **Canto verb / stative:** 郁 抌 鐘意 好睇 核突 拍拖 沖涼 坐低 溫書 𥄫 影相 犀利 掂 曳 → v / a
- **Closed-class x:** 我地 我們 他們 定係 嘅/嗰/呢 系列 爲了 無論 既然 若果 一係 幹嘛 嘆詞 哈哈／哇／哎…
- **Num+CL:** 一句 一種 一條 三個 一間 一件 一份 一位 一張 第二個 → x,n
