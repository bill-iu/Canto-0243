# u_inlex_top2000_nf2 manual POS label — part2

**File:** `data/pos/audit/u_inlex_top2000_nf2/label_part2.tsv`  
**Universe slice:** in-lexicon still-`u` top2000_nf2 batch part2  
**n:** 400  
**Date:** 2026-07-19  

**Rules:** `n/v/a/r/x` multi-ok（comma 按 a,n,r,v,x 字母序）；`u` only fragment/unclear；`family=idiom` 僅真熟語；`voice` 全空；`note` 只標 `u` 理由。

## Counts

| pos bucket | n | % |
|------------|--:|---:|
| formal（非 u） | 399 | 99.75% |
| `u` fragment/unclear | 1 | 0.25% |
| **total** | **400** | 100% |

| family | n |
|--------|--:|
| empty | 381 |
| `idiom` | 19 |
| voice non-empty | 0 |

### Formal tag hits（multi 計入每個 tag；一列可多 hit）

| tag | hits |
|-----|-----:|
| n | 256 |
| v | 126 |
| a | 92 |
| r | 22 |
| x | 13 |
| multi rows | 105 |

## `u` patterns（1）

| pattern | n | examples |
|---------|--:|----------|
| 合成詞殘字 | 1 | 踊 |

**Full `u` list (1):** 踊（踊躍殘字）

## `family=idiom`（19）

| literal | pos |
|---------|-----|
| 一無所有 | a,v |
| 想方設法 | v |
| 恭喜發財 | x |
| 鋪天蓋地 | a,r |
| 不顧一切 | a,r |
| 一目瞭然 | a |
| 理直氣壯 | a,r |
| 深入人心 | a,v |
| 從頭到尾 | r |
| 出人意料 | a |
| 拳打腳踢 | v |
| 按捺不住 | a,v |
| 火上加油 | v |
| 輕舉妄動 | v |
| 五花八門 | a |
| 甜言蜜語 | n |
| 大街小巷 | n |
| 不言而喻 | a |
| 別有用心 | a |

未標 idiom（固定但非成語桶）：親朋好友`n`（並列稱謂）、下定決心`v`（能產動短）、大打折扣`v`（能產）、隨處可見`a,v`（能產）、新年快樂`x`（節日套語）、免責聲明`n`（法律套語）、由此可見`r,x`（篇章標記）。

## Formal patterns worth keeping

- **專名／地名／品牌 → n**：呼和浩特、少林寺、黎巴嫩、別克、哥倫比亞、保時捷、羅湖、印度、共產黨、大同、尼日利亞、青藏高原、羅馬尼亞、委內瑞拉、三國演義、星際爭霸、諾貝爾獎、馬拉多納
- **粵語常用**：不知所謂、乜料、使錢、傻更更、兩公婆、凍冰冰、口快快、唔知醜、嘜、坑渠、埋去、大褸、估唔到、吊頸
- **擬聲／語氣 → x**：呼呼、兮、恭喜發財、新年快樂
- **連／介／助／篇章 → x**：抑、那般、可謂、固然、由此可見、多久、沒什麼
- **科技／政經 NP → n**：壓縮機、風險管理、私營企業、信息產業、平面設計、污水處理、程序設計、投資銀行、資料庫、域名註冊、財務報表

## Borderline（已標 formal；可再審）

| literal | pos | note |
|---------|-----|------|
| 甄／敖／鈺／培 | n 或 n,v | 多專名用字；非純殘則留 formal |
| 抑 | v,x | 抑制／文言「抑或」兩棲 |
| 見鬼 | a,v,x | 形／動／咒罵語氣 |
| 喪 | a,n,v | 喪事／喪失／喪氣 |
| 將要 | r | 近體標記；未 multi v |
| 無妨 | a,r | 述謂／情態 |
| 單方面 | a,n,r | 形／名／副皆常見 |
| 前瞻 | a,n,v | 前瞻性／前瞻力／前瞻 v |
| 三大 | a,n | 「三大…」定語／並列；未加 x |
| 恭喜發財 | x | 節日套語；family=idiom |
| 口爆 | n,v | 俚俗；名／動兩棲 |

## Policy notes

1. **唔造 POS**：合成詞殘字（踊）一律 `u`。
2. **multi 從嚴**：只標兩棲皆常見者；comma 按 a,n,r,v,x。
3. **family**：僅真成語／固定熟語標 `idiom`；能產短語、政經 NP、法律套語 family 空。
4. **voice**：本批無語態對，全空。
5. **下一步**：與 part1／3–5 合併後可 upsert（note 帶 `u-inlex-nf2b;agent-label;review`）再抽 gate sample。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex_top2000_nf2/label_part2.tsv` | 400 列已填 pos |
| `data/pos/audit/u_inlex_top2000_nf2/label_part2_summary.md` | 本摘要 |
