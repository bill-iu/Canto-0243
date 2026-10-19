# 第三批：廣東歌語料優先補詞及讀音審核

2026-10-19；AI 輔助逐項檢視，未經人類逐條認證。本批列入
[v1.1.2 刷新](https://github.com/bill-iu/Canto-0243/releases/tag/v1.1.2)，完整建置結果見下方「正式建置」。

## 來源選擇

| 來源 | 已核對資料 | 本輪處理 |
|---|---|---|
| [Jason Y H Lee：Cantopop corpus](https://github.com/jasonleeubc/Cantopop-corpus) | 105 首，2000–2020；Humdrum 檔有旋律、漢字、逐字粵拼三欄；[專案介紹](https://cantopop.humdrum.org/)及固定版本 [LICENSE](https://github.com/jasonleeubc/Cantopop-corpus/blob/018e88540b917c40dc3f7248ed98908208544b54/LICENSE) 標示 CC BY 4.0 | 本輪主要候選與讀音交叉檢視來源 |
| [ToneCraft](https://github.com/purepasser-by/ToneCraft)／[EMNLP 論文](https://aclanthology.org/2025.emnlp-main.18/) | 倉庫有訓練資料，但檢視時未見明確資料授權 | 記錄候選來源，未下載或併入正式清單 |
| [Yang、Wu、Duan 2021](https://archives.ismir.net/ismir2021/latebreaking/000046.pdf) | 論文分析約 750 首粵語歌，描述歌詞來自網上卡拉 OK 網站 | 論文的 CC BY 4.0 唔等於原始歌詞另有可重用授權；未據此匯入原始歌詞 |
| [Rime Essay](https://github.com/rime/rime-cantonese) | 本 repo 已有字面詞頻證據；本輪補足少量日常搭配 | 31 個新增口語表達 |

Cantopop 固定版本 `018e88540b917c40dc3f7248ed98908208544b54`。原始檔只放本機
`.tmp/lexicon-b03-cantopop/`；追蹤檔只保留短語、標音、位置及來源指紋，唔搬整首歌詞。
呢個語料範圍有限，唔代表全部年代、歌手或日常口語。

## 候選與判決

- 解析 6,560 個漢字樂句片段；2–6 字共 60,669 個不同字串。
- 對照 v1.1.2 詞庫及既有 curated，56,525 個字串未收；其中 1,907 個跨至少兩首歌。
- 唔將上述數字當成可收錄詞數。例：「甜言蜜」「言蜜語」「地老天」「心真意」係截詞殘片。
- 本輪接納 199 個新字面：歌詞證據 168、Essay 口語 31；通用中文 72、填詞短語 93、口語 34。
- 另補 1 個原有字面的正確讀音，排除 54 個明顯殘片；其餘未逐項審定，唔自動收錄。
- 前兩批 337 + 今批 199 = **536 個新增表達**。以同一 v1.1.2 覆蓋更新詞庫、PWA 及兩平台桌面完整套件。

歌詞的跨曲出現係用法證據，唔係讀音權威。多音字及語境讀法有額外校對，例如：
「只差一點」用 `zi2 caa1 jat1 dim2`，「千斤重」用 `cin1 gan1 cung5`，
「大時代」用 `daai6 si4 doi6`，唔直接採用語料最高頻異讀／誤標。

審核表：

- [補詞及排除項](../data/lexicon/reviews/2026-10-19-b03-supplement.tsv)
- [讀音判決](../data/lexicon/reviews/2026-10-19-b03-readings.tsv)
- [來源、逐檔 SHA-256、參數及統計](../data/lexicon/reviews/2026-10-19-b03.meta.json)

## 現有詞庫讀音

重新唯讀掃描 v1.1.2 的 181,546 列：碼／粵拼不符為 0；36 列音節數待審、
7,732 列詞級讀音未列於單字表，共 7,768 列待審。36 列包括「兙」等一字多音節合字，
唔將字數與音節數不同一律當錯誤。

與歌詞字串交集 120 列：確認刪除 11、保留 34、其餘 75 留待審。
刪除按精確 `(字面, 舊粵拼)` 套用 overlay，唔改搜尋模式的鬆緊規則。

| 字面 | 移除 | 保留／補回 | 核對依據 |
|---|---|---|---|
| 未曾 | `mei4 cang4`、`mei6 jang4` | `mei6 cang4` | [CantoDict 未](https://cantonese.sheik.co.uk/dictionary/characters/567/)、[曾](https://www.cantonese.sheik.co.uk/dictionary/characters/798/) |
| 挽手 | `waan2 sau2` | `waan5 sau2` | [CantoDict 挽](https://www.cantonese.sheik.co.uk/dictionary/characters/2045/) |
| 見怪 | `gin3 gwai3` | `gin3 gwaai3` | [CantoDict 見](https://cantonese.sheik.co.uk/dictionary/characters/431/?full=true) |
| 一覽 | `jat1 laam4` | `jat1 laam5` | [Rime 詞表](https://github.com/CanCLID/rime-cantonese-upstream/blob/126ce8c8365b9264ed46f813c3e6720a898be227/word.csv) |
| 一霎 | `jat1 sap3` | `jat1 saap3` | 同上 Rime 詞表 |
| 從頭開始 | `cung4 tau4 hoi1 ci5` | `cung4 tau4 hoi1 ci2` | 語料整詞 + Rime「開始」`hoi1 ci2` |
| 志願 | `zi2 jyun6` | `zi3 jyun6` | [CantoDict 志](https://cantonese.sheik.co.uk/dictionary/characters/638/) |
| 愛錫 | `ngoi3 sek3` | `oi3 sek3` | 上述 Rime 詞表同詞 |
| 折衷 | `caak3 cung1` | `zit3 cung1` | [CantoDict 折](https://cantonese.sheik.co.uk/dictionary/characters/2011/) |
| 百家姓 | `baak3 gaa1 sing1` | `baak3 gaa1 sing3` | [粵典](https://cantowords.com/dictionary/%E7%99%BE%E5%AE%B6%E5%A7%93) |

重要保留項：粵典明確記錄 [自己](https://cantowords.com/dictionary/%E8%87%AA%E5%B7%B1) 的 `gei1`、
[今日](https://cantowords.com/dictionary/%E4%BB%8A%E6%97%A5) 的 `mat6`、
[把握](https://cantowords.com/dictionary/%E6%8A%8A%E6%8F%A1) 的 `baa2 ngak1`／`baang2 ak1`，
以及 [來年](https://cantowords.com/dictionary/%E4%BE%86%E5%B9%B4)、[以為](https://cantowords.com/dictionary/%E4%BB%A5%E7%82%BA)、
[歷歷在目](https://cantowords.com/dictionary/%E6%AD%B7%E6%AD%B7%E5%9C%A8%E7%9B%AE) 的異讀，故保留。
「海嘯」「月相」等來源有分歧，仍待審。歌詞與字典唔一致唔足以單獨刪詞。

## 驗證

- 正常預設來源合併及 overlay 後，隔離測試庫 181,735 列、166,594 個字面。
  精確新增 200 個 `(字面, 粵拼)` 對、移除 11 個指定對；新增 199 個字面，原有字面全部保留。
- 所有 200 筆新增／修復標音的格式、六聲碼、音節數及單字參考檢查均通過。
- 200 筆 × 三檔，Python 與 PWA 各 600 次、合共 **1,200 次查詢通過**；
  排除轉碼／粵拼提示列後，兩端都以指定字面列首項。此為本批字面驗證，唔代表所有延伸候選排序均一致。
- 原有音節數待審仍為 36；詞級單字表未列由 7,732 降至 7,721，唔將其餘待審當成錯誤。
- 煙霧套件 255 項（4 項既定 skip）；其中三項 Node 啟動檢查首次受 Windows 過長 PATH 影響，
  使用縮短 PATH 重跑所屬 7 項檢查後全通過。接縫檢查 89 項通過（6 項 skip）。
- 105 個來源檔 SHA-256、全部歌詞證據的起訖行與字面、以及新增／刪除對的精確集合均已核對。
- 審核期間使用中 `lyrics.db` SHA-256 保持 `6d83593d659b48ca957e5e66d07de8373d521af3ec7cb09326a5f79b35bcccff`。

測試庫只驗證詞條來源及查詢，未重建關係與語意鄰居，唔作正式發佈庫。
正式更新須依 [發佈流程](release.md) 完整建置，唔以只重建 words 的測試庫取代現行詞庫。

## 正式建置（v1.1.2 同版本刷新）

- 補詞與讀音來源先經 PR #169 合併至 `main`，再以完整 `build-db` 重建詞條及關係，
  共 **181,735 列、166,594 個字面**；未使用上述只有 words 的隔離測試庫發佈。
- 對照上一份正式庫：新增 200 個指定讀音對、刪除 11 個指定錯讀，199 個新字面；
  原有 166,395 個字面全部保留。
- 近反義資料由 225,402 增至 **225,479 筆**。沿用 ADR-0039 每端最多 20 個近義鄰居：
  8 條舊 Cilin 稀疏邊重新選取（均有一端已達 20 上限），85 條新邊加入；
  其餘舊關係、全部專案自建關係保留，未繞過既有上限補回邊。
- 語意索引由備份庫的舊 ID → 字面 → 新 ID 遷移；先核對舊指紋與 bin SHA-256，
  再逐條核對 **2,258,966 條有向邊與量化分數**全部保留。
  今批 199 個新字面未新增模型鄰居，三批累計 536 個補詞可正常查詞及聲調搜尋。
- 三語關於頁、三語 README 及 Release notes 同步更新，保留 Cantopop corpus 署名及上游授權。
