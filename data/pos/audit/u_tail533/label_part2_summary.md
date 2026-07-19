# u_tail533 label part2 summary

**File:** `data/pos/audit/u_tail533/label_part2.tsv`  
**Universe slice:** remaining long-tail still-`u` batch part2  
**n:** 102  
**Date:** 2026-07-19  

**Rules:** `n/v/a/r/x` multi-ok（comma 按 a,n,r,v,x 字母序）；`u` only fragment/unclear；`family=idiom` 僅真熟語；`voice` 全空；`note` 只標 `u` 理由；零 Essay freq 亦標 formal 若係實詞。

## Counts

| pos bucket | n | % |
|------------|--:|---:|
| formal（非 u） | 102 | 100% |
| `u` fragment/unclear | 0 | 0% |
| **total** | **102** | 100% |

| family | n |
|--------|--:|
| empty | 47 |
| `idiom` | 55 |
| voice non-empty | 0 |

### Formal tag hits（multi 計入每個 tag；一列可多 hit）

| tag | hits |
|-----|-----:|
| v | 44 |
| a | 41 |
| n | 29 |
| r | 10 |
| x | 4 |
| multi rows | 25 |

### pos distribution（列級）

| pos | n |
|-----|--:|
| v | 27 |
| a | 24 |
| n | 22 |
| a,v | 11 |
| a,r | 4 |
| x | 3 |
| n,v | 3 |
| n,r | 3 |
| r,v | 2 |
| a,v,x | 1 |
| a,n | 1 |
| r | 1 |

## `u` patterns（0）

_None._ 本批無 clause-slice／合成詞殘字／opaque；全數為可獨立實詞或固定熟語。

## `family=idiom`（55）

| pos pattern | examples |
|-------------|----------|
| v | 吃閉門羹、各自為政、吐氣揚眉、唱對台戲、問柳尋花、喜結連理、大吃一驚、好説歹説、妖言惑眾、安守本分、寅吃卯糧、引以為戒、引以為鑑、張燈結彩、扭虧為盈、拋諸腦後 |
| a | 和顏悦色、唇亡齒寒、堅毅不屈、大有可為、天朗氣清、天高氣爽、如坐針氈、學有所長、家喻户曉、家無寧日、密不透風、實而不華、屬垣有耳、工力悉敵、平淡如水、年輕有為、廣為人知、德藝雙馨、悲憤填膺、慧眼獨具、户樞不蠹 |
| a,v | 命懸一線、嗜酒成性、噬臍莫及、坐卧不寧、學有所成、居無定所、屹立不倒、平鋪直敍、心悦誠服、慈悲為懷 |
| a,r | 單人獨馬、密鑼緊鼓、年久月深 |
| n | 定海神針 |
| n,r | 大庭廣眾、字裡行間 |
| r | 常年累月 |
| r,v | 幾經周折 |

未標 idiom（固定但非成語桶）：品質檢查／嚴刑逼供／四散奔逃／地震震級／大好前程／大政方針／大眾運輸／天氣預測／官立學校／尋人啟事／對沖基金／小兒麻痺／平方呎／平等待人／店舖／度身訂造／引體上升／忘我工作／思覺失調／慈善團體／扭力天平 等 NP／能產動短；呃人／唔小心／唔得／喺度／外便／多士爐／太平龍頭／好仔／手頭鬆／我嘅／呢啲／嗰啲 等粵語常用；拉脱維亞 專名；名為／啟程／失聯／嫻熟／實存／復闢／抬頭／拆台 等普通詞。

## Formal patterns worth keeping

- **成語／熟語主軸 → a／v／a,v + idiom**：本批 bulk（四字格與固定熟語）
- **粵語常用 formal：** 呃人`v`、呢啲／嗰啲`x`、唔小心`a,r`、唔得`a,v,x`、喺度`r,v`、外便`n`、多士爐`n`、太平龍頭`n`、好仔`n`、我嘅`x`、手頭鬆`a`、店舖`n`、平方呎`n`
- **專名 → n**：拉脱維亞
- **政經／機構／醫護 NP → n**：對沖基金、官立學校、慈善團體、小兒麻痺、思覺失調、地震震級、大眾運輸、天氣預測
- **名動兩棲 → n,v**：品質檢查、失聯、引體上升
- **形副兩棲 → a,r**：唔小心、單人獨馬、密鑼緊鼓、年久月深
- **定製／狀態 → a,v**：度身訂造

## Borderline（已標 formal；可再審）

| literal | pos | note |
|---------|-----|------|
| 唔得 | a,v,x | 形「唔得」／能願否定／嘆拒 |
| 喺度 | r,v | 處所副／「在／在場」動 |
| 我嘅 | x | 領屬；可單用「係我嘅」；非主謂截斷 |
| 名為 | v | 「名為 X」；未 multi x |
| 失聯 | n,v | 斷聯事態名／失聯動 |
| 度身訂造 | a,v | 定語「度身訂造嘅」／動短 |
| 單門獨户 | n | 户型 NP；未 multi a |
| 大眾 | n | 群眾／品牌兩用皆名 |
| 復闢 | v | ＝復辟異體；動 |
| 坐卧不寧 | a,v | 對齊坐立不安類；述謂／動態 |

## Policy notes

1. **唔造 POS：** 本批無 fragment；若後續 gate 發現 clause-slice 再改 `u`。
2. **multi 從嚴：** 只標兩棲皆常見者；comma 按 a,n,r,v,x。
3. **family：** 僅真成語／固定熟語標 `idiom`；能產動短、政經 NP、粵語封閉類 family 空。
4. **voice：** 本批無語態對，全空。
5. **下一步：** 與 part1／3–5 合併後可 `_apply.py` upsert（note 帶 `u-tail533`）再抽 gate sample。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_tail533/label_part2.tsv` | 102 列已填 pos |
| `data/pos/audit/u_tail533/label_part2_summary.md` | 本摘要 |
