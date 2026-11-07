# 自建詞庫讀音常用度

`data/lexicon/curated_reading_ranks.json` 為每個自建「字面／粵拼」記錄讀音等級，
配合既有 Rime 排序使用。2026-11-06 首次覆核涵蓋 7,996 個讀音，截至 B66（2026-11-07）共 **76,768 個讀音**。
這是讀音選擇的常用程度，並非某個詞語在語料出現多少次。

| 等級 | 排序值 | 本輪數量 |
|------|-------:|---------:|
| 預設 | 0 | 66,395 |
| 常用 | 1 | 10,287 |
| 罕見 | 2 | 83 |
| 棄用 | 3 | 3 |

值越小越優先。沒有加入任意詞頻分數，也沒有把新增詞自動加入 `curated_common.txt`。
搜尋按漢字層、詞語常用度、Essay 詞頻、字幕頻道分布、常用字面加分、讀音等級、字面排序；
等號參考讀音則先比讀音等級。同音異讀查詢維持同字面內純粵拼序。
純文字查詞在合併同字面卡片前亦先按排序選讀音，避免舊列的入庫先後次序蓋過新分級。

## 依據

- `rime-components`：66,935 項沿用 `data/rime/char.csv` 的單字讀音等級，取最大值，與原系統一致。
- `rime-orthographic`：141 項只用明確同字異體對照繼承等級，例如羣／群、藴／蘊。
- `ai-context`：9,692 項由 AI 按完整詞義判斷；包括沒有單字分級的詞級變調、
  或單字分級不能準確代表特定詞語的讀法。每項保留原 `component_rank`、判斷標記及說明。
  這些是維護判斷，沒有標成實測頻率或人類逐項批准。

上游未提供可直接沿用的多字詞常用度；不把 Jieba 的詞形權重或 words.hk 的來源旗標冒充讀音分數。
資料及來源指紋見 [metadata](../data/lexicon/curated_reading_ranks.meta.json)。

| 字面 | 優先讀法 | 保留異讀 |
|------|----------|----------|
| 長於 | `zoeng2 jyu1`（擅長，預設） | `coeng4 jyu1`（比……長，常用） |
| 首尾相連 | `sau2 mei5 soeng1 lin4`（預設） | `sau2 mei2 soeng1 lin4`（常用） |
| 鈾礦 | `jau2 kwong3`（預設） | `jau4 kwong3`（沿用棄用） |
| 烷基 | `jyun2 gei1`（預設） | `jyun4 gei1`（沿用棄用） |
| 懷揣 | `waai4 caai1`（藏於懷中，預設） | `waai4 cyun2`（有詞例支持的又讀，常用） |
| 水磨 | `seoi2 mo6`（磨具名詞，預設） | `seoi2 mo4`（加工／工夫義，常用） |
| 釘住 | `deng1 zyu6`（日常口語，預設） | `ding1 zyu6`（文讀，常用） |
| 校本 | `haau6 bun2`（學校為本，預設） | `gaau3 bun2`（校訂本，常用） |
| 咯血 | `lok3 hyut3`（預設） | `haak3 hyut3`（常用） |
| 空行 | `hung1 hong4`（空白行，預設） | `hung1 hang4`（佛教名詞，常用） |
| 行前 | `hang4 cin4`（出發前，預設） | `haang4 cin4`（走向前方，常用） |
| 鋪位 | `pou3 wai2`（店鋪位置，預設） | `pou1 wai2`（床鋪位置，常用） |
| 強壓 | `koeng5 aat3`（強迫壓制，預設） | `koeng4 aat3`（強大壓力，常用） |
| 盛放 | `sing6 fong3`（花朵盛放，預設） | `sing4 fong3`（容器裝載，常用） |
| 恬淡 | `tim4 daam6`（預設） | `tim5 daam6`（保留又讀，常用） |
| 捻子 | `nin2 zi2`（藥捻、紙捻，預設） | `nim2 zi2`（同義又讀，常用） |
| 廊檐 | `long4 jim4`（文讀，預設） | `long4 jam4`（口語異讀，常用） |
| 錠子 | `ding6 zi2`（預設） | `ding3 zi2`（紗錠又讀，常用） |
| 指縫 | `zi2 fung6`（預設） | `zi2 fung4`（又讀，常用） |
| 嫋娜 | `niu5 no5`（預設） | `niu5 no4`（柔美義又讀，常用） |
| 胼胝 | `pin4 zi1`（預設） | `pin4 dai1`（又讀，常用） |
| 數數 | `sou2 sou3`（數數字，預設） | `sou2 sou2`（數一數，常用） |

「社會保障」的 `wui2`、「處方藥」的 `cyu2` 按詞義採正常讀法；
「利潤率」的 `leot6` 採通行書面讀法。「無縫、巖縫、窗縫」保留名詞 `fung6` 並列常用，
不按單字分級直接棄置該詞義。[縫的名詞讀法](https://cantonese.sheik.co.uk/dictionary/characters/2871/?full=true)
只作核音參考，未複製其釋義。

第九批新增 1,833 筆分級：1,751 筆沿用 Rime（包括 3 筆異體繼承），82 筆另作整詞判斷；
之前 11,356 筆分級逐欄保留。「錠子」參考[教育署建議及紗錠詞例](https://jyut.net/query?q=錠)，
「嫋娜」按[娜的柔美義](https://jyut.net/query?q=娜)分開 `no5`／`no4`，
「胼胝」的[兩個通行讀法](https://jyut.net/query?q=胝)亦分列。
「咿咿呀呀」採[香港學校教材的衣鴉注音](https://www.taipocrgps.edu.hk/wp-content/uploads/2020/05/11may-p6-ws1.pdf)，
「呢喃」則按呢的詞義採 `nei4`，沒有把語氣詞讀法套入整詞。

第十批新增 1,787 筆分級：1,662 筆沿用 Rime 單字分級、6 筆經同字異體繼承、
119 筆按完整詞義、變調或異讀順序判斷；之前 13,189 筆分級逐欄保留。
不以詞語較少見推斷它的正常讀法也罕見，亦不以字典收有異讀就把所有讀法並列首選。

| 字面 | 優先讀法 | 保留異讀 |
|------|----------|----------|
| 生澀 | `saang1 gip3`（日常） | `sang1 gip3`（書面） |
| 蘆蓆 | `lou4 zek6`（日常、教育署建議） | `lou4 zik6`（文讀） |
| 筆墨紙硯 | `bat1 mak6 zi2 jin6`（書面） | `bat1 mak6 zi2 jin2`（硯的變調） |
| 締合 | `dai3 hap6`（教育署建議、文讀） | `tai3 hap6`（白讀、又讀） |
| 螺鈿 | `lo4 din6`（現代正音字典的整詞例） | `lo4 tin4`（較早字典飾物義） |
| 外差 | `ngoi6 caai1`（工作出差） | `ngoi6 caa1`（物理術語） |
| 凹版 | `nap1 baan2`（日常、教育署建議） | `aau3 baan2`、`aau1 baan2`（文讀、又讀） |

分音參考[蓆](https://jyut.net/query?q=蓆)、[硯](https://jyut.net/query?q=硯)、
[締](https://jyut.net/query?q=締)、[鈿](https://jyut.net/query?q=鈿)及[凹](https://jyut.net/query?q=凹)的字典對照；
整詞優先次序由 AI 按本次詞義判斷，未標成實測詞頻。
「閼氏」用[字典明載的燕支讀法](https://jyut.net/query?q=閼) `jin1 zi1`；
「漂白劑」用[漂白義建議音](https://jyut.net/query?q=漂) `piu3`，
「哄人」用[哄騙、安慰義建議音](https://jyut.net/query?q=哄) `hung3`。
這些均按整詞處理，沒有改動原單字音表或其他詞庫的孤字分級。

第十一批新增 1,765 筆分級：1,659 筆沿用 Rime 單字分級、3 筆經同字異體繼承，
103 筆按完整詞義、變調或異讀先後判斷。原有 14,976 筆分級逐欄保留。

| 字面 | 優先讀法 | 保留異讀 |
|------|----------|----------|
| 令妹 | `ling6 mui2`（整詞敬稱） | `ling6 mui6`（文讀） |
| 指畫 | `zi2 waa2`（繪畫名詞） | `zi2 waak6`（指點比畫動詞） |
| 橫笛 | `waang4 dek6`（文讀） | `waang4 dek2`（口語變調） |
| 繾綣 | `hin2 hyun2`（通行整詞） | `hin2 hyun3`（文讀） |
| 校勘學 | `gaau3 ham3 hok6`（教育署建議） | `gaau3 ham1 hok6`（校勘專用詞例） |
| 露餡 | `lou6 haam2`（日常及教育署建議） | `lou6 haam6`（文讀） |
| 吼叫聲 | `haau1 giu3 sing1`（日常及教育署建議） | `hau3 giu3 sing1`（文讀） |
| 重利 | `cung5 lei6`（厚利） | `zung6 lei6`（重視利益） |

「令妹」優先讀法有[香港粵語語料研究的完整詞例](https://edizionicafoscari.it/media/pdf/books/978-88-6969-407-3/978-88-6969-407-3-ch-09_yUfo2wK.pdf)，
沒有以年少女子「妹仔」的 `mui1` 代替敬稱；研究中的出現次數未當成產品讀音分數。
「繾綣」的[完整詞條](https://zh.wiktionary.org/wiki/繾綣)同列 `hyun2`、`hyun3`；
「校勘」的[專用詞例及建議音](https://jyut.net/query?q=勘)亦支持兩種讀法。
「創痛」取[傷口、傷痛義 `cong1`](https://jyut.net/query?q=創)，
「賁門」取[解剖學詞例 `ban1`](https://jyut.net/query?q=賁)，不按創造或賁臨的孤字首選音拼接。

## 維護流程

1. 補詞仍先走提案、整詞核音、六聲碼及明確收錄流程；新增讀音同步加一筆分級。
2. 優先沿用現有等級。需要覆核的整詞例外記作 `ai-context`，寫明詞義或變調依據。
3. `char` 留來源字面，`ingested_char` 記正式入庫字形，兩者共用同一等級。
4. 讀音修正須在批次審核表記錄舊讀音，並同步更新分級及來源指紋。
5. 執行來源覆蓋、排序及兩端一致性檢查；不把待審草稿自動納入正式資料。

後端從同一 payload 的 `data/lexicon/` 載入；舊 payload 缺檔仍回退原單字分級。
PWA 在建置時合併入 `ranking-index.json`，分級檔變動會令建置快取失效；桌面打包亦必須包含此檔。
未列詞語、單字讀音及錨點單字選擇繼續使用原 Rime 資料。


## 第十二批（2026-11-06）

新增 1,728 個讀音分級，原有 16,741 筆逐欄保留。1,542 筆沿用 Rime（其中 1 筆異體繼承），
186 筆按整詞詞義、變調或異讀先後作 AI 判斷。全部 18,469 筆均有分級及依據。

| 字面 | 優先讀法 | 保留異讀或異義 |
|------|----------|----------------|
| 跛行 | `bai1 haang4`（日常行走） | `bo2 hang4`（文讀） |
| 種糧 | `zung2 loeng4`（播種用穀種） | `zung3 loeng4`（種植糧食） |
| 登記簿 | `dang1 gei3 bou2`（日常冊簿名） | `dang1 gei3 bou6`（文讀） |
| 會員卡 | `wui6 jyun4 kaa1` | `wui2 jyun4 kaa1`（詞條記錄變調） |
| 水松 | `seoi2 sung1`（香港軟木材料名） | `seoi2 cung4`（植物種類） |
| 同行者 | `tung4 hang4 ze2`（一同前往） | `tung4 hong4 ze2`（同一行業） |
| 曖昧關係 | `oi3 mui6 gwaan1 hai6`（建議及日常音） | `oi2 mui6 gwaan1 hai6`（現代字典詞例） |
| 首倡者 | `sau2 coeng1 ze2`（建議及日常音） | `sau2 coeng3 ze2`（現代字典文讀） |

「炸薯條」沿教育局完整詞例的 `tiu2`，補足孤字沒有的分級；
「清創、櫟樹、刻蝕」分別按傷口、樹種及侵蝕詞義取 `cong1`、`lik1`、`sik6`，不套用同字的其他詞義。
讀音常用度屬詞級維護判斷，沒有把字典權重、地理普及程度或專業詞語稀疏程度當成讀音頻率。
詳見[第十二批詞義及讀音依據](lexicon-supplement-written.md)。


## 第十三批（2026-11-06）

新增 1,700 個讀音分級；1,503 筆沿用 Rime（其中 3 筆為同字異體繼承），
197 筆按整詞語境、變調或異讀先後作 AI 判斷。全部 20,169 筆均有等級、依據與來源指紋。
18,468 筆舊分級逐欄保持原樣；上批「沖頭」`cung3 tau4` 明記改成 `cung1 tau4`，
分級保留預設並移除舊鍵，不把錯讀當成罕見異讀留存。舊批審核表保持不變。

| 字面 | 優先讀法 | 保留異讀或異義 |
|------|----------|----------------|
| 竹蓆 | `zuk1 zek6`（日常器物名） | `zuk1 zik6`（書面） |
| 右衽 | `jau6 jam6` | `jau6 jam5`（現代字典又讀） |
| 彈球 | `taan4 kau4`（彈動、遊戲） | `daan2 kau4`（玻璃小球） |
| 毛巾被 | `mou4 gan1 bei2` | `mou4 gan1 bei6`（書面本調） |
| 休息廳 | `jau1 sik1 teng1` | `jau1 sik1 ting1`（書面） |
| 跳跳蹦蹦 | `tiu3 tiu3 bang1 bang1` | `tiu3 tiu3 baang6 baang6`（現代又讀） |
| 儀表板 | `ji4 biu2 baan2` | 原字形儀錶板 `ji4 biu1 baan2` |

「緩衝存儲器、睫毛膏、個位數、樹袋熊」等按整詞現行讀法判斷，
不因緩、睫、位、袋的單字等級或缺級而把通用讀音判罕。
「采地、射干」分別沿封邑與植物的完整詞例選 `coi3`、`je6`，不套採取與射擊義。
「儀表板」的兩種字形共用實際入庫字面，`biu2` 優先於計量器字錶的 `biu1`。
後端及 PWA 共 20,427 個字形／粵拼排序鍵逐一相同。
詳見[第十三批詞義、讀音依據及修正紀錄](lexicon-supplement-written.md#第十三批續審2026-11-06)。


## 第十四批（2026-11-06）

新增 1,725 條讀音分級，原有 20,169 筆逐欄保留。
1,506 筆沿用 Rime（含 1 筆異體繼承），219 筆按整詞詞義、變調或異讀先後判斷。
全部 21,894 筆均有分級及來源指紋，沒有把候選字典權重直接當作產品讀音分數。

| 字面 | 優先讀法 | 保留異讀或異義 |
|------|----------|----------------|
| 去核 | `heoi3 wat6`（日常果核義） | `heoi3 hat6`（書面及科學語境） |
| 報名處 | `bou3 meng2 cyu3` | `bou3 ming4 cyu3`（書面） |
| 嵌合體 | `ham3 hap6 tai2` | `ham6 hap6 tai2`（現代習讀） |
| 廳局級 | `ting1 guk6 kap1`（行政級別） | `teng1 guk6 kap1`（日常語音） |
| 梳篦 | `so1 bei6` | `so1 bei1`（現代字典又讀） |
| 腺嘌呤 | `sin3 piu1 ling4`（沿完整嘌呤詞條） | `sin3 piu3 ling6`（正音字典書面組合） |
| 拙著 | `zyut3 zyu3` | `zyut6 zyu3`（現代字典又讀） |
| 肉鴿 | `juk6 gap3` | `juk6 gaap3`（現代字典又讀） |
| 聾啞學校 | `lung4 aa2 hok6 haau6` | `lung4 ngaa2 hok6 haau6`（字典又讀） |

「桀驁不馴」既有 `ngou4` 為現代主要讀法；新增 `ngou6` 直接繼承 Rime 的罕見等級，
沒有只因字面是常用成語就把異讀升為預設。完整多來源庫的搜尋已確認 `ngou4` 仍優先。
「山參、參附湯、茄克、草長鶯飛、臧否人物、詩思」則按植物、音譯、動作、褒貶及構思的整詞語境配音。
後端與 PWA 共 22,171 個字形／粵拼排序鍵逐一相同。
詳見[第十四批讀音依據及驗證](lexicon-supplement-written.md#第十四批續審2026-11-06)。


## 第十五批（2026-11-06）

新增 1,611 條讀音分級，原有 21,894 筆逐欄保留，合共 23,505 筆。
1,433 筆沿用 Rime（含 3 筆同字異體繼承），178 筆按整詞詞義、變調或異讀先後判斷。
詞形來源的權重沒有當作產品讀音分數。

| 字面 | 優先讀法 | 保留異讀 |
|------|----------|----------|
| 酵解 | `haau1 gaai2`（建議音） | `gaau3 gaai2`（現代又讀） |
| 倩女 | `sin6 neoi5`（完整詞例及建議音） | `sin3 neoi5`（現代又讀） |
| 金錠 | `gam1 ding6` | `gam1 ding3`（現代又讀） |
| 外廓 | `ngoi6 kwok3`（建議音） | `ngoi6 gwok3`（現代又讀） |
| 冥界 | `ming5 gaai3`（日常完整詞） | `ming4 gaai3`（文讀） |
| 條件性 | `tiu4 gin2 sing3`（詞級變調） | `tiu4 gin6 sing3`（本調） |
| 膠膜 | `gaau1 mok6`（書面本調） | `gaau1 mok2`（字典語音） |
| 露相 | `lau6 soeng3`（日常） | `lou6 soeng3`（書面） |
| 鐵板釘釘 | `tit3 baan2 deng1 deng1`（日常） | `ding1 ding1`、`ding3 ding1`（文讀） |

「朝乾夕惕、綸巾羽扇、柞絲綢、金行、逐行、並行工程、分子病」按詞義取音，
不直接套用孤字的其他義項。「苯醚」保留中大字庫的 `mai4`，不憑相近字音改成 `mei4`。
全部新舊分級均可追溯依據，後端與 PWA 共 23,801 個排序鍵逐一相同。
詳見[第十五批讀音依據及驗證](lexicon-supplement-written.md#第十五批續審2026-11-06)。


## 第十六批（2026-11-06）

新增 1,535 條讀音分級；原有 23,505 筆逐欄保留，合共 25,040 筆。
1,332 筆沿用 Rime（含 4 筆同字異體繼承），203 筆按整詞詞義、變調或異讀先後判斷。

| 字面 | 優先讀法 | 保留異讀 |
|------|----------|----------|
| 鴨肫 | `aap3 zeon1`（建議本音） | `aap3 san5`（完整詞例語音） |
| 銘心 | `ming5 sam1`（銘記動詞） | `ming4 sam1`（文讀） |
| 鮑魚之肆 | `baau6 jyu4 zi1 si3`（完整詞例建議音） | `baau1 jyu4 zi1 si3`（醃魚義又讀） |
| 茜素 | `sin6 sou3`（染料植物義） | `sin3 sou3`（現代又讀） |
| 黏稠度 | `nim1 cau4 dou6`（既有建議音） | `nim4 cau4 dou6`（本批新增變體，排後） |
| 滴鼻 | `dik1 bei6`（日常） | `dik6 bei6`（現代建議音，保留） |
| 夜靜更深 | `je6 zing6 gaang1 sam1`（夜更） | `je6 zing6 gang1 sam1`（較早字書） |
| 塑料膜 | `sou3 liu2 mok6`（書面） | `sok3 liu2 mok2`（現代語音） |

沒有把 `ming5`、`dik6` 等有效讀法誤判為無據錯音；
「創痕、囊蚴、綸巾、重點班、靜電荷、乾親家」則依完整詞義取音。
「前程萬里、無精打采」的既有字面還原有來源遷移紀錄，不改讀音或碼。
後端與 PWA 共 25,354 個排序鍵逐一相同。
詳見[第十六批讀音依據及驗證](lexicon-supplement-written.md#第十六批續審2026-11-06)。


## 第十七批（2026-11-06）

新增 1,471 條分級，舊有 25,040 個物件逐欄保留，合共 26,511 筆。
新增 1,319 筆直接沿用 Rime 單字等級、6 筆同字異體繼承、146 筆整詞語境或次序判斷。

| 字面 | 優先讀法 | 保留異讀 |
|------|----------|----------|
| 大簷帽 | `daai6 sim4 mou2` | `daai6 jim4 mou2` |
| 捻碎 | `nin2 seoi3` | `nip6 seoi3`、`nim2 seoi3` |
| 新蕾 | `san1 leoi4` | `san1 leoi5` |
| 彌天大禍 | `nei4 tin1 daai6 wo6` | `mei4 tin1 daai6 wo6` |
| 流通券 | `lau4 tung1 hyun3` | `lau4 tung1 gyun3` |
| 聽眾席 | `ting1 zung3 zik6` | `ting3 zung3 zik6` |
| 一日之長 | `jat1 jat6 zi1 coeng4`（才能稍勝） | `jat1 jat6 zi1 zoeng2`（年齡、資歷稍長） |
| 輕騎隊 | `hing1 kei4 deoi6` | `hing1 kei3 deoi6`、`hing1 gei6 deoi6` |

有效的 `nip6`、`leoi4`、`nei4` 不列為錯音；「期冀」用 `kei4 kei3`。
「毛呢」用織物 `nei4`，「焊縫」用 `hon6 fung6`，按整詞義項修正孤字拼接草稿。
後端與 PWA 26,853 個排序鍵逐一相同；「斗車」和「鬥車」仍分別保留料斗及比賽義。
詳見[第十七批依據及驗證](lexicon-supplement-written.md#第十七批續審2026-11-06)。


第十八批新增 **1,464 筆分級**：1,261 筆沿用 Rime 單字等級，203 筆按整詞語境或異讀次序判斷；
之前 26,511 筆分級逐欄保留。所有 27,975 個自建讀音都有等級，
後端與 PWA 的 28,335 個正規化字面／粵拼鍵逐項一致。
「玻璃絲、警笛聲、非處方藥品」採完整詞義的正常讀法，
保留原單字分級在 `component_rank`，另記 `ai-context` 判斷。

「意味雋永」優先 `syun5`，保留 `zeon3`；「踢毽」優先 `jin2`，保留 `gin3`；
「陶塤」優先 `hyun1`，保留 `fan1`；「飛簷翹角」優先 `sim4`，保留 `jim4`。
這些音都有現代字典依據，整詞先後屬 AI 維護判斷；分音連結與完整逐詞紀錄見
[第十八批審核](lexicon-supplement-written.md#第十八批續審2026-11-06)。
「重病纏身」按 `zung6` 優先、`cung5` 常用分列，病仍只採 `beng6`。

「明火執仗」保留既有 `zoeng3` 預設讀法；新增 `zoeng6` 列常用異讀，
與其他詞庫的完整詞條一併驗證排序。[仗的現代分音及兵器義](https://jyut.net/query?q=仗)。

## 第十九批（2026-11-06）

新增 **1,605 筆分級**：1,372 筆直接沿用 Rime、3 筆同字異體繼承、230 筆按完整詞義或異讀順序判斷。
另明示修正第十批「相冊」的 `soeng1 caak3`，原有其餘 27,974 筆詞源及分級逐欄保留。
全部 **29,580 條自建讀音**都有等級；工具與 PWA 的 **29,956 個排序鍵**逐項一致。

「鶉衣百結」優先 `seon4`、「併條機」優先 `bing3`、「受賄人」優先 `kui2`，保留有效異讀。
「心宿」優先星宿義 `sau3`，保留現代俗讀 `suk1`；「簷瓦」優先 `sim4`，
`jim4` 列常用，`jam4` 沿用 Rime 罕見級，沒有誤當成錯音刪除。
「病毒檢測」採 `beng6 duk6 gim2 cak1` 優先，現代習讀 `caak1` 另列常用。

「相冊」照片義的日常變調 `soeng2 caak3` 列預設，書面 `soeng3 caak3` 列常用，
錯誤相互義 `soeng1 caak3` 移除。`soeng2` 優先為 AI 整詞判斷，`soeng3` 有完整詞條注音支持。
詳細分音來源、範圍重審及驗證見[第十九批紀錄](lexicon-supplement-written.md#第十九批續審2026-11-06)。

## 第二十批：完整語境與異讀優先次序

新增 1,810 筆分級：1,587 筆直接沿用 Rime、7 筆經同字異體繼承、216 筆另作整詞判斷。
之前 29,580 筆分級逐欄保留。單字有罕見等級而本詞沒有另行覆核的讀法仍保留該等級，
沒有把所有新收表達一律標為預設。這是讀音常用程度，並非詞形的上游權重。

| 字面 | 優先讀法 | 保留讀法 |
|------|----------|----------|
| 新加坡人 | `san1 gaa3 bo1 jan4` | `san1 gaa1 bo1 jan4` |
| 一併處理／一並處理 | `jat1 bing3 cyu2 lei5` | `jat1 bing6 cyu2 lei5` |
| 一氣渾成 | `jat1 hei3 wan4 sing4` | `jat1 hei3 wan6 sing4` |
| 衣夾 | `ji1 gaap2` | `ji1 gaap3` |
| 轎廂 | `giu6 soeng1`（科技名物） | `giu2 soeng1`、`kiu2 soeng1` |
| 藥捻 | `joek6 nin2` | `joek6 nim2` |
| 一簞食 | `jat1 daan1 sik6`（現代教材） | `jat1 daan1 zi6`（古典名詞異讀） |
| 一瓣心香 | `jat1 baan6 sam1 hoeng1` | `jat1 faan6 sam1 hoeng1` |

「新加坡」的 gaa3 見[教育局中文教材](https://cd.edb.gov.hk/chi/resource/ncs/download/NCS_Chi_Sec_U01.pdf)
與[粵典完整詞條](https://words.hk/zidin/新加坡)，不把變調誤當錯讀。
「轎」的[現代字典對照](https://jyut.net/query?q=轎)有 giu6、giu2、kiu2；
本批排除沒有相應粵音依據的 kiu6，不從變調反推一個本調。
「渾」的[字典對照](https://jyut.net/query?q=渾)也有 wan6 的全滿義，故保留，wan4 優先。
「一簞食」現代 sik6 見[香港中學教材](https://dse.mpep.com.hk/chi200/pdf/ClassicalChinese-2019_trial2.pdf)，
古典名詞 zi6 的考辨見[學者原文](https://www.master-insight.com/article/20930)。
整詞優先順序皆明示為 AI 判斷，並非以上來源直接提供的整詞頻率。

所有新讀音以正式編碼器產生 394052 六聲碼；「一瀉萬里」用距離單位 lei5，
「一夔一契」用古人名 sit3，「一字不易」用更改義 jik6，
「一筆一畫」用筆畫義 waak6。原稿和修訂理由保留在
[第二十批審核表](../data/lexicon/reviews/2026-11-06-written-b20-supplement.tsv)。

## 第二十一批：保留詞級變調與有效現代異讀

新增 1,803 筆分級：1,614 筆直接沿用 Rime、1 筆經明確異體繼承、188 筆另作整詞判斷。
另外修正「不可勝計」原有一筆的讀音及分級，其餘 31,389 筆原分級物件逐欄保留。
新增記錄分為預設 1,536 筆、常用 267 筆；沒有把詞形權重當成讀音常用度。

| 字面 | 優先讀法 | 保留讀法 |
|------|----------|----------|
| 上籃得分 | `soeng5 laam2 dak1 fan1` | `soeng5 laam4 dak1 fan1` |
| 不分首從 | `bat1 fan1 sau2 cung4` | `bat1 fan1 sau2 zung6` |
| 一騎當千 | `jat1 kei3 dong1 cin1` | `jat1 gei6 dong1 cin1`、`jat1 kei4 dong1 cin1` |
| 不忮不求 | `bat1 zi3 bat1 kau4` | `bat1 gei6 bat1 kau4` |
| 世風澆薄 | `sai3 fung1 hiu1 bok6` | `sai3 fung1 giu1 bok6` |
| 丁腈橡膠 | `ding1 cing1 zoeng6 gaau1` | `ding1 zing1 zoeng6 gaau1` |
| 丙腈 | `bing2 cing1` | `bing2 zing1` |
| 喜不自勝 | `hei2 bat1 zi6 sing3`（保留整詞來源） | `hei2 bat1 zi6 sing1`（承受義） |

[上籃的 laam2](https://www.cantonese.sheik.co.uk/dictionary/characters/617/?full=true)
是有完整詞例的變調，沒有因單字分級缺音就刪去。
[腈的 cing1、zing1](https://jyut.net/query?q=腈)都有現代粵音字典根據，
不能因 cing1 也讀作氰便誤判錯音；[澆的 giu1](https://jyut.net/query?q=澆)亦明列薄義，
與 hiu1 一同保留。[忮的 gei6](https://jyut.net/query?q=忮)有嫉忌義根據，不當成無據異音。
「不分首從」[cung4／zung6](https://jyut.net/query?q=從)分別有現代詞典及教育署主從讀法支持。
以上整詞先後次序為 AI 維護判斷，來源並未提供實測的整詞讀音頻率。

「下切侵蝕」的 sik6、「不甚瞭解」的 liu5、「不暇顧及」的 haa6、
「不能緩和」的 wun6 均按正常詞義及教育署建議覆核，沒有機械沿用字級罕見標籤。
「不害臊」用 sou3、「不置褒貶」用 bou1、「不龜手藥」用 gwan1、
「不豐不殺」取減少義 saai3；草稿及修正理由見[本批審核表](../data/lexicon/reviews/2026-11-06-written-b21-supplement.tsv)。

## 第二十二批整詞順序

新增 **1,781 筆分級**：1,561 筆直接沿用 Rime、2 筆經同字異體繼承、218 筆作整詞語境判斷。
前 33,193 筆分級物件逐欄保留，新增為預設 1,566 筆及常用 215 筆。

| 字面 | 優先讀法 | 保留讀法 |
|------|----------|----------|
| 二妹 | `ji6 mui2` | `ji6 mui6` |
| 二級域名 | `ji6 kap1 wik6 ming4` | `ji6 kap1 wik6 meng2` |
| 乙未年 | `jyut6 mei6 nin4` | `jyut3 mei6 nin4` |
| 久旱不雨 | `gau2 hon5 bat1 jyu6` | `gau2 hon5 bat1 jyu5` |
| 五棓子 | `ng5 bui6 zi2` | `ng5 pui5 zi2` |
| 人溺己溺 | `jan4 nik6 gei2 nik6` | `jan4 nik1 gei2 nik1` |
| 交角券 | `gaau1 gok3 hyun3` | `gaau1 gok3 gyun3` |
| 事出肘腋 | `si6 ceot1 zaau2 jik6` | `si6 ceot1 zau2 jik6` |

[乙的 jyut6／jyut3](https://jyut.net/query?q=乙)、[棓的藥名 bui6／pui5](https://jyut.net/query?q=棓)、
[溺的淹沒義 nik6／nik1](https://jyut.net/query?q=溺)、[券的 hyun3／gyun3](https://jyut.net/query?q=券)
均有現代字書根據，沒有因單字罕見標籤便誤刪。
「二妹 mui2」另有[香港粵語語料親屬詞研究](https://edizionicafoscari.unive.it/media/pdf/books/978-88-6969-407-3/978-88-6969-407-3-ch-09_yUfo2wK.pdf)完整詞音支持；
mui1 女孩子泛稱未有二妹整詞根據，本批不擴入。
「久旱不雨」先列降雨動詞 jyu6，保留無雨述語 jyu5；整詞讀法及先後為 AI 語境判斷。
中華新字典明列拱券義 hyun3，交角券以此排前，gyun3 異讀保留。
丹參酮、主觀輪廓、亂吼、井底蛤蟆、交流腐蝕按正常詞義覆核，沒有機械沿用單字罕見等級。

詳見[第二十二批審核表](../data/lexicon/reviews/2026-11-06-written-b22-supplement.tsv)及
[補詞紀錄](lexicon-supplement-written.md)。

## 詞語本身常用度（2026-11-06）

本表只表示同一字面的讀音順序。另見[詞語常用度與冷僻退回](lexicon-word-usage-design.md)：全部 38,065 個自建字面另有分級，詞語常用度先決定跨字面結果次序，讀音分級再決定同一詞的異讀先後。2,051 個冷僻表達退回後，歷史讀音證據繼續留檔，不視作錯音。

## 第二十三批讀音分級

新增 1,325 條讀音，舊有 34,974 個分級物件不變。現有等級為預設 32,059／常用 4,156／罕見 81／棄用 3；這些是歷史來源讀音總數，冷僻詞的有效收錄另由詞語常用度控制。按整詞覆核人質 zi3、仗勢 zoeng6、伺機 zi6、佣金 jung2、依傍 bong6、侵蝕 sik6；不因孤字罕見標籤把正常語境讀音排後。佳茗 ming4 保留現代字書又讀，列常用級。

「以正視聽」ting3 有粵典完整詞例；ting1／teng1 是依視聽整詞異讀保留的 AI 組合，來源與推論分開註明。住宅 zaak2／zaak6、併 bing3／bing6／ping3、票券 hyun3／gyun3 均按現代依據保留，主次另列，不能只憑單字或國語聲調刪除異讀。詳見[本批審核表](../data/lexicon/reviews/2026-11-06-written-b23-supplement.tsv)。

## 第二十四批讀音及一項舊排序調整

新增 1,057 條讀音。倒的反向／反而義 dou3 與傾倒 dou2、請假 gaa3 與虛假 gaa2、處分 cyu2 fan1（B65 詞級覆核修正）、和約 wo4 joek3 按整詞分清。家具 geoi6 與商店行 hong4、像素數的數 sou3、充滿著的著 zoek6 均保留原稿作對照。兄弟姐妹依 CantoDict 完整詞例保留 ze2 mui6，並列姐妹 mui2 變調；不把姊字 zi2 機械搬到姐字。

傳奇 zyun6／cyun4、倦怠感 toi5／doi6、倩人捉刀 sin6／sin3 有現代字書依據，分級為主要／常用異讀。倦怠的 doi6 雖被單字資料標為棄用，現代商務及教育署仍列又讀，故不能直接判錯。倚官仗勢 zoeng6、倚山傍水 bong6、偷溜走 liu1、偽劣／優劣 lyut3、充當人質 zi3 另按整詞覆核。

「優惠券」已有 gyun3 預設級，新增 hyun3 若同級會因粵拼字序仍把 gyun3 排先；本批明示把舊 gyun3 改為常用級，保留為有效異讀，日常 hyun3 優先。其餘 36,298 個舊分級物件不變，所有舊詞源列及讀音保留。詳見[一項舊分級調整表](../data/lexicon/reviews/2026-11-06-written-b24-existing-reading-grades.tsv)及[本批審核表](../data/lexicon/reviews/2026-11-06-written-b24-supplement.tsv)。

## 第二十五批：整詞詞義與有效異讀

再加 776 組讀音，37,356 個舊分級物件逐欄保留。兒女親家的 `can3` 按現代字書的親家義作正常整詞讀法，沒有因單字表標為罕見便排後。

- 「兒童玩具」採整詞玩具 `wun6 geoi6`，撤回初審把單用動詞玩 `waan2` 搬入名詞的判斷。[整詞詞例](https://cantonese.sheik.co.uk/dictionary/words/1147/)
- 「公筷母匙」完整詞條列 `si4`，同時保留現代字書湯匙義的 `ci4` 組合為次讀；後者整詞組合與先後為 AI 判斷，沒有冒稱完整詞條載錄。[完整詞條](https://cantonese.sheik.co.uk/dictionary/words/44474/)、[匙的詞義讀音](https://jyut.net/query?q=匙)
- 「兩粒裝、六粒裝」`nap1` 優先，有現代字書支持的 `lap1` 又讀保留。[粒的讀音](https://jyut.net/query?q=粒)
- 「公使團」使為外交官義 `si3`；「兵多將廣」將領 `zoeng3`；「典當行」商店 `hong4`；「八斤重、六斤重」重量 `cung5`，均按整詞語境核對。[使](https://jyut.net/query?q=使)、[將](https://jyut.net/query?q=將)、[行](https://jyut.net/query?q=行)、[重](https://jyut.net/query?q=重)

以上讀音次序獨立於詞語本身常用度，沒有靠提高詞語等級來代替讀音選擇。詳見[本批審核](../data/lexicon/reviews/2026-11-06-written-b25-supplement.tsv)及[驗證記錄](../data/lexicon/reviews/2026-11-06-written-b25-validation.json)。

## 第二十六批：以完整詞例覆核草稿

新增 678 組讀音，全部 38,132 個舊分級物件逐欄保留。單字未列、或標為罕見，均不能直接證明整詞讀音錯誤；同樣地，字形校正必須同步校正字音與 0243 碼。

- 「再試一下」的下按動作次數用 `haa5`；「冠帽」帽子義冠 `gun1`，與「冠絕一時」的 `gun3` 分開。[下](https://jyut.net/query?q=下)、[冠](https://jyut.net/query?q=冠)
- 「准入條件」保留詞級變調 `gin2` 優先及 `gin6` 本調；「出示證件」用完整證件詞音 `gin2`。不能因單字表缺少變調便改成另一音。[條件](https://words.hk/zidin/條件)、[證件](https://words.hk/zidin/證件)、[條件本調及變調](https://cantonese.sheik.co.uk/dictionary/characters/407/?full=true)
- 「判處刑罰、判處死刑」保留 `cyu5/cyu2/cyu3`：日常 `cyu5` 優先為 AI 判斷，`cyu3` 有完整詞條支持，不能只憑處所義刪除。[判處詞條](https://words.hk/zidin/判處)、[書面 cyu2 詞例](https://cantonese.sheik.co.uk/dictionary/characters/1451/?full=true)
- 「冷眼相覷」保留 `ceoi3/zeoi3`；撤回初審猜作 `keoi3` 的判斷。「冥王」保留 `ming5/ming4` 文白兩讀。[覷](https://jyut.net/query?q=覷)、[冥](https://jyut.net/query?q=冥)
- 「初始密碼」始 `ci2`、「叛亂、叛徒、叛變、叛軍」叛 `bun6`、「別出心裁」心 `sam1`，均同步修正字形、讀音及碼；「制禮作樂」樂取音樂義 `ngok6`。[始](https://jyut.net/query?q=始)、[叛](https://jyut.net/query?q=叛)、[樂](https://jyut.net/query?q=樂)

「划行、划走、划着走」的行船義保留 `waa4/waa1`，與劃線 `waak6` 分開。另七個「划／劃」詞形因既有正規化與舊來源遷移尚待聯同審核，明示暫緩，沒有標為冷僻或宣稱已收錄。[划的不同詞義](https://jyut.net/query?q=划)

詳見[本批審核表](../data/lexicon/reviews/2026-11-06-written-b26-supplement.tsv)及[驗證記錄](../data/lexicon/reviews/2026-11-06-written-b26-validation.json)。

## 待核詞義補審：划／劃與九筆始字讀音

上批暫緩的七個表達已逐項解決：划不來、划動、划進、划進來、划進去、划過來、划過去，共補入自建來源 15 組讀音。划船動作義保留 `waa4/waa1`；划不來保留 `waa4` 優先及 `faa3/waa1` 又讀，整詞先後為 AI 判斷。原有合併庫已載的划不來 `waa4` 也在自建來源記錄，以明示整詞偏好，沒有把它冒稱合併庫的新讀音。[划的詞義與讀音](https://jyut.net/query?q=划)、[划不來整詞讀法](https://en.wiktionary.org/wiki/划不來)

本次另精確核對九筆開放詞典 `始 ci5`：始終不變、始終如一、更始、起始、週而復始、自始至終、善始善終已有 `ci2`，只移除該錯音；初始、由而家開始則替換為 `ci2` 並重算碼，保留字面。沒有全域限制始只能一音，未始的 `ci3` 等其他有依據詞義不受影響。[現代始字讀音](https://jyut.net/query?q=始)、[始終完整詞音](https://words.hk/zidin/始終)、[初始等詞例](https://cantonese.sheik.co.uk/dictionary/characters/506/)

舊 38,810 個自建詞源列及讀音分級物件逐欄不變；九筆舊來源修正與一筆劃不來→划不來字形遷移均另外明示。詳見[十筆既有資料處理表](../data/lexicon/reviews/2026-11-06-written-context01-existing-rows.tsv)、[七項補審表](../data/lexicon/reviews/2026-11-06-written-context01-supplement.tsv)及[驗證記錄](../data/lexicon/reviews/2026-11-06-written-context01-validation.json)。


## 第二十七批

新增 578 組來源讀音；舊 38,825 個分級物件逐欄不變。剛醒採 seng2，副領隊採 deoi2，動彈不得按完整詞例保留 daan6，十九樓恢復 sap6 gau2；不以初判或單字機械拼音否定整詞讀音。保留劣 lyut6、昭 ziu1、剖 pau2 的現代有效異讀，分別排在 lyut3、ciu1、fau2 之後。

前仆後繼的既有 fu6 音明示補進自建來源，與 puk1 異讀一起設定整詞順序；僕字只在此精確詞組恢復仆。正常人質 zi3、瞭解 liu5、副領隊 deoi2 使用整詞級別，不套孤字罕見語義。字形轉換及冷暖快取驗證見[B27 審核與驗證](../data/lexicon/reviews/2026-11-06-written-b27-validation.json)。


## 第二十八批

新增 817 條來源讀音，全部舊 39,403 個分級物件保持不變。本批整詞判斷涵蓋協會 wui2 優先、wui6 保留；參差不一 cam1 優先、caam1 保留；處理／相處 cyu5 優先、cyu2 保留；傢俱 geoi6 優先、keoi1 保留。不把有效現代異讀判成錯音，也不把某個讀音的常用級別當作詞語本身的使用頻率。

卡式／卡帶 kaa1 與卡費／卡面 kaat1 按詞義區分；卷冊、卷首語 gyun3 與卷髮夾 gyun2 按完整詞區分。十成把握、十足把握各保留 baa2 ak1、baa2 ngak1、baang2 ak1，首種優先；口腔黏膜保留 nim1 mok2、nim1 mok6、nim4 mok6。完整語境與字書連結逐項列於[B28 審核表](../data/lexicon/reviews/2026-11-06-written-b28-supplement.tsv)，排序與前 200 項核對見[B28 驗證](../data/lexicon/reviews/2026-11-06-written-b28-validation.json)。


## 第二十九批

新增 659 條來源讀音，全部舊 40,220 個分級物件不變。名片 pin2 日常變調優先、pin3 本調保留；宵夜 je2 依完整詞例設定正常級，不受孤字夜的缺音標籤影響。可緩和的 wun6 wo4、合理要求的 jiu1 kau4 依完整詞音設定正常級，不把孤字的其他語義等級當作整詞罕見。

呱呱墮地的嬰啼用 gu1，保留 waa1；吼起來等的 haau1 白讀及 hau3 文讀均有效；咕嚕咕嚕保留 lou1／lu1，和平相處保留 cyu5／cyu2。含着淚及咬着唇等持續態著讀 zoek6，與口語住的 zyu6 字形、語法分清。具體字書連結列在[B29 審核表](../data/lexicon/reviews/2026-11-06-written-b29-supplement.tsv)及讀音分級理由；[驗證紀錄](../data/lexicon/reviews/2026-11-06-written-b29-validation.json)另核對首選、完整池排序及前 200 項。


## 第三十批

新增 566 條來源讀音，全部舊 40,879 個分級物件不變。哄勸依完整詞例 hung6 優先、有效 hung3 保留；嗓子疼依完整嗓子 song2 優先、現代 song1 異讀保留。嚴格要求的 jiu1 kau4 是要求的正常詞音，不把孤字要的其他語義等級套作整詞罕見。

咽不下 jin3 與咽喉 jin1、品相 soeng3、嗎啡中毒 zung3、單卡 kaat1、請假 gaa3 按完整詞義選音；親屬喪失 song3 與喪禮 song1 分開。電子嗶聲 bit1、嗡嗡 jung1、輕哼唱歌 hang1、書面持續態著 zoek6 均有語境依據。具體理由與字書連結見[B30 審核表](../data/lexicon/reviews/2026-11-06-written-b30-supplement.tsv)，完整池排序及首選核對見[B30 驗證](../data/lexicon/reviews/2026-11-06-written-b30-validation.json)。


## 第三十一批

新增 826 條自建來源讀音，全部舊 41,445 個分級物件不變。國庫券的既有 hyun3 明示補入自建來源，以設定 hyun3 首選、有效 gyun3 又讀排後，避免兩者同級時單靠粵拼字母排序。條件的 gin2 由粵典完整詞例支持，保留 gin6 本調；堂哥哥採 go4 go1 日常讀法，保留 go1 go1 書面又讀。單字表沒有某個變調，不能直接當作整詞讀音錯誤。

國產轎車 giu2 變調優先、giu6 保留；坎坷保留現代 ham1 ho1 與字書 ham2 ho2。塑料／塑膠的 sou3 與有據 sok3、鏈接的 lin2 與 lin4 分別記錄次序。地磅 bong2、地縫及填縫 fung6、方位上 soeng6、代付墊錢 din6 各按語義判斷，墊錢的有效 zin3 又讀仍保留。具體來源見[B31 審核表](../data/lexicon/reviews/2026-11-06-written-b31-supplement.tsv)，首選、完整池及前 200 項核對見[B31 驗證](../data/lexicon/reviews/2026-11-06-written-b31-validation.json)。

同類名詞補核包括文件／軟件／郵件的 gin2 及水位 wai2，均保留原 gin6／wai6 本調。粵典和 CantoDict 完整名詞例支持日常變調，沒有把缺少單字音誤作不合法。

## 第三十二批：按語義保留現代讀法

新增 785 組讀音，每組均有獨立等級；原有 42,271 個分級物件逐欄不變。現共 43,056 組：預設 37,879、常用 5,093、罕見 81、棄用 3。新批沒有僅因單字缺音而把姑丈 zoeng2、大使 si5、硬盤 pun2 或物件名詞變調判成無效讀音。

夜半三更與夜靜更長採 gaang1 日常讀法，保留 gang1 本讀；比率詞尾 leot2、病房 fong2、夾心糖 tong2 亦分列現代首選與本調。夏收夏種 zung3、重量 cung5、價格上漲 zoeng2、過分 fan6、天蠍 kit3、食匙 ci4 及金融崩盤 pun4 按詞義處理。棋步義失着沿用有詞例支持的 zoek6，不與衣着 zoek3 混同。證據、AI 判斷及原草稿見[B32 審核表](../data/lexicon/reviews/2026-11-06-written-b32-supplement.tsv)，實際查詢首選及前 200 項核對見[B32 驗證](../data/lexicon/reviews/2026-11-06-written-b32-validation.json)。

## 第三十三批：嗜好、職銜與完整詞例

新增 935 組讀音，每組均有獨立等級，原有 43,056 個分級物件逐欄不變。現共 43,991 組：預設 38,679、常用 5,228、罕見 81、棄用 3。好為「容易／良好」用 hou2，喜愛嗜好用 hou3；校長、家長及會長為 zoeng2，方位上的上為 soeng6，組織會為 wui2。

完整詞例支持院長 jyun2、動聽 ting3／teng1／ting1、炮製 paau3／paau4、孽 jip6／jit6，均分列優先次序。嫵媚 mou5 mei6、媽咪 maa1 mi4 等完整詞級讀法，不因單字缺音或棄用標記而判錯；孤嶼 zeoi6 與大嶼山專音 jyu4 亦分清。預訂／訂購義採 deng6，另保留 ding3 文讀及 ding6 又讀。細節見[B33 審核表](../data/lexicon/reviews/2026-11-06-written-b33-supplement.tsv)及[B33 驗證](../data/lexicon/reviews/2026-11-06-written-b33-validation.json)。

## 第三十四批：完整詞例優先於單字類推

新增 1,110 組讀音，各有獨立等級，原有 43,991 個物件逐欄不變。現共 45,101 組：預設 39,664、常用 5,353、罕見 81、棄用 3。將軍名詞與象棋動詞均有 zoeng1 整詞支持；將佐等單字語義沒有被機械套入將軍令。射籃 laam2、小便宜 pin4 ji2、小販 faan2、文件 gin2、瓶 ping2 等現代整詞變調保留優先次序。

到的結果補語 dou2 與終點／程度 dou3 依語法分列；不因同字同形便刪掉其中一義。家無長物 zoeng6、將進酒 coeng1、少不經事 siu3、少校 haau6、小學校長 zoeng2、小廚房 cyu4 亦按整詞覆核。寒蟬 sim4／sin4 與射籃 laam2／laam4 分別記錄常用次序；寺 zi6 採詞義建議音，沒有宣稱有字書語音根據的 zi2 一概無效。詞語常用度與這些讀音選擇獨立；細節見[B34 審核表](../data/lexicon/reviews/2026-11-06-written-b34-supplement.tsv)及[B34 驗證](../data/lexicon/reviews/2026-11-06-written-b34-validation.json)。

## 第三十七批：按完整詞義核音並保留有據異讀

本批新增 762 組來源讀音、740 個表達；全部 47,027 個舊讀音分級物件不變。心手相應為 sam1 sau2 soeng1 jing3，心情愉快用 jyu4，性交易的易為 jik6。正字修正時同步對齊粵拼：畢竟的畢 bat1、惡習不改的習 zaap6，兩組正音已有覆蓋，未另加重複詞條。

[咽字書例](https://jyut.net/query?q=咽)分清悲咽／悽咽的聲塞 jit3、咽喉 jin1、吞咽 jin3；[見字義](https://jyut.net/query?q=見)支持情見於色的顯現義 jin6。[粵典着／著](https://words.hk/zidin/着)的書面持續態為 zoek6，忍受着沿此規則，不能以口語住的 zyu6 直接代換。

[昭](https://jyut.net/query?q=昭)以現代建議／習讀 ciu1 先列，保留有字書依據的原讀 ziu1；[狂](https://jyut.net/query?q=狂)以 kwong4 先列，有據 kong4 又讀列後。[湃](https://jyut.net/query?q=湃)的 baai3／paai3 均保留，怒濤澎湃、思潮澎湃採 baai3 優先。[忸](https://jyut.net/query?q=忸)在忸怩有 nau2／nuk6，兩讀保留；[怏](https://jyut.net/query?q=怏)失意不快義保留 joeng2／joeng3，不套自大義 joeng1。[老婆](https://cantowords.com/dictionary/老婆)的妻子義是 lou5 po4，不把名詞變調機械套成 po2。膜的 mok2 有名詞變調依據，未一概判錯；本批解剖名稱以 mok6 列前，沒有憑單字列出所有組合。

固定版本歌詞僅是觀測：快玩、快適、心要等須先辨清跨詞邊界；怕吃苦的 hek6 沒有因語料曾標便升為正式讀音，[字書的吃苦配詞](https://jyut.net/query?q=吃)支持 hek3。上述先後是整詞語境判斷，並非實測整詞讀音頻率；詞語常用度另外記錄。完整草稿、正字、正式音、碼、理由及語料行號見[B37 審核表](../data/lexicon/reviews/2026-11-06-written-b37-supplement.tsv)及[驗證記錄](../data/lexicon/reviews/2026-11-06-written-b37-validation.json)。


## 第三十八批：完整詞例與現代語音分列

新增 854 組來源讀音、779 個字面；舊 47,789 個讀音分級物件逐欄保留。成群結隊 deoi6 已在合併詞庫，本批明示鏡映至自建來源並排在 deoi2 前，避免未設等級的正音被新增異讀搶先。詞語熟悉程度另記錄，不與讀音分級混用。

[慢慢完整詞例](https://words.hk/zidin/慢慢)支持 maan6 maan2／maan6 maan1；[嗎](https://jyut.net/query?q=嗎)的 maa1／maa3 均有現代疑問助詞義，本批句末先列 maa3、保留 maa1，未將 maa1 判錯。[打聽完整詞例](https://cantonese.sheik.co.uk/dictionary/characters/546/?all=true&full=true)有 ting1*3，打聽一下先列 ting1、保留 ting3，不把此處的 ting3 誤當聽眾專音。

[扔](https://jyut.net/query?q=扔)在拋擲義有 wing1 語音與 jing4 文讀；[扛](https://jyut.net/query?q=扛)分肩扛 kong1、兩手抬舉 gong1，普通搬運短語保留並按語境排序。房車賽按完整房車名詞優先 fong2，保留 fong4。懵懂保留 mung2／mung5，懵然無知依字書專義取 mung4。手鋸的 goe3／geoi3 有完整工具配詞；手指畫取藝術名稱 waa2。手倒立按完整手倒立式詞例保留 dou2，不只憑倒字的上下易位義改音。

感到痛苦等感受狀態用 dou3，意料不到先列結果義 dou2、保留文讀 dou3。所累用牽累義 leoi6，不套積累 leoi5；家給人足用現代 kap1，正音已有覆蓋；打腫臉充補全為打腫臉充胖子並同步配 bun6，沒有憑草稿造充肥子。上述先後為明示整詞語境判斷，非實測讀音次數。字書、完整歌詞行號及判斷見[B38 審核表](../data/lexicon/reviews/2026-11-06-written-b38-supplement.tsv)及[驗證記錄](../data/lexicon/reviews/2026-11-06-written-b38-validation.json)。


## 第三十九批：語義專音與完整表達

本批新增 1,254 組來源讀音，各有獨立等級；舊 48,643 個分級物件逐欄保留。詞語常用度另記錄，未以單字的罕見、棄用標記代替整詞語義。

現代字書[扳](https://jyut.net/query?q=扳)的 baan2／paan1 都有拉動、扳轉義，paan1 並非只屬攀登；[拴](https://jyut.net/query?q=拴)有 saan1 與 cyun4 俗讀，俗讀不等於錯音。[LSHK 完整散文詞例](https://cala.hk/assets/CRAT_Appendix2_bystroke_1.5.pdf)明列 man2／man4，抒情散文保留兩讀；[腫瘤](https://words.hk/zidin/腫瘤)的 lau2／lau4 亦按完整詞例保留。[拾級](https://jyut.net/query?q=拾)有 sip3 專讀及 sap6 俗讀，不能誤稱 sap6 只屬拾取；拾級而下先 sip3、sap6 列後。

[拘泥](https://jyut.net/query?q=泥)的固執義 nei6 與泥土 nai4 分開；[拂](https://jyut.net/query?q=拂)輕擦、拂衣為 fat1，不套通弼的 bat6。[拗](https://jyut.net/query?q=拗)的彎折義 aau2 不用爭拗義 aau3；持正不阿的[阿](https://jyut.net/query?q=阿)採徇私、阿附義 o1，非稱呼前綴 aa3。折疊動作正式採摺 zip3，折斷、折價保留折 zit3；批假用休假 gaa3，折衷用 zung1，拱手而降的投降為 hong4，行禮為 hang4。拙著按著作 zyu3 查重，未把書面着的持續態 zoek6 套到著作。

扼 ak1／aak1、拙 zyut3／zyut6 的現代又讀保留並排序；抹按擦拭 maat3、塗抹 mut3 的完整動作分義。原歌詞拋下 haa3、拋字 pau1 未照抄入庫，正式取 paau1 haa6；拾到的 dou2／dou3 則都保留。這些先後是明示整詞語境判斷，非實測讀音頻率。字書、原歌詞行號、草稿、正字及理由見[B39 審核表](../data/lexicon/reviews/2026-11-06-written-b39-supplement.tsv)及[驗證記錄](../data/lexicon/reviews/2026-11-06-written-b39-validation.json)。


## 第四十批：完整詞義、語音與文讀分列

新增 1,174 組來源讀音並逐項設定等級，原有 49,897 個分級物件逐欄保留。完整詞語常用度另記，不把其中一個字的罕見或未知標記直接套到整詞。

[挑](https://jyut.net/query?q=挑)的挑撥義 tiu1／tiu5 均有現代根據；[挾](https://jyut.net/query?q=挾)按夾住 gaap3、hip3／hip6／haap6 及要挾 hip3／hip6 的完整動作分開，不套通浹 zip3。捻線等兩指搓捻動作先列 nin2，保留現代 nim2 與 nip6；[捏](https://jyut.net/query?q=捏)造則先 nip6、保留 nip3，不混同兩個字的語境。[掙](https://jyut.net/query?q=掙)取得報酬先 zaang6、保留完整掙錢的 zaang1 語音；擺脫亦有 zaang6 現代配詞，不誤稱它只屬賺錢。

[探聽](https://jyutdictionary.com/dictionary/entry/探聽)的 ting3／ting1、[推斷](https://jyutdictionary.com/dictionary/entry/推斷)的 dyun6／dyun3 都有現代整詞例。新短語按香港用法先列 ting3、dyun6，並非實測讀音次數。[接聽](https://jyutdictionary.com/dictionary/entry/接聽)電話先列 teng1，ting1 文讀列後，未套聽命 ting3。掀被的被子用 pei5，非被動 bei6；[揹](https://humanum.arts.cuhk.edu.hk/Lexis/lexi-mf/search.php?word=揹)負用 bui3，不沿草擬 bui1。

[捍](https://jyut.net/query?q=捍)疆衞國的 hon6／hon2 與[悍](https://jyut.net/query?q=悍)然的 hon5／hon6 分開；[掰](https://jyut.net/query?q=掰)保留 baai1／maak3，[率](https://jyut.net/query?q=率)的比率義保留 leot6／leot2。揣着按衣內藏物義保留 caai1／cyun2，揣測才列 cyun2／ceoi2；劍鞘義 ciu3 不套鞭鞘的 saau1。判斷與詞例見[B40 審核表](../data/lexicon/reviews/2026-11-06-written-b40-supplement.tsv)及[驗證記錄](../data/lexicon/reviews/2026-11-06-written-b40-validation.json)。

掛斗的斗為載貨車斗 dau2，非格鬥 dau3；字形、讀音及 0243 碼同時修正。排除干擾的干為干擾 gon1，不轉幹部的幹。兩項精確字面還原使解析快取升至 21，舊字面鍵無受影響；原 Essay 掛斗 342 詞頻沿用。


## 第四十一批：按完整詞義保留現代異讀

新增 1,183 組來源讀音並逐項分級；51,071 個既有讀音分級物件逐欄保留。詞語常用度獨立處理，沒有因單字在 Rime 的音未知或罕見，就直接判整詞冷僻。

[摟](https://jyut.net/query?q=摟)抱住義 lau2／lau5、[撬](https://jyut.net/query?q=撬)開義 giu6／hiu3、[攙](https://jyut.net/query?q=攙)扶及混合義 caam1／caam4 均保留並排序。水中取物的撈列 laau4、laau1、lou4，撈外快列 lou1、laau4，不把所有孤字異讀套入每一詞義。撩起先列 liu1，現代字書亦有 liu4 提掀義，未把有效文讀判錯。

[處分完整配詞](https://cantonese.sheik.co.uk/dictionary/characters/78/?full=true)及[粵拼詞表](https://cala.hk/assets/CRAT_Appendix2_bystroke_1.3.pdf)支持 cyu2 fan1／cyu5 fan1；新增撤銷處分、撤職處分不按普通話 fèn 改 fan6。撰寫論文採 zaan6，[擬](https://jyut.net/query?q=擬)具採 ji5；操場上用方位 soeng6，不沿向上 soeng5。[播種](https://jyutdictionary.com/dictionary/entry/播種) bo3 zung2 與[理大摺疊](https://www.polyu.edu.hk/clc/cantonese/phoneticKnowledge/vowel/recognizingVowel/) zip3 dip6 各按完整詞例覆核。

歌詞連串另記完整原文行號，擁到跨相擁／到邊界而退回；歌曲次數及異音不冒充日常頻率。據云的說話義還原云，精確規則增至 80、快取格式 22，無舊鍵遷移。草稿、正式音、正字及先後理由見[B41 審核表](../data/lexicon/reviews/2026-11-06-written-b41-supplement.tsv)及[驗證記錄](../data/lexicon/reviews/2026-11-06-written-b41-validation.json)。

最終詞級覆核：塗脂抹粉依[現代完整配詞](https://jyut.net/query?q=抹)採 mut3，已有讀音查重覆蓋，未加入初稿擦拭義 maat3；該音在其他詞義仍按語境審定。熙來攘往的 [joeng4 完整詞例](https://en.wiktionary.org/wiki/Module:zh/data/yue-word/029)保留，既有[香港字書 joeng5 詞例](https://jyut.net/query?q=攘)亦未刪除。


## 第四十二批：完成語境讀音覆核

本批新增 752 組讀音並配分級，原 52,254 個讀音分級物件逐欄保留。敬上按完整書信詞例用 soeng6；散了架按散架鬆散解體義用 saan2 gaa3。文件／郵件先列 gin2、保留 gin6；整棵樹保留現代 po1／fo2，整衣斂容保留 lim5／lim6，不因孤字等級便把有效整詞讀音刪去。

[斷的現代詞例](https://jyut.net/query?q=斷)區分斷無此事、斷然拒絕的 dyun3 與截開、折斷的 dyun6／tyun5；[斷然的 dyun6 完整詞例](https://cantonese.sheik.co.uk/dictionary/characters/2176/?full=true)亦保留列後。[診斷](https://jyutdictionary.com/dictionary/entry/診斷)的 dyun6／dyun3 均按整詞保留；沒有把該詞的異讀機械套入所有斷字詞。

文人墨客的客 haak3、文如其人的如 jyu4、新陳代謝的陳 can4 及新古典主義末字義 ji6 均與正式字面同步；數數看兩個數皆 sou2，數百人的數為數量 sou3，數算為動詞 sou2。詞語本身常用度與讀音先後獨立處理，來源和 AI 判斷可在[B42 審核表](../data/lexicon/reviews/2026-11-06-written-b42-supplement.tsv)及[驗證](../data/lexicon/reviews/2026-11-06-written-b42-validation.json)追溯。


## 第四十三批：詞級讀音優先與同義異讀

新增 710 組來源讀音並逐項分級；53,006 個既有分級物件逐欄保留。旁聽席保留有完整詞例支持的 ting3／ting1／teng1，書刊雜誌先列 hon2、保留 hon1；旋繞着先列 jiu2、保留 jiu5。會計公司等詞先列日常 wui6，保留字書 kui2，未將字級棄用標籤直接當成完整會計詞的結論。

[着想](https://words.hk/zidin/着想)是 zoek6 soeng2，不按穿著義猜作 zoek3；[晃動](https://cala.hk/assets/CRAT_Appendix2_bystroke_1.5.pdf)為 fong2 dung6，初步推測的 fong6 已撤回。書面報告等文字形式採 min6，書本上、書架上、書桌上的方位上採 soeng6；會員的會 wui6 與會員大會末字的聚會 wui2／wui6 分開。

手不釋卷的 gyun2 完整詞例已有覆蓋，保留現代字書書卷義 gyun3 作較後異讀，未將 gyun3 宣稱為全局錯音。早占勿藥、星占學、星占術的占 zim1 與佔有 zim3 分義；83 項精確還原與快取 23 保持重建一致。正式字面、草稿、讀音、碼及先後理由見[B43 審核表](../data/lexicon/reviews/2026-11-06-written-b43-supplement.tsv)及[驗證](../data/lexicon/reviews/2026-11-06-written-b43-validation.json)。

## 第四十四批終審（2026-11-07）

本批新增 715 組讀音，原有 53,716 個分級物件逐欄不變。杳 miu5 優先、jiu2 保留；有接縫 fung4 優先、fung6 保留；期刊以現代全詞 hon2 優先、hon1 保留。扳手已由其他來源覆蓋 baan2／paan1，不重複收錄；扳機新增 baan1 作較後讀法。不能用孤字的名動詞概括或 Rime 缺項否定有據全詞：盤 pun2 有粵典器皿義，枕戈待旦的 zam2 原有預設等級保留，另收現代動詞 zam3 作較後讀法。

完整結果排序驗證發現大海撈針的新異讀與原 laau4 同級時會因字母序搶前，已按實際常用程度將新增 lou4／laau1 列較少用，laau4 保持優先；較少用不等於錯音或棄用。架空電纜的纜只收 laam6，撤回無現代字書支持的 laam5 推測。正式字面、來源草稿、0243 碼、佐證與分級見[B44 審核表](../data/lexicon/reviews/2026-11-06-written-b44-supplement.tsv)及[驗證](../data/lexicon/reviews/2026-11-06-written-b44-validation.json)。精確字形還原累計 86 項，快取為 24。

## 第四十五批整詞讀音（2026-11-07）

新增 700 組讀音，原有 54,431 個分級物件不變。桌面／樓面的 min2 有完整現代詞例，不能因書面形式讀 min6 便一概剔除，兩者分先後；文件詞的 gin2 優先、gin6 保留，與量詞一件分清。橋墩 dan2、檔案夾 gaap2、檢查一下 haa5 優先，保留有據的文讀或異讀。桀驁採有完整現代詞例的 ngou4；桃脯 pou2／fu2、梳攏 lung5／lung4、糟粕 pok3／paak3 皆保留現代同義異讀。極差採 caa1，不從普通話意義分工推測 caa3。

橫的現代字書 waang4 亦明收不順情理及粗暴義，完整橫徵暴斂詞例亦採 waang4；保留 waang6 作較後異讀，不以 Rime 棄用標籤斷言所有全詞無效。簷的 sim4 優先、jim4 保留，撤回 jam4 草稿。鱗次櫛比保留既有 bei2 優先，新增 bei6 作較後讀法。正式字面、草稿、0243 碼、佐證及先後理由見[B45 審核表](../data/lexicon/reviews/2026-11-06-written-b45-supplement.tsv)及[驗證](../data/lexicon/reviews/2026-11-06-written-b45-validation.json)。機械系統精確字面還原累計 87 項，快取為 25。

## 第四十六批整詞讀音（2026-11-07）

新增 1,070 組讀音，原有 55,131 個分級物件不變。上一批橡膠墊排除 zin3 的判斷過窄，現按中大及完整墊子詞例補回，與 din3 同列通行；字書收錄多寡不能當日常頻率。氣墊床保留 zin2／din2、zin3／din3；毛氈墊先列日常 zin3。每間房的 fong2／fong4、母女的 neoi5／neoi2、歌友會的 wui2／wui6 分先後，沒有把變調當錯音，也沒有保留能力義 wui5。每頁行數的行讀 hong4、數讀 sou3；民族樂派讀 ngok6，氈呢讀 nei4。

現代全詞先於孤字標籤：正當理由先列 dong3，保留有同義完整詞例的 dong1；每盎司維持 words.hk 公版詞表及 Rime 完整盎司 on1 si2 優先，另列有據讀法；死鏈接先列 lin2，保留 lin6／lin4。比肩接踵的 zung2／dung2、毒蠍的 kit3／hit3、枕藉的 zam2／zam3、贅述的 zeoi6／zeoi3 均有現代字書根據，依整詞分先後，不用少用或棄用的孤字標籤一律刪除。正式字面、草稿、六聲碼、佐證及順位見[B46 審核表](../data/lexicon/reviews/2026-11-06-written-b46-supplement.tsv)及[驗證](../data/lexicon/reviews/2026-11-06-written-b46-validation.json)。正規化規則未變，快取維持 25。

## 第四十七批整詞讀音（2026-11-07）

本批逐項完成 1,210 個初選的讀音覆核，退回 9 個不合範圍或太冷的表達；查重後寫入 1,225 組來源讀音，原有 56,201 個分級物件保留。其中沉陷 cam4 haam6 已由其他來源覆蓋，為使其優先於新增 cam4 ham6，顯式鏡像到自建來源並寫入整詞分級；合併後仍只有一個相同三元組，沒有因字級較低而讓較後讀音搶前。

水分子 fan1、濕度水分 fan6，中毒 zung3、組織會 wui2／wui6、數量數 sou3、油量 loeng6、治喪 song3、泳將 zoeng3 按詞義處理。沈的沉靜、下沉義轉通行沉 cam4，非姓氏 sam2；汙的污濁義用 wu1，非鑿地 waa1。泡茶、浸泡為 paau3，泡沫 pou5 有現代字書直接支持；泡芙 paau3 fu4、沙發 saa1 faat3 優先採完整現代詞例。沉溺 nik1／nik6、泛 faan3／faan6、浹背 zip3／gaap3、河鰻 maan6／maan4 保留有據異讀。法蘭 laan4／laan1 為完整詞的文讀與語音，不因 Rime 缺孤字記錄便判錯。

詞級先後與詞語常用度獨立，整詞組合及無實測資料的判斷有明確標記。來源字面、草稿、正式字面、0243 碼及引用見[B47 審核表](../data/lexicon/reviews/2026-11-06-written-b47-supplement.tsv)及[驗證](../data/lexicon/reviews/2026-11-06-written-b47-validation.json)。水煙斗、煙斗兩個精確還原避免錯成鬥；累計 89 項，快取為 27。

## 第四十八批讀音終審（2026-11-07）

新增 1,265 組詞級讀音分級，累計 58,691 組；原有 57,426 個分級物件逐欄不變。整詞先後與詞語熟悉度分開。活頁夾 gaap2、流水聲 seng1、港片 pin2、流動比率 leot2 先列日常音，保留有據文讀；渲染 hyun1、銘 ming5 等現代異讀沒有因孤字較少用而誤刪。

浩浩湯湯改 soeng1 soeng1、温書假 gaa3、湧上來 soeng5；涵意、淡蘭色及溝造改正字後分別重核 ham4、laam4、kau3。奄奄一息 jim1 與渾身解數 gaai2 有完整詞例，沒有按國語猜成 jim2 或 haai6。淡妝濃抹以日常 taam5 優先，保留既有 daam6 文讀及原等級。現代同義異讀的組合和次序標明為 AI 整詞判斷，沒有冒充實測次數。

完整結果池排序、三種模式搜尋、兩端讀音分級與異讀次序、冷／熱快取及新詞庫實際客戶端查詢均見[B48 驗證](../data/lexicon/reviews/2026-11-06-written-b48-validation.json)。全池比對亦發現並修正前端以 UTF-16 排列擴展漢字的既有差異，統一為後端的 Unicode 碼位次序；一般排序及同音異讀排序共 54 個結果池、73,618 條記錄一致。

## 第四十九批整詞讀音終審（2026-11-07）

新增 1,404 組來源讀音分級，累計 60,095 組；原有 58,691 個分級物件逐欄保留。烘焙 hung3 pui4 已由其他來源覆蓋，本批顯式鏡像以寫入整詞等級，與原有 hung3 bui6 分先後；[香港詞例](https://cantonese.sheik.co.uk/dictionary/characters/8748/)支持 pui4，沒有以孤字缺項否定全詞。烘的 hung3 優先，現代 hung1／hung4 按烘乾等具體語境保留，未機械套進所有比喻詞。

滴 dik6／dik1、漲 zoeng3／zoeng2、瀝 lik1／lik6、炫 jyun4／jyun6、灼 coek3／zoek3、瀰 nei4／mei4 均保留有現代同義根據的讀法，按完整詞分先後，未用國語聲調或過窄的孤字義概括刪音。炮烙之刑以現代俗讀 paau3 優先、保留 paau4 文讀；焊上等先列 hon6，保留有現代工程教材索引完整焊接詞例支持的 hon2。教材 PDF 未完成逐頁核實，證據層級在審核紀錄明示。

滋事分子的人物義依[粵典完整詞例](https://words.hk/zidin/份子)採 fan6，精確過濾該詞既有 fan1 錯音，未影響數學、分子結構及水分子的 fan1。濃妝豔抹保留既有日常 maat3 優先，新增 mut3 文讀置後，沒有只憑擦拭／塗抹的孤字概括否定整詞。滿腔熱忱 sam4、瞞天過海 mun4、洩氣 sit3、火花塞 faa1、無彈性 taan4、無印痕 han4 均與正字及詞義同步核對。

正式字面、草稿、0243 碼、現代來源、讀音先後及 AI 判斷理由見[B49 審核表](../data/lexicon/reviews/2026-11-06-written-b49-supplement.tsv)和[既有讀音修正](../data/lexicon/reviews/2026-11-06-written-b49-existing-readings.tsv)。完整主讀音、結果池排序、三種模式、新詞庫客戶端查詢及冷／熱快取見[B49 驗證](../data/lexicon/reviews/2026-11-06-written-b49-validation.json)。

## 第五十批整詞讀音與異讀先後（2026-11-07）

新增 1,244 組來源讀音分級，累計 61,339 組；原有 60,095 個分級物件逐欄保留。牛頓定律以[完整牛頓詞例](https://words.hk/zidin/牛頓)的 deon1 日常變調優先，另保留 deon6 文讀，撤回初審把 deon1 誤限於另一詞義的推測。牛腱採[香港完整詞例](https://www.cantonese.sheik.co.uk/dictionary/words/61258/)的 zin2 優先，保留 gin3 文讀；爺爺奶奶的奶奶依完整親屬詞採 naai4 naai2，不沿兩個奶的孤字 naai5 拼音。

[熱情好客](https://words.hk/zidin/好客)取待客 hou3，與客量高的 hou2 分義；父為子隱取替子隱瞞 wai6；特賣會採活動名詞 wui2／wui6，未加入能力義 wui5。燒賣店先列 maai2、保留 maai6／maai5；燜牛肉先列 man1、保留 mun6；爭的 zang1 文讀與 zaang1 語音按具體整詞分先後。處理 cyu2／cyu5、熨衣 tong3／wan6、彌補 nei4／mei4 等現代讀法保留，組合及無實測順位明示為 AI 判斷。

改字不能沿原音：物救必反的救 gau3 不套入極 gik6；煮豆燃箕的箕 gei1 不套入完整煮豆燃萁的豆莖 kei4。兩項原有正確詞音已覆蓋，沒有補入錯讀。煮茗先列現代建議 ming5，保留茶義 ming4 又讀；要求 jiu1、搖曳 jai6、呢喃 nei4 naam4 及抹灰 mut3 均按完整詞及現代詞義處理，不因孤字較後便把正常全詞列作罕見。

讀音順位與詞語常用度獨立。新增來源、原字／正字、0243 碼及理由見[B50 審核表](../data/lexicon/reviews/2026-11-06-written-b50-supplement.tsv)；全部收錄候選首選音、一般與異讀全池排序、三種模式搜尋、新詞庫實際客戶端查詢及冷／熱快取見[B50 驗證](../data/lexicon/reviews/2026-11-06-written-b50-validation.json)。

## 第五十一批整詞讀音終審（2026-11-07）

新增 887 組讀音分級，累計 **62,226 組來源讀音**；全部 61,339 個舊分級物件保留。狐狸精採[粵典完整詞](https://words.hk/zidin/狐狸精) lei4，沒有憑口語直覺改成 lei2；生命以[完整詞例](https://words.hk/zidin/生命) ming6 優先，既有口語 meng6 同義異讀另列。產科病房以[日常病房](https://words.hk/zidin/病房) fong2 優先，fong4 文讀保留，病一律 beng6。

吼的 hau3、haau1、hau1 均有現代咆哮詞例，不把 haau1 限成注視義而誤刪；玩轉的 zyun3 與 zyun2 有完整詞來源，按整詞先後排列。狹義、狹路的 haap3／haap6、猥褻的 wai2／wui1 亦保留有據異讀。瓦楞 ling4 有現代直接詞例，未臆增 lang4；瑰奇、瑰異取珍奇義 gwai1，不沿玫瑰義 gwai3。逃竄 cyun2 優先、cyun3 文讀較後。

獲益匪淺的匪讀 fei2，字形改正後未保留非 fei1 的錯配草稿。狂風怒號 hou4、玄奧晦澀 fui3 sap1 等按完整詞義分級，不因孤字順位把正常全詞判作罕見。玻璃墊 zin3／din3 及玻璃框 kwaang1／hong1 的日常、文讀先後獨立於詞語常用度。

見[B51 讀音與字形審核](../data/lexicon/reviews/2026-11-06-written-b51-supplement.tsv)及[B51 完整驗證](../data/lexicon/reviews/2026-11-06-written-b51-validation.json)。組合與無實測順位均標明為 AI 判斷；未改舊來源、全局字音或原有詞頻。

## 第五十二批整詞讀音終審（2026-11-07）

新增 **983 組讀音分級**，累計 **63,209 組來源讀音**；原有 62,226 個分級物件保留。甩的[現代字書詞義](https://jyut.net/query?q=甩)區分主動揮擲 seot1 與脫落 lat1，甩乾 seot1 gon1 不沿 lat1 草稿；當作、擔任分別採 dong3、dong1。男生宿舍沿[完整男生](https://words.hk/zidin/男生) sang1，沒有機械套生育 saang1。

盛菜、盛酒先列 sing4；[香港中學生中文詞典的現代同義詞例](https://jyut.net/query?q=盛)亦有 sing6 盛飯、盛湯，因此保留較後，不當錯音刪去。[甲乙](https://jyut.net/query?q=乙)以香港日常 jyut6 優先、jyut3 文讀較後；[發酵](https://jyut.net/query?q=酵)的 haau1／gaau3、[曰](https://jyut.net/query?q=曰)的 joek6／jyut6 亦保留現代同義異讀。白淨淨依[完整白淨](https://words.hk/zidin/白淨)取 zeng6；皮膜以書面 mok6 優先、同義語音 mok2 排後。

病入骨髓 seoi5、白癜風 din6、百媚生 mei6 sang1、皇皇巨著 zyu3 與改正字形同步覆核；病一律 beng6。白茉莉的 lei2／lei6、番薯藤的 syu2／syu4 有完整詞根依據；百年偕老 gaai1 優先、haai4 現代又讀較後。戰犯 faan2、和尚 soeng2 及茄克 gaa1 hak1 按完整詞核對，沒有因孤字缺項把正常整詞列作罕見。

完整字形、碼、依據與順位見[B52 審核](../data/lexicon/reviews/2026-11-06-written-b52-supplement.tsv)和[B52 最終驗證](../data/lexicon/reviews/2026-11-06-written-b52-validation.json)。無實測整詞順位明示為 AI 判斷，與詞語本身的常用度獨立。

## 第五十三批整詞讀音終審（2026-11-07）

新增 **908 組讀音分級**，累計 **64,117 組來源讀音**；原有 63,209 個分級物件逐欄保留。盡其所長的[長](https://words.hk/zidin/長)採專長 coeng4，里為距離 leoi5，相忍為國取目的義 wai6；正字修正同步音節與數字碼。監聽的[聽](https://jyut.net/query?q=聽)保留 teng1／ting1，不加入任憑 ting3。

[睫](https://words.hk/zidin/睫)有現代完整眼睫毛 zit3 詞例，[化妝教學](https://www.cantoneseclass101.com/lesson/absolute-beginner-cantonese-for-every-day-81-10-mustknow-words-about-make-up-products)亦有睫毛液 zit6。本批四個化妝詞採 zit3 先、zit6 後，舊假睫毛 zit3 不動；不把裸字表未列等同整詞無效。[睜](https://jyut.net/query?q=睜)保留 zaang1 語音與 zang1 文讀；[眯](https://jyut.net/query?q=眯)保留 mei1 與同義 mai4，不套灰沙入眼 mai5。[研](https://jyut.net/query?q=研)的細磨義 jin4 有現代研磨、研成細末詞例，另保留 ngaan4 碾磨又讀，不套硯古寫 jin6。

著作、著名、著述與衣着、着色、着重按[著字詞義](https://jyut.net/query?q=著)分音。隸書 dai6／lai6、睥睨 pai5／pei5／bei6、盤子 pun2／pun4 及結膜 mok6／mok2 分別依現代同義詞例保留先後；不按來源字典數量判整詞高低頻。舊冥思苦想 ming5 有[完整詞學術比較](https://www.ny.edu.hk/web/cht/hkbc_journal/HKBC_11th%20Journal/489-583.pdf)支持；瞑思苦想原形較少用，按詞語常用度撤回，沒有改冥字製作新詞源。

字面、讀音、碼、依據與先後見[B53 審核](../data/lexicon/reviews/2026-11-06-written-b53-supplement.tsv)和[B53 最終驗證](../data/lexicon/reviews/2026-11-06-written-b53-validation.json)。無整詞頻率者明示 AI 判斷，與詞語本身的常用度獨立。

## 第五十四批整詞讀音終審（2026-11-07）

新增 **1,000 組來源讀音分級**，累計 **65,117 組**。舊響應者以原證據修正 jing1→jing3；其餘 64,116 個舊分級物件逐欄保留。[響應](https://words.hk/zidin/響應)是回應附和 jing3，不套應該 jing1。轎車僅排除只見舊書的 kiu4 整詞音，保留現代 giu2／giu6／kiu2。[時間](https://words.hk/zidin/時間)兩音 gaan3／gaan1，以及[累積](https://words.hk/zidin/累積)的 leoi6 有完整詞例，不因裸字表分義而刪除。

碌碌取庸碌 luk1，非礦物 luk6；種因、種過及種瓜取種植動詞 zung3；科學論斷取判定 dyun3。私放罪犯以名詞 faan2 先、faan6 文讀後，磅稱的稱採量重器物 cing3。豌豆原有日常 wun2 dau2 明確鏡錄為正常首讀，另保留 wun2 dau6、wun1 dau6；驗證中修正了新增較後讀法會排過舊首讀的問題，沒有增加 runtime 重複詞條。

無實測整詞順位者明示 AI 判斷；同義原讀、語音及異讀保留依據，與詞語本身常用度獨立。完整字形、讀音、0243 碼、依據及驗證見[B54 審核](../data/lexicon/reviews/2026-11-06-written-b54-supplement.tsv)及[B54 最終驗證](../data/lexicon/reviews/2026-11-06-written-b54-validation.json)。

## 第五十五批整詞讀音終審（2026-11-07）

新增 **1,094 組來源讀音分級**，累計 **66,211 組**；原有 65,117 個分級物件逐欄保留。上升的 soeng6 與 soeng5、籠罩的 lung5 與 lung4、競的 ging6 與 ging3 都有現代依據，按完整詞語境排先後，沒有按孤字分義或書目數量刪有效舊音。

[黏](https://words.hk/zidin/黏)的黏貼動詞 nim4、濃黏性質 nim1 分開處理；[粘](https://jyut.net/query?q=粘)是同字異體，香港中學生字典亦有粘住、粘貼 zim1，非粘米一義專用。粘住採 nim4 先、zim1 後，粘結性等性質詞保留 nim1；粘膜炎保留膜 mok6／mok2。[加油](https://words.hk/zidin/加油)的入油義有完整 jau2 詞例，另保留 LSHK 詞表的 jau4；空中加油沒有因 Rime 油字缺2而被判棄用。

管理局長的長採職位 zoeng2，篤學好古的好採喜愛 hou3，篇數、節數採數量 sou3。簿記師 bou6 為記帳行業詞，簿本 bou2 為器物語音；竹簾子 lim4、粗花呢 nei4 與什麼 sam6 mo1 都是現代正常整詞語境，沒有讓裸字等級誤判其讀音罕見。窗簾杆、粗杆依簡體來源的棍棒義採同詞正體桿，gon2 先、gon1 後；竹杆保留杆原字 gon1，沒有換另一表達製作來源。

完整字面、音節、碼、依據與排序見[B55 審核](../data/lexicon/reviews/2026-11-06-written-b55-supplement.tsv)及[B55 最終驗證](../data/lexicon/reviews/2026-11-06-written-b55-validation.json)。未有整詞實測先後者明示 AI 判斷，與詞語本身的常用度獨立。

## 第五十六批整詞讀音終審（2026-11-07）

新增 **1,105 組來源讀音分級**，累計 **67,316 組**；原有 66,211 個分級物件逐欄保留。[紀](https://jyut.net/query?q=紀)的 gei2／gei3 均有現代整詞依據，紀錄下來採3先2後，紀念等詞採2先3後；處分的分採 fan1，處 cyu2 先、現代 cyu5 同義後讀保留。系統診斷保留 dyun3／dyun6；絞斷、綿綿不斷採 tyun5 先、dyun6 後，沒有把所有斷字套同一聲調。

[縫](https://jyut.net/query?q=縫)的開口名詞 fung6 與商務新詞典名詞又讀 fung4 保留；1916年的 fung3 不加入現代候選，也不以罅 laa3 作縫字讀音。素負盛名的盛採顯赫 sing6，寢具被採 pei5，緊接著按[完整接著](https://cantonese.org/search.php?q=接著)採 zoek6；著作 zyu3 不混入接續詞。[絨](https://jyut.net/query?q=絨)採 jung2 語音先、jung4 文讀後；[綴](https://jyut.net/query?q=綴)的連結、組字和裝飾義採 zeoi6 先、zeoi3 現代同義後讀。統計權重採 cung5、緝拿罪犯採 faan2、級長採 zoeng2，音節與0243碼一同核對。

詞語本身的常用度獨立分級；有正常書讀不等於生活高頻，裸字缺少變調讀音也不將完整詞判為棄用。完整字形、讀音、碼、依據與排序見[B56 審核](../data/lexicon/reviews/2026-11-06-written-b56-supplement.tsv)及[B56 最終驗證](../data/lexicon/reviews/2026-11-06-written-b56-validation.json)。

## 第五十七批整詞讀音終審（2026-11-07）

新增 **1,073 組來源讀音分級**，累計 **68,389 組**；原有67,316個分級物件逐欄保留。[緩](https://cantonese.sheik.co.uk/dictionary/characters/2866/)的 wun4 為現代有據異讀，舊32組合併讀音及15條自建來源均保留；新緩詞採 wun6 先、wun4 後，沒有按單字正音表全局刪4。方向縱 zung1、放任及即使義 zung3 分開；重複 cung4 不混入總重的 cung5／zung6，職位 zoeng2 不混入總長度 coeng4。

[繫](https://jyut.net/query?q=繫)鞋帶的打結義有完整 gai3 詞例，hai6 的束縛義也有效，較後保留；繫心／繫懷不套打結音。[繩](https://words.hk/zidin/繩)物件採 sing2 先、sing4 本調後，繩結等固定配詞另判；[繞](https://jyut.net/query?q=繞)採 jiu2 先、jiu5 同義異讀後。[翹](https://cantonese.sheik.co.uk/dictionary/characters/8512/)向上彎曲動作採 kiu3 語音先，kiu4 書讀保留，翹板及翹首固定詞仍用4。

群英薈萃依現代完整詞例保留 kui2／wui6／wai3，沒有把缺乏依據的 wai6 入庫。腐蝕採損傷材料 sik6，不混蝕本虧耗 sit6；聚斂錢財保留 lim5／lim6，縫釦子採 kau3，不憑變調猜出 kau2。完整來源、0243碼和先後見[B57 審核](../data/lexicon/reviews/2026-11-06-written-b57-supplement.tsv)及[B57 最終驗證](../data/lexicon/reviews/2026-11-06-written-b57-validation.json)。讀音先後為整詞語境判斷，與詞語常用度分開。

## 第五十八批整詞讀音終審（2026-11-07）

新增 **968組來源讀音分級**，累計 **69,357組**；原有68,389個分級物件逐欄保留。[聽](https://jyut.net/query?q=聽)的teng1語音、ting1書讀依耳聞及接受意見義排先後，聽從的ting3同義讀法保留較後；[聽覺](https://words.hk/zidin/聽覺)固定感官詞有現代ting3直接詞例，不能套用聽見1刪除。聽裝為馬口鐵罐義ting3，不沿用耳聞teng1。19條舊自建ting3來源覆核後保留，沒有作一律刪音。

[背](https://jyut.net/query?q=背)誦記憶的bui6採先，有現代字典同義背誦詞例的bui3保留後；負載及背面bui3另判。[聞](https://jyut.net/query?q=聞)的man4兼耳聞及嗅聞，不機械套名聞聲譽man6。膜mok6／mok2、粒nap1／lap1、鞋haai2／haai4等有據讀法分列；語音變調不因孤字缺項就當作棄用。聾啞症ngaa2、痙攣lyun4、抹黑mut3 haak1按現代字義覆核讀音分級，詞語常用度獨立處理。

自供狀gung1、自傳式zyun6、自彈taan4、臆度dok6、肥分fan6、能謀善斷dyun3及位置上soeng6按完整詞義判斷。來源、0243碼、先後、語料邊界與排除原因見[B58審核表](../data/lexicon/reviews/2026-11-06-written-b58-supplement.tsv)及[B58最終驗證](../data/lexicon/reviews/2026-11-06-written-b58-validation.json)。

## 第五十九批整詞讀音終審（2026-11-07）

新增 **888組讀音分級**，累計 **70,245組**；原有69,357個分級物件逐欄保留。興致hing3／興起hing1、投降hong4／下降gong3、種植zung3／種子zung2、傷口創cong1／創作cong3、荷槍ho6／荷花ho4、著有zyu3／衣著zoek3依完整詞義處理。舉手表決biu2、良品率leot6、草草率率seot1、草地上soeng6亦修正，不照單字草稿配詞。

[芒果](https://www.cantonese.sheik.co.uk/dictionary/words/3965/)的mong4本調有[理大借詞資料](https://chaaklau.github.io/elw/)完整詞據，新詞mong1日常先、4後，舊芒果樹4保留。參加會議jyu6建議音先，與會完整詞典另有jyu5同義讀法，舊與會者／與會國5亦保留；會議wui2語音先、wui6原讀後。檐sim4／jim4／jam4、茼蒿tong4 hou1／tong4 ou1／tung4 hou1、自縊ai3／ngai3、偕老haai4／gaai1、莞爾wun2／wun5均有現代字義或完整詞據，不因裸字Rime缺項就判棄用。

落泊潦倒依完整詞例bok6，不能套泊船paak3或地名尼泊爾pok3；原譜字音不是核准詞庫讀音。記錄gei3沒有機械混入另一字紀的gei2。來源、0243碼與先後見[B59審核表](../data/lexicon/reviews/2026-11-06-written-b59-supplement.tsv)及[B59最終驗證](../data/lexicon/reviews/2026-11-06-written-b59-validation.json)。詞語常用度與讀音先後獨立處理。

### B60：處理、虛擬與行字的整詞先後

新增470組讀音，70,245個既有分級物件完整保留。「行數」是行列hong4及數量sou3；行俠好義是hang4、喜好hou3；行有行規取行業hong4；行行好取施善hang4，不用行業hong4或剛健貌hong6。處世、處理、處罰的cyu2與cyu5均有現代同義依據，先2後5，不套地方cyu3；虛擬ji5建議書讀先、ji4現代整詞語音後，不能因孤字表缺ji4判棄用。

藥物中毒zung3、藥物製劑zai1、衣着打扮zoek3、血流量loeng6按語義修正。蓮花瓣faan6先baan6後、膜mok6先mok2後、蠶絲被bei2先bei6後、衍生jin2先hin2後、行情看漲zoeng3先zoeng2後；這些較後讀法有現代同義依據。藤傢俱geoi6日常先，完整CantoDict所列傢俱keoi1後，保留三個舊自建物件及四個舊runtime字面；不以單字類推全刪。原有孤詞行將hang6未在此改寫；新增完整行將崩潰／滅亡用現代詞例hang4及較後haang4，舊孤詞須另作來源審核。

廣東歌7個觀測的13段原文已核讀。相處／到、相處／得均跨詞；其餘完整命中按語境採音，歌譜與重複副歌不等於核准音或生活頻率。見[B60審核表](../data/lexicon/reviews/2026-11-06-written-b60-supplement.tsv)及[B60最終驗證](../data/lexicon/reviews/2026-11-06-written-b60-validation.json)。詞語常用度另行分級，不把少用詞自動判作讀音罕見。

B60最終覆核補正：「表妹夫」依完整「妹夫」mui6fu1讀6，不把表妹末字mui2變調搬入組詞內。修正後重新重建完整隔離詞庫及428個首選讀音，重驗冷熱快取、受影響搜尋、網頁端及完整排序池；初次驗證結果另存，最終報告採修正後結果。

### B61：按整詞分義，保留有據的現代異讀

新增626組讀音，全部70,715個舊分級物件原值保留。親善大使用si5先、si3後，草稿sai2屬花錢義；親家can3、見精識精zeng1、計量loeng4、詞彙量loeng6、押解gaai3按語境處理。視聽ting3及ting1都有現代整詞依據；答應daap3jing3是同意承諾，不因應該jing1而誤刪。訂位／訂購deng6口語先、ding3與ding6書讀後；訂正採ding3先，現代整詞ding6後。診斷dyun3建議先，同音字彙1997明列診斷dyun6後；斷層掃描則是截面dyun6。褶裙zip3先、現代褲褶詞例zaap3後，褲縫fung6先、商務新詞典名詞又讀fung4後。

記錄簿bou2先bou6後，複式簿記固定bou6；解剖fau2先、現代pau2後，不採只有早期字書依據的paau2。較後讀法並非錯音，詞語較少用亦不等於讀音罕見。本批新增讀音沒有罕見／棄用級；較少用書面詞另外透過整詞熟悉度排後。

行將原始kaifang讀音hang6已另作精確覆核，修正為hang4、0243碼由23改03；前文將來源寫作Rime不準確，此處更正。只替換該完整字面及讀音，其他hang6用法與長詞均保留。完整來源指紋、全部559個新增表達的首選讀法及網頁／桌面搜尋一致性見[B61最終驗證](../data/lexicon/reviews/2026-11-06-written-b61-validation.json)。

### B62：調、請、說及長字的整詞配讀

新增959組讀音，全部71,341個舊分級物件保留。調整、調校tiu4與調派、調查diu6分開；調配出依調製材料／調配資源保留tiu4及diu6兩種自然用法。請假單／條用假期gaa3；請坐下等自然請求ceng2口語先、cing2書讀後，沒有把有效書讀判作棄用。正式請求與公告保留cing2先。

說唱樂ngok6，說短道長coeng4，話中帶刺zung1，誤報率leot6，謹備菲酌fei2，警察局長zoeng2，豎行hong4。說服教育採現代整詞依據seoi3fuk6，本批沒有憑此批量刪除其他舊來源讀音。測cak1建議先、caak1現代習讀後；券hyun3先、gyun3現代又讀後；證件gin2先gin6後，會員wui2先wui6後；不以裸字級別把正常整詞配讀判成罕見。諄諄zeon1與豌豆wun2有現代詞級依據，詞語較書面另由熟悉度排後。

語云jyu5wan4保持言語之云，不變雲朵之雲；完整字面修復與快取36一併驗證。歌詞跨詞命中、白髮名詞邊界及同曲重複不當獨立詞頻。逐項依據見[B62審核表](../data/lexicon/reviews/2026-11-06-written-b62-supplement.tsv)，全部新增首選讀音及一般／異讀排序比對見[B62最終驗證](../data/lexicon/reviews/2026-11-06-written-b62-validation.json)。

### B63：買賣與財務語境，多音字按整詞分義

新增1,086組讀音。「貴行」「貿易商行」用hong4而非haang4／hong2；賈禍是招致禍患gu2，gwu2現代同義後列，不是姓氏gaa2；賺大錢用金錢cin2，不把錯切大錢的cin4搬入。負擔重、越來越重以重量cung5先，書讀zung6後；負有重任及貴重物品先用zung6。貧鈾彈daan2先、daan6後（B65補正名詞變調），足數sou3非數算sou2，貨幣匯率leot6非草稿leot2，賢相soeng3非互相soeng1。

前批語重情深唯一舊列明列cung4→zung6／5003→5203勘誤，表示言語懇切，原來源及標記保留；72,299個其餘舊來源與分級物件不變。歷史B62審核表保留當時值，本批repair列記錄前後音，驗證可還原輸入指紋。

貯5先2後、轎giu2先giu6及kiu2後、贍sin6先sim6後、券hyun3先gyun3後、舌sit3先sit6後均有現代依據；不收僅早期轎kiu4。贏到口語結果dou2先，完整歌詞dou3後。字面較書面與讀音是否常見分開判斷，新讀音沒有新增罕見／棄用級。豔后修復及快取37一併驗證。逐項依據見[B63審核表](../data/lexicon/reviews/2026-11-06-written-b63-supplement.tsv)，完整新首選及前後端一般／異讀排序見[B63最終驗證](../data/lexicon/reviews/2026-11-06-written-b63-validation.json)。

### B64：動作、轉換與名詞變調按完整詞例覆核

新增1,123組讀音。身中數彈zung3／sou3／daan6分別是擊中、數量及子彈；跨行hong4指業界或行列，躬行hang4指實踐；踩油門jau4不套短詞踩油的末字變調。跳舞會、輔導會、社會的wui2口語先、wui6書讀後，物件gin2先gin6後，車位及首位wai2先wai6後。

轉喻用詞級來源zyun3jyu6，不從單字概括推zyun2；轉圜之地zyun2waan4先、zyun3waan4後，不搬入短詞末字waan1。轉換／轉讓保留現代2與3；轉彎、轉速及轉音按各自完整詞義處理。跨kwaa1先kwaa3後、蹣跚mun4先pun4後、蹦bang1先baang6後，重複詞同音節一致。軋鋼機zaat3為正常配讀，其他軋詞的aat3現代又讀較後；踢棉被保留pei5、bei2及bei6。不把書面詞或技術詞本身較少用等同讀音罕見，本批沒有新增罕見／棄用級。

舊跟上及踏上只精確替換soeng6→soeng5並重算0243碼，原HSK30來源標記1保留；原字面詞表並無粵拼，錯音在匯入配讀產生。單字上、其他上字詞與上升soeng6沒有全局刪音。原有73,386個自建來源與讀音分級物件不變。辣椒乾精確修復及快取38一併驗證。依據見[B64審核表](../data/lexicon/reviews/2026-11-06-written-b64-supplement.tsv)，來源修正與全量首選、前後端排序見[B64最終驗證](../data/lexicon/reviews/2026-11-06-written-b64-validation.json)。

### B65：詞級變調、語義邊界與舊詞讀音修正

新增1,164組讀音。炮彈／導彈、囚犯／逃犯的6→2為有據名詞變調，不能由單字表缺2推論所有詞都是錯音。102個既有名詞候選原值保留，排除表不變。兩個前批過嚴判斷明列修正：新增貧鈾彈daan2日常先，原daan6書讀後；身中數彈保留新聞書面daan6先並補daan2。原始字典完整炮彈／導彈詞例支持變調類別，較長表達的配讀先後為AI判斷，並非實測頻率。前批把二聲一律等同彈奏的敘述以本批覆核為準。

行政處分、停刊處分、停工處分、停業處分、刑事處分的分音精確修正fan6→fan1，新連帶處分亦採cyu2／cyu5 fan1；依據[LSHK完整詞表](https://cala.hk/assets/CRAT_Appendix2_bystroke_1.5.pdf)與[CantoDict處分配詞](https://cantonese.sheik.co.uk/dictionary/characters/78/?full=true)。五項舊來源只改讀音與0243碼，74,504個其他來源物件不變。相應五個分級採預設，另將貧鈾彈6由預設調至常用；其餘74,503個舊分級原值保留，整詞常用度不變。

這ze5語音先、ze2現代詞級／歌詞後、ze3書讀再後，三音都保留。這行hong4；這番話waa6，與外語番話waa2分開。連皮帶肉的帶daai3，非皮帶的詞末變調2。迴腸coeng4用於情緒；逸興hing3非興起hing1；逕行hang4非步行haang4。追到手dou2表成功，進到dou3表到達。名詞量loeng6、數sou3、率leot6按完整搭配判斷，沒有把單字順位當整詞結論。

逛kwaang3先，gwaang6及gwaang3有現代依據後；廟會2／6的有效組合完整保留。逾jyu4通行先jyu6書讀後，逾重cung5先zung6後。返的自由返回動作faan1與固定書面返回／返祖faan2按搭配先後排序，保留另一現代讀法。迫bik1語音先、逼迫義baak1書讀後，迫擊專名只bik1。睫zit6先zip3後、彌撒nei4先mei4後、幄aak1語音先ak1讀音後均按現代依據，不新增只在早期字書見的音。本批新讀音沒有新增罕見／棄用級。

逐項依據見[B65審核表](../data/lexicon/reviews/2026-11-06-written-b65-supplement.tsv)，七個舊決策、五項精確來源讀音修正與六項舊分級調整的前後值、全量首選及一般／異讀排序見[B65最終驗證](../data/lexicon/reviews/2026-11-06-written-b65-validation.json)。

### B66：整詞變調與另一詞義，保留有據讀音

新增1,095組來源分級，累計76,768組；原75,673個分級物件不變。重低音、重型、重力、重傷採cung5語音先、zung6書讀後；重情／重工輕商取重視義zung6，重彈老調取彈奏taan4。既有重估zung6gu2是重＝仲的仍以為義，另補重新評估cung4gu2；不以新義否定舊義。部會首長不能錯切會首再配長短音，那行的行hong4與那怎麼行的可行haang4分開。

酗酒jyu1有原始詞級粵拼及[完整jyu3→1詞例](https://en.wiktionary.org/wiki/酗酒)，並非單字表缺1便判錯。新增heoi3異讀及jyu1詞級鏡像均列常用，既有jyu3優先；新酗酒滋事保留三音。鏡像只補分級，不重複加執行列。酒店傢俱優先geoi6、保留keoi1；醃jip3語音先jim1讀音後；酵粉haau1先gaau3後。郵費付訖gat1為完結義，酒吧街baa1為現代借詞，依整詞覆核改正單字等級誤標的罕見；不新增罕見／棄用級。酒吧女neoi2先5後、付訖gat1先ngat6後均有現代完整配詞依據，長搭配次序屬明列AI判斷。

詞語常用度另排，沒有因讀音預設便提高冷門詞。來源原供讀音、AI配音、原始字級與整詞覆核見[B66審核表](../data/lexicon/reviews/2026-11-06-written-b66-supplement.tsv)及[B66最終驗證](../data/lexicon/reviews/2026-11-06-written-b66-validation.json)。
