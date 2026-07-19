# u_tail533 manual POS — part3

**File:** `data/pos/audit/u_tail533/label_part3.tsv`  
**Universe:** remaining long-tail still-`u` · part3 · **102** rows  
**Date:** 2026-07-19  

**Rules:** `n/v/a/r/x` multi-ok（逗號、字母序 `a,n,r,v,x`）；`u` 僅真正截斷／殘片；`family=idiom` 只標清晰熟語；`voice` 全空；`note` 只標 borderline／`u` 理由。

## Counts

| bucket | n | % |
|--------|--:|---:|
| formal（≥1 五主類） | 102 | 100.0% |
| still `u` | 0 | 0.0% |
| **total** | **102** | 100% |

### Single-tag vs multi

| pos 模式 | n | % |
|----------|--:|---:|
| `n` only | 21 | 20.6% |
| `v` only | 31 | 30.4% |
| `a` only | 17 | 16.7% |
| `r` only | 2 | 2.0% |
| `x` only | 2 | 2.0% |
| multi（≥2 tags） | 29 | 28.4% |
| `u` | 0 | 0.0% |
| `family=idiom` | 49 | — |
| voice non-empty | 0 | — |
| **total** | **102** | 100% |

### pos distribution

| pos | n |
|-----|--:|
| `v` | 31 |
| `n` | 21 |
| `a` | 17 |
| `a,v` | 8 |
| `r,x` | 7 |
| `n,v` | 5 |
| `a,r` | 2 |
| `n,r` | 2 |
| `a,n` | 2 |
| `r` | 2 |
| `x` | 2 |
| `a,r,v` | 1 |
| `v,x` | 1 |
| `a,n,v` | 1 |

### Tag incidence（row 含該 tag；multi 可重疊）

| tag | rows |
|-----|-----:|
| a | 31 |
| n | 31 |
| r | 14 |
| v | 47 |
| x | 10 |
| u | 0 |
| multi rows | 29 |

## `family=idiom`（49）

| literal | pos |
|---------|-----|
| 拔足狂奔 | v |
| 拿腔作勢 | a,v |
| 指腹為婚 | v |
| 探親訪友 | v |
| 推濤作浪 | v |
| 搖鵝毛扇 | v |
| 據為己有 | v |
| 救火揚沸 | v |
| 敢為人先 | a,v |
| 敵眾我寡 | a |
| 明珠投暗 | v |
| 晴空萬裏 | a,n |
| 更弦易轍 | v |
| 有失遠迎 | v |
| 朋比為奸 | v |
| 望風捕影 | v |
| 杳無人跡 | a |
| 枯燥乏味 | a |
| 桃李滿門 | a,n |
| 橫説豎説 | v |
| 橫躺豎卧 | a,v |
| 欺世惑眾 | v |
| 死氣白賴 | a,r,v |
| 毫髮無傷 | a |
| 水米無交 | a |
| 沉冤得雪 | v |
| 沒精打採 | a |
| 油煎火燎 | a |
| 泰然自得 | a |
| 洋為中用 | v |
| 深受其害 | v |
| 深孚眾望 | a,v |
| 温文爾雅 | a |
| 為人作嫁 | v |
| 為富不仁 | a |
| 為時已晚 | a |
| 為時過早 | a |
| 無以為繼 | a,v |
| 無可指責 | a |
| 無所作為 | a,v |
| 無精打採 | a |
| 無縫接軌 | v |
| 無話可説 | a,v |
| 牛年馬月 | n,r |
| 犁庭掃閭 | v |
| 狼狽為奸 | v |
| 用心險惡 | a |
| 異端邪説 | n |
| 痴心妄想 | a,n,v |

## Formal patterns

1. **成語／熟語 → a/v/a,v + family=idiom**：拔足狂奔、指腹為婚、救火揚沸、朋比為奸、望風捕影、狼狽為奸、温文爾雅、為富不仁、無精打採／沒精打採、痴心妄想
2. **粵語常用**：搞唔掂`a,v`、晚黑`n,r`、死氣白賴`a,r,v`、毛公仔`n`、温書`v`、滴裏嘟嚕`a,r`、生猛海鮮`n`、生蛇`n,v`
3. **名物／術語／專名 → n**：文藝語言、春秋時期、有性雜交、有理函數、有聲書、止咳水、武俠小説、民眾、氣象衞星、水上電單車、消極影響、烏蘭巴託、無名腫毒、物質損耗、特惠關税、環境衞生、環狀軟骨、畢業禮
4. **話頭／連介虛 → r,x／x**：換句話説、比如説、有鑒於此、為什麼／為何／為啥、為了、為止、為此；最為`r`；為主`v,x`
5. **名動 dual → n,v**：正當防衞、正選、減税、準許、生蛇
6. **現代固定短語（非 idiom）**：推倒重來`v`、止跌回穩`v`、汲取教訓`v`、深入生活`v`、熱情接待`v`、明説`v`、改為`v`

## Borderline（已標 formal；可再審）

| literal | pos | note |
|---------|-----|------|
| 推倒重來 | v | 現代固定短語；未標 idiom |
| 無縫接軌 | v | 近成語；已標 idiom |
| 死氣白賴 | a,r,v | 粵固定；多義兩棲 |
| 痴心妄想 | a,n,v | 名／形／動皆見 |
| 為主 | v,x | 「以…為主」核；近 x |
| 最為 | r | 程度標記「最為＋A」 |
| 改為 | v | 改成；亦可再收窄 |
| 生蛇 | n,v | 病名／發病 |
| 牛年馬月 | n,r | 遙遙無期時間；n,r |
| 晴空萬裏 | a,n | 裏／里異體；成語 |

## Policy notes

1. **long-tail 優先 formal**：清晰詞／成語／粵語固定式盡量五主類；唔堆 `u`。
2. **multi 從嚴但允兩棲**：只標皆常見用法。
3. **family／voice**：清晰成語／固定熟語 49 條標 `family=idiom`；voice 全空。
4. **本批無 u**：無真截斷／殘片；fragments 已另列於 `fragments.tsv`。
5. **下一步**：與 part1–2／4–5 合併後可 `_apply.py` upsert（note 帶 `u-tail533`）再抽 gate。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_tail533/label_part3.tsv` | 102 列已填 pos |
| `data/pos/audit/u_tail533/label_part3_summary.md` | 本摘要 |
