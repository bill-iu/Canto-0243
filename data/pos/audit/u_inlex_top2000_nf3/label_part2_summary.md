# u_inlex_top2000_nf3 manual POS label — part2

**File:** `data/pos/audit/u_inlex_top2000_nf3/label_part2.tsv`  
**Universe slice:** in-lexicon still-`u` top2000_nf3 batch part2  
**n:** 400  
**Date:** 2026-07-19  

**Rules:** `n/v/a/r/x` multi-ok（comma 按 a,n,r,v,x 字母序）；`u` only fragment/unclear；`family=idiom` 僅真熟語；`voice` 全空；`note` 只標 `u` 理由。

## Counts

| pos bucket | n | % |
|------------|--:|---:|
| formal（非 u） | 400 | 100% |
| `u` fragment/unclear | 0 | 0% |
| **total** | **400** | 100% |

| family | n |
|--------|--:|
| empty | 188 |
| `idiom` | 212 |
| voice non-empty | 0 |

### Formal tag hits（multi 計入每個 tag；一列可多 hit）

| tag | hits |
|-----|-----:|
| n | 181 |
| a | 142 |
| v | 145 |
| r | 7 |
| x | 7 |
| multi rows | 82 |

### pos distribution（列級）

| pos | n |
|-----|--:|
| n | 151 |
| v | 83 |
| a | 83 |
| a,v | 41 |
| n,v | 18 |
| a,n | 11 |
| a,x | 4 |
| a,r | 3 |
| v,x | 2 |
| r | 1 |
| n,r | 1 |
| r,v | 1 |
| r,x | 1 |

## `u` patterns（0）

_None._ 本批無合成詞殘字／clause-slice／opaque。

## `family=idiom`（212）

本批 rank 切片以四字成語／固定熟語為主（與 nf／nf2 part2 科技 NP 為主的切片不同），故 idiom 比例偏高。

| pos pattern | examples |
|-------------|----------|
| a | 雷霆萬鈞、一相情願、高不可攀、枯燥無味、生龍活虎、三心二意、不可救藥、南轅北轍、囊中羞澀、大公無私、蠻不講理… |
| v | 重見天日、一掃而光、咬緊牙關、過關斬將、小題大做、出爾反爾、一箭雙鵰、畫蛇添足、逼上梁山… |
| a,v | 面不改色、人去樓空、疲於奔命、高枕無憂、廢寢忘食、神出鬼沒、站不住腳、千錘百鍊… |
| n | 飲食男女、文房四寶、金童玉女、老生常談、洪水猛獸、槍林彈雨、清風明月、良辰美景… |
| n,v | 久別重逢、適者生存、驚鴻一瞥、改朝換代 |
| a,n | 別有洞天、歌舞昇平、長治久安、沉默是金、杯水車薪、鐵石心腸、浮光掠影 |
| r / n,r / r,v / r,x | 一年到頭`r`；三更半夜`n,r`；夜以繼日`r,v`；如此而已`r,x` |
| a,r / a,x / v,x | 平心靜氣`a,r`；情何以堪`a,x`、長命百歲`a,x`、百年好合`a,x`；到此一遊`v,x` |

未標 idiom（固定但非成語桶）：五年計劃／文革時期／知識青年／外交關係／電子文件／語音識別／總參謀長／地緣政治／土地改革／高速緩存／勞動教養／紅頭文件／高等法院／十月革命／聚酰亞胺 等政經／科技／機構 NP；刻苦學習／擦亮眼睛／隨地吐痰／雙方同意／搶先一步／親自出馬 等能產動短；堂吉訶德／博茨瓦納／危地馬拉／波多黎各／多米尼克／雲岡石窟／秦始皇陵 等專名。

## Formal patterns worth keeping

- **成語／熟語主軸 → a／v／a,v + idiom**：本批 bulk；述謂偏 a、動態偏 v、兩棲 a,v
- **專名／地名 → n**：堂吉訶德、博茨瓦納、危地馬拉、北愛爾蘭、波多黎各、多米尼克、旅順口區、雲岡石窟、秦始皇陵、新華日報
- **科技／政經／機構 NP → n**：化學纖維、數值分析、路由協議、電磁感應、語音識別、地緣政治、高速緩存、滾動軸承、總領事館、惡意代碼、聚酰亞胺、齒輪傳動
- **褒貶／狀態形容 → a**：嬌弱、闊綽、妖冶、體弱多病、來歷不明、無法替代、不成文
- **動短／能產 → v**：復課、消氣、稱臣、跟從、付諸實施、周遊世界、拜師學藝、掛在嘴上
- **名動兩棲 → n,v**：巡迴演出、國有化、穿着打扮、大量生產、肌肉注射、忌口、雙方同意
- **套語／語氣 → x multi**：到此一遊`v,x`、欲購從速`v,x`、週末愉快`a,x`、百年好合`a,x`、長命百歲`a,x`、情何以堪`a,x`、如此而已`r,x`

## Borderline（已標 formal；可再審）

| literal | pos | note |
|---------|-----|------|
| 一波未平／一波又起 | a,v + idiom | 全式「一波未平一波又起」之半；庫內獨立字面、可單用 → formal+idiom |
| 識時務 | v | 「識時務者為俊傑」截；庫內可單用，未當 fragment |
| 適者生存 | n,v + idiom | 格言／命題；名述謂兩棲 |
| 沉默是金 | a,n + idiom | 格言；定語／命題 |
| 到此一遊 | v,x + idiom | 遊客題字套語 |
| 週末愉快 | a,x | 問候套語；非成語桶 → family 空 |
| 欲購從速 | v,x | 廣告套語；family 空 |
| 辯證論治 | n,v | 中醫術語；非熟語 |
| 羅曼蒂克 | a,n | 音譯；形／名 |
| 必死無疑 | a,r | 述謂／情態副用 |
| 每週一次 | a,r | 定語／頻率 |
| 小幅度 | a,n | 定語／名量 |
| 親眼所見 | n | 偏 NP；未 multi v |
| 革命委員 | n | 歷史職稱殘（非「會」）；仍作 n |

## Policy notes

1. **唔造 POS**：本批無殘字；全 formal。
2. **multi 從嚴**：只標兩棲皆常見者；comma 按 a,n,r,v,x。
3. **family**：僅真成語／固定熟語標 `idiom`；能產短語、政經／科技 NP、專名、廣告／問候套語 family 空。
4. **voice**：本批無語態對，全空。
5. **下一步**：與 part1／3–5 合併後可 upsert（note 帶 `u-inlex-nf3;agent-label;review`）再抽 gate sample。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex_top2000_nf3/label_part2.tsv` | 400 列已填 pos |
| `data/pos/audit/u_inlex_top2000_nf3/label_part2_summary.md` | 本摘要 |
| `data/pos/audit/u_inlex_top2000_nf3/_fill_part2.py` | 本批填標腳本（可覆核） |
