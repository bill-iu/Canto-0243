# u_inlex still-u manual POS label — part5

**File:** `data/pos/audit/u_inlex/label_part5.tsv`  
**Universe slice:** in-lexicon still-`u` batch part5  
**n:** 400  
**Date:** 2026-07-19  

**Rules:** `n/v/a/r/x` multi-ok（comma 按 a,n,r,v,x 字母序）；`u` only fragment/unclear；`family=idiom` 僅真熟語；`voice` 全空。

## Counts

| pos bucket | n | % |
|------------|--:|---:|
| formal（非 u） | 400 | 100% |
| `u` fragment/unclear | 0 | 0% |
| **total** | **400** | 100% |

| family | n |
|--------|--:|
| empty | 397 |
| `idiom` | 3 |
| voice non-empty | 0 |

### Single-tag breakdown

| pos | pure single |
|-----|------------:|
| n | 158 |
| v | 68 |
| a | 48 |
| r | 7 |
| x | 12 |
| multi (≥2) | 107 |
| u | 0 |
| **total** | **400** |

### Formal tag hits（multi 計入每個 tag；一列可多 hit）

| tag | role | examples |
|-----|------|----------|
| `n` | 名物／專名／處所 | 空檔、財政部、巴基斯坦、紅樓夢、叉燒包、東涌、茶樓 |
| `v` | 動詞／動短 | 翻學、落樓、買嘢、掛機、執嘢、暈低、行過嚟、試吓 |
| `a` | 形容／狀態 | 粗暴、香噴噴、麻麻、古惑、硬頸、百厭、穩陣、口窒窒 |
| `r` | 副詞 | 遲下、大都、不光、不免、不妨、無從、幸虧 |
| `x` | 虛（助／嘆／連／擬聲） | 好呀、以至、加之、因而、換言之、轟隆、咯咯、嗡 |
| multi | 兩棲常見 | 覺悟 n,v；都好 a,r；着數 a,n；橫 a,n,v；得嚟 v,x |

## `u` patterns（0）

本批 ∈ 詞庫、語義可還原，**無**切段／殘字需留 `u`。

## `family=idiom`（3）

| literal | pos | note |
|---------|-----|------|
| 五顏六色 | a | 成語；色彩繽紛 |
| 九唔搭八 | a | 粵語熟語；胡扯／不着邊際 |
| 無可奈何 | a | 成語；無奈狀 |

未標 idiom（固定但非成語桶）：開場白`n`、換言之`x`、基本上能產短語、政經 NP。

## Formal patterns worth keeping

1. **實體／專名 → n**：巴基斯坦、青海、紹興、泉州、東海、東涌、青山、青衣、阿星、俞／郝／韓／龐／潘、紅樓夢、財政部、基本法、教育局、政協
2. **粵語常用 → 清晰單標／dual**：翻學`v`、落樓`v`、買嘢`v`、遲下`r`、麻麻`a`、都好`a,r`、口窒窒`a`、古惑`a`、夠喇`a,x`、幾快`a,r`、得嚟`v,x`、白車`n`、百厭`a`、硬頸`a`、衰嘢`n`、計埋／記翻／試吓`v`、長氣`a`、高質`a`、都得`a,v`、先嚟`v`、入屋`v`、十足十`a,r`、執嘢`v`、搲`v`、暈低`v`、水皮`n`、着數`a,n`、硬食`v`、穩陣`a`、耷`v`、聽落`v`、行過嚟`v`、凈`a,r`
3. **名動 dual → n,v**：覺悟、非禮、號召、轉賬、還款、超頻、貼圖、偷拍、承包、合唱、維修、報名、監管、照射
4. **形名／形副 dual**：長遠`a,n`、動感`a,n`、低調`a,n`、便宜`a,n`、都好`a,r`、不大`a,r`、整整`a,r`、着數`a,n`
5. **擬聲／語氣 → x**：咕嚕、嗒、轟隆、咯咯、嗡、唏、好呀
6. **時刻／數量短語 → n,r／n,x**：舊時、下年、死後、過幾日、半點、幾個字、幾歲

## Borderline（已標 formal；可再審）

| literal | pos | note |
|---------|-----|------|
| 聆／舒／纖／烈／碧／燁 | v／a,n／a | 黏着字根；詞庫單字列，按主義標 |
| 煙海 | n | 多見於「浩如煙海」；仍可名物 |
| 得嚟 | v,x | 補語結構；近虛 |
| 都得 | a,v | 粵「都得」可接受／都必須 |
| 辣雞 | a,n | 網語 laggy／垃圾 |
| 齊人 | n | 古典／專名向；非「齊+人」切段 |
| 下頭 | n,r | 下屬／下方 |
| 橫 | a,n,v | 橫向／橫筆／橫過 |
| 依照 | v,x | 介引向；可再收窄 x |
| 炮／申／載／證／謝 | n,v | 多義單字，兩棲皆常見 |

## Policy notes

1. **唔造 POS**：本批無主謂截斷／殘字，故 `u=0`。
2. **multi 從嚴**：只標兩棲皆常見者；comma 按 a,n,r,v,x。
3. **family**：僅 3 條真成語／粵熟語標 `idiom`。
4. **voice**：本批無語態對，全空。
5. **下一步**：與 part1–4 合併後可 upsert（note 帶 `u-inlex;agent-label;review`）再抽 gate sample。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex/label_part5.tsv` | 400 列已填 pos（overwrite） |
| `data/pos/audit/u_inlex/label_part5_summary.md` | 本摘要 |
