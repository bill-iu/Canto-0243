# u_inlex_top2000_nf manual POS label — part5

**File:** `data/pos/audit/u_inlex_top2000_nf/label_part5.tsv`  
**Universe slice:** in-lexicon top2000 still-`u` · non-fragment batch · part5  
**n:** 400  
**Range:** `甯`…`桃`  
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
| empty | 398 |
| `idiom` | 2 |
| voice non-empty | 0 |

### Single-tag breakdown

| pos | pure single |
|-----|------------:|
| n | 188 |
| v | 75 |
| a | 26 |
| r | 11 |
| x | 4 |
| multi (≥2) | 96 |
| u | 0 |
| **total** | **400** |

### Formal tag hits（multi 計入每個 tag；一列可多 hit）

| tag | rows | % of 400 |
|-----|-----:|---------:|
| n | 257 | 64.3% |
| v | 139 | 34.8% |
| a | 62 | 15.5% |
| r | 25 | 6.3% |
| x | 14 | 3.5% |
| u | 0 | 0% |
| **multi** (≥2 tags) | **96** | **24.0%** |

## `u` patterns（0）

本批 ∈ 詞庫、語義可還原，**無**切段／殘字需留 `u`。

## `family=idiom`（2）

| literal | pos | note |
|---------|-----|------|
| 淋漓盡致 | a,r | 成語；盡情盡致 |
| 不可或缺 | a | 成語式固定；必不可少 |

未標 idiom（固定但非成語桶）：故此`x`、突然間`r`、無可奈何類未出現；粵口語短語（出貓、找數、乞人憎）只填 pos。

## Formal patterns worth keeping

1. **實體／專名 → n**：芝加哥、西寧、包頭、白宮、古巴、敦煌、德國、浙、禹、上官、永樂、西遊記、五糧液、馬刺、科學院、紀念館
2. **姓／名用字 → n**（偶 a,n／a,v）：甯、詹、婭、駿、鈞、煥、沐、筱、冉、黛、瞳、妍、姚、徐、桃
3. **名動 dual → n,v**：節水、摘編、答疑、預售、首映、對陣、放電、刻畫、代購、倉儲、海運、檢察、告警、考查、測繪、連勝、閉幕、調配、選題、朗讀、督導、網戀、疊加、淺析、聽證、致辭、回禮、好轉、感觸、戒、染色、保潔、收發、懸賞、獻血、崇敬
4. **形／形兼 → a／a,***：開放式、迅猛、可持續、夠嗆、無誤、艱鉅、劣質、輕薄、歡快、狹隘、稀缺、勤快、雙邊、亢奮、乞人憎、古舊、多變、太高、妙、嬌、愚蠢、柔弱；`a,n` 圓通、長篇、人際、實名、高產、癡心、五星、至尊、喜慶、例牌、大肚、新婚
5. **副 → r**：亦可、突然間、首度、壓根、屢屢、待會兒、怕是、並未、何嘗、徹夜；`a,r` 過早、婚前、淋漓盡致、無條件、堂堂；`r,v` 總得、不止、兜頭、周街
6. **虛／擬聲 → x**：啦啦、嘖嘖、叄、故此；`v,x` 別看、僅次於、据、似得、單憑、嗤；`n,x` 上一頁、三個字、立方米、呢樣
7. **粵語常用**：一輪嘴`n`、乞人憎`a`、乞兒`n`、企定`v`、似得`v,x`、作狀`v`、例牌`a,n`、做戲`v`、出貓`v`、升班`v`、呢樣`n,x`、周街`r,v`、廁格`n`、影低`v`、後尾枕`n`、得嗰`r`、手板`n`、打丁`v`、打工仔`n`、找數`v`、拋低`v`、擦紙膠`n`、帶眼`v`、兜頭`r,v`

## Borderline（已標 formal；可再審）

| literal | pos | note |
|---------|-----|------|
| 得嗰 | r | 近量限「得嗰（咁多）」；非截斷主謂 |
| 似得 | v,x | 粵口語「似乎」；近虛 |
| 据 | v,x | 據之異體；介引向 |
| 叄 | x | 財務大寫數字；非實義名 |
| 總得 | r,v | 情態「總得…」 |
| 一例 | n,r | 一例／一律兩讀 |
| 絕緣 | a,n,v | 電氣／人際／動詞皆常 |
| 日產 | n,v | 日產量 vs 車廠專名 |
| 圓通 | a,n | 形容 vs 企業名 |
| 楞 | a,v | 愣住／呆 |
| 侃 | v | 亦作名；本批主義聊天 |
| 帶眼 | v | 粵「帶眼識人」詞幹 |
| 太高 | a | 形短語；非「太+高」硬切 u |

## Policy notes

1. **唔造 POS**：本批無主謂截斷／殘字，故 `u=0`。
2. **multi 從嚴**：只標兩棲皆常見者；comma 按 a,n,r,v,x。
3. **family**：僅 2 條真成語／固定熟語標 `idiom`。
4. **voice**：本批無語態對，全空。
5. **下一步**：與 part1–4 合併後可 upsert（note 帶 `u-inlex-top2000-nf;agent-label;review`）再抽 gate sample。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex_top2000_nf/label_part5.tsv` | 400 列已填 pos（overwrite） |
| `data/pos/audit/u_inlex_top2000_nf/label_part5_summary.md` | 本摘要 |
