# u_inlex label_part1 POS fill

**File:** `data/pos/audit/u_inlex/label_part1.tsv`  
**Batch:** in-lexicon still-u · high essay-freq · part1 · **400** rows  
**Date:** 2026-07-19  

**Rules:** n/v/a/r/x（comma multi-ok，a&lt;n&lt;r&lt;v&lt;x 排序）；particles／代／連 → x；stative → a；專名 → n；essay 截斷／黏着殘字 → u；family 僅真熟語 = idiom；voice 全空。

## Counts formal vs u

| bucket | n | % |
|--------|--:|---:|
| formal（非 u） | 381 | 95.2% |
| `u` fragment/opaque | 19 | 4.8% |
| **total** | **400** | 100% |

## Tag incidence（row contains tag；multi 計入每個）

| tag | rows | % of 400 |
|-----|-----:|---------:|
| n | 222 | 55.5% |
| v | 130 | 32.5% |
| a | 86 | 21.5% |
| r | 46 | 11.5% |
| x | 29 | 7.2% |
| u | 19 | 4.8% |
| **multi** (≥2 tags) | **121** | **30.3%** |

family=idiom: 4 · voice non-empty: 0

## Single-tag breakdown

| pos | pure single |
|-----|------------:|
| n | 143 |
| v | 58 |
| a | 42 |
| r | 8 |
| x | 9 |
| u | 19 |
| multi | 121 |
| **total** | **400** |

## u keep (19) — essay fragments / opaque residues

我見（主+動截斷） 然（然後等截斷殘字） 將我（介／副+代截斷） 曱（曱甴殘字） 甴（曱甴殘字） 你估（主+動截斷） 我識（主+動截斷） 總有（總+有截斷） 個月（個+月量度碎片） 講乜（講+乜截斷） 侏（殘字／不明） 仲話（仲+話截斷） 不知幾（不知幾多截斷） 人嚟（主+嚟截斷） 蘿（蘿蔔截斷殘字） 我架（主+架語氣截斷） 蔔（蘿蔔截斷殘字） 咖（咖啡等殘字／黏着） 咇（罕用／擬聲殘）

## family=idiom (4)

急不及待, 的而且確, 男人老狗, 似曾相識

## Notable patterns

- **截斷 u（對齊 u_top3000）：** 我見／你估／我識／我架／將我／人嚟；總有／個月／講乜／仲話／不知幾；然；曱／甴；蘿／蔔；侏；咖／咇
- **粵語實詞 formal：** 合埋／咁滯／孭／愈嚟愈／極之／嗰度／跪低／埋單／差人／差館／外母／屋邨／戇居／郁手／食屎／石屎／手指公／銀仔／剩低／嘈醒／偷睇／好型／難食／難聽／一嚟／唔覺意／男人老狗
- **專名／地名／機構 n：** 河北／昆明／加拿大／伊朗／清華／長江／澳門／歐陽／黎生／中大／百佳／高登／公安局／派出所／市政府／央行
- **stative a：** 堅強／囂張／多餘／害羞／開朗／淡定／清純／淫蕩／戇居／迷惘／甜美／有意思／好近／好型
- **closed-class x：** 是否／不論／以免／嗰度／邊間／呱／嘎嘎／哈哈哈哈哈／喳
- **true dual multi：** 眼紅 a,v；上手 a,v；筆記 n,v；彈性 a,n；親身 a,r；高速 a,n,r

## Policy notes

1. **唔造 POS：** 主+動／介+代／總+有／量月碎片／曱甴·蘿蔔分字一律 `u`。
2. **multi 從嚴：** 只標兩棲皆常見；主標不清先單標。
3. **family：** 急不及待、的而且確、似曾相識、男人老狗 → idiom；其餘空。
4. **下一步：** 與 part2–5 合併後可 upsert `project_pos`（note 帶 `u-inlex;review`）再抽 gate sample。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex/label_part1.tsv` | 400 列已填 pos |
| `data/pos/audit/u_inlex/label_part1_summary.md` | 本摘要 |
