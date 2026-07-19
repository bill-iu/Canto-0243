# u_inlex still-u manual POS label — part2

**File:** `data/pos/audit/u_inlex/label_part2.tsv`  
**Universe slice:** in-lexicon still-`u` batch part2 (`u_inlex_top2000` 段)  
**n:** 400  
**Date:** 2026-07-19  

**Rules:** `n/v/a/r/x` multi-ok（comma 按 a,n,r,v,x 字母序）；`u` only fragment/unclear；`family=idiom` 僅真熟語；`voice` 全空；`note` 只標 `u` 理由。

## Counts

| pos bucket | n | % |
|------------|--:|---:|
| formal（非 u） | 397 | 99.25% |
| `u` fragment/unclear | 3 | 0.75% |
| **total** | **400** | 100% |

| family | n |
|--------|--:|
| empty | 394 |
| `idiom` | 6 |
| voice non-empty | 0 |

### Formal tag hits（multi 計入每個 tag；一列可多 hit）

| tag | role | examples |
|-----|------|----------|
| `n` | 名物／專名／處所 | 媳婦、越南、遼寧、公屋、比卡超、中環、亞視、豉油、間尺 |
| `v` | 動詞／動短 | 借鑑、善於、玩嘢、翻工、落雨、飲茶、打邊爐、抆、厹 |
| `a` | 形容／狀態 | 可疑、孤單、巴閉、得戚、細膽、詭異、肉麻、貪玩 |
| `r` | 副詞 | 多麼、往後、至今、即管、夾硬、照計、橫掂、跟手、紛紛 |
| `x` | 虛（助／嘆／代／量／連） | 要不然、嘍、凡是、輛、況且、縱使、不但、嗶、嘖 |
| multi | 兩棲常見 | 研製 n,v；嚟緊 r,v；爛口 a,n,v；綜合 a,n,v；樣樣 n,r,x |

## `u` patterns（3）

| pattern | n | examples |
|---------|--:|----------|
| 合成詞殘字（骷髏） | 2 | 骷、髏 |
| 主語 + 仲 + V 截斷 | 1 | 你仲記 |

**Full `u` list (3):** 骷、髏、你仲記

## `family=idiom`（6）

| literal | pos | note |
|---------|-----|------|
| 異口同聲 | a,r | 成語；形／副「齊聲」 |
| 不由自主 | a,r,v | 成語；情態 |
| 難以置信 | a | 成語；述謂形 |
| 話口未完 | r,x | 固定起承；話輪標記 |
| 不約而同 | a,r | 成語 |
| 見牙唔見眼 | a,v | 粵語熟語（笑到／人多） |

未標 idiom（固定但非成語桶）：改革開放`n`（政經專名／時期）、面對面`r,v`（能產）、食花生`v`（網語）、版權所有`n,x`（法律套語）。

## Formal patterns worth keeping

- **專名／地名 → n**：越南、遼寧、瀋陽、珠海、金山、長春、賈、孫、布什、羅馬、中環、亞視、中山、南昌、黃河、太平洋、薛、比卡超
- **粵語常用**：傾得、啞仔、嚟緊、廢青、煙通、爛仔、玩嘢、組爸、翻工、落雨、食花生、即管、夾硬、巴閉、得戚、焗爐、照計、見工、連埋、點先、寫低、幾錢、翻嚟、飲杯、係路、右手面、喱士、嘅時、底衫、手尾、打邊爐、抆、擦字膠、橫掂、睇小、細膽、豉油、跟手、邨、依邊、厹、死八婆、煮飯仔、私隱、間尺、見牙唔見眼
- **擬聲／語氣 → x**：嘍、噓、嚓、嗶、嘖
- **連／量／代 → x**：要不然、凡是、輛、況且、縱使、不但、儂、皆
- **科技／政經 NP → n**：像素、性價比、光驅、交換機、控股、勞動力、改革開放

## Borderline（已標 formal；可再審）

| literal | pos | note |
|---------|-----|------|
| 互 | r | 黏着性強；essay 或作「互相」截；可再審 x |
| 婷／嬋 | n | 多專名用字；非純殘則留 n |
| 習 | n,v | 姓／習近平指稱 + 學習／習慣 |
| 質 | n,v | 質量／質詢 |
| 臺 | n,x | 台／臺灣／量詞義 |
| 先好 | a,r | 粵「你先好」；亦可獨立情態 |
| 點先 | r,x | 頭先義／「點…先」；非主謂截斷 |
| 嘅時 | r,x | 「…嘅時」關係；近虛 |
| 尷 | a | 尷尬截用；粵可單用「好尷」 |
| 許 | n,v,x | 姓／允許／或許 |
| 濟 | a,n,v | 濟南／救濟／濟濟 |
| 版權所有 | n,x | 固定套語；family 未標 |
| 怎麼回事 | x | 整句疑問標記 |
| 食花生 | v | 網語「圍觀」；非成語 family |

## Policy notes

1. **唔造 POS**：主謂／仲+V 截斷、合成詞殘字（骷／髏）一律 `u`。
2. **multi 從嚴**：只標兩棲皆常見者；comma 按 a,n,r,v,x。
3. **family**：僅 6 條真成語／粵熟語標 `idiom`；能產短語、政經專名、網語、法律套語 family 空。
4. **voice**：本批無語態對，全空。
5. **下一步**：與 part1／3–5 合併後可 upsert（note 帶 `u-inlex;agent-label;review`）再抽 gate sample。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex/label_part2.tsv` | 400 列已填 pos |
| `data/pos/audit/u_inlex/label_part2_summary.md` | 本摘要 |
