# 自建詞庫讀音常用度

`data/lexicon/curated_reading_ranks.json` 為每個自建「字面／粵拼」記錄讀音等級，
配合既有 Rime 排序使用。2026-11-06 首次覆核涵蓋 7,996 個讀音，第三十四批後共 **45,101 個讀音**。
這是讀音選擇的常用程度，並非某個詞語在語料出現多少次。

| 等級 | 排序值 | 本輪數量 |
|------|-------:|---------:|
| 預設 | 0 | 39,664 |
| 常用 | 1 | 5,353 |
| 罕見 | 2 | 81 |
| 棄用 | 3 | 3 |

值越小越優先。沒有加入任意詞頻分數，也沒有把新增詞自動加入 `curated_common.txt`。
搜尋按漢字層、詞語常用度、Essay 詞頻、字幕頻道分布、常用字面加分、讀音等級、字面排序；
等號參考讀音則先比讀音等級。同音異讀查詢維持同字面內純粵拼序。
純文字查詞在合併同字面卡片前亦先按排序選讀音，避免舊列的入庫先後次序蓋過新分級。

## 依據

- `rime-components`：41,059 項沿用 `data/rime/char.csv` 的單字讀音等級，取最大值，與原系統一致。
- `rime-orthographic`：84 項只用明確同字異體對照繼承等級，例如羣／群、藴／蘊。
- `ai-context`：3,958 項由 AI 按完整詞義判斷；包括沒有單字分級的詞級變調、
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

新增 1,057 條讀音。倒的反向／反而義 dou3 與傾倒 dou2、請假 gaa3 與虛假 gaa2、處分 cyu2 fan6、和約 wo4 joek3 按整詞分清。家具 geoi6 與商店行 hong4、像素數的數 sou3、充滿著的著 zoek6 均保留原稿作對照。兄弟姐妹依 CantoDict 完整詞例保留 ze2 mui6，並列姐妹 mui2 變調；不把姊字 zi2 機械搬到姐字。

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
