# POS 語彙族細分設計

日期：2026-07-19  
基線：`408044e`、ADR-0061  
範圍：語彙族契約、離線提案與審核、三軸搜尋結果篩選、句格工作台篩選

## 目標

把 **語彙族** 由空或 `idiom` 擴充為空、`idiom`、`chengyu`、`suyu`、`yanyu`。三葉語意上皆屬熟語，但 SSOT 每字面仍只存一個值。既有 `idiom` 不會因 schema 升級而被強制改類；只有過審提案才可改成葉值。

產品提供完整三軸篩選：**詞類**、**語彙族**、**語態面**各自軸內多選 OR，軸與軸之間 AND；未選的軸不限制結果。語彙族葉值精確匹配，`idiom` 匹配傘與全部三葉；啟用某軸後，缺該軸高信任標籤的字面不通過。這是創作者主動收窄結果的條件；**同詞性**、campaign 硬閘及工作台同桶繼續只看 **詞類**。

這項後續決策取代 ADR-0061 原先只描述「語彙族單選」的產品控制方式；實作提交會同步修訂 `CONTEXT.md` 與 ADR-0061，但不改其單值 SSOT、傘葉匹配或外源只提案邊界。

## 已考慮方案

### A. 把 China-idiom 加入產品 dependency

直接安裝 `china-idiom`，由 runtime 查 membership。實作短，但令產品 build、Portable、PWA 和離線查詢依賴外部成語庫，亦形成第二套權威。拒絕。

### B. Vendor 完整 `idiom.csv`

把外部 CSV 放入 repo 或發布產物，再由 ingest/runtime 共用。可重現，但引入約 9 MB 外源資料、更新及授權維護成本，而且仍容易被誤用成產品詞庫。拒絕。

### C. 外部 CSV 只作離線提案輸入（採用）

提案指令接受維護者提供的 `China-idiom/china_idiom/idiom.csv` 路徑。腳本讀取字面、繁化、與本專案詞庫及細分母體取交集，只輸出 `chengyu` proposal。repo 記錄來源 URL、commit、輸入 SHA-256 和衍生提案；不保存完整外源 CSV，也不在正常 build 或 test 期間取網。

這個方案符合 ADR-0061：外部 membership 提高召回，但不取得權威地位。

## 模組與契約

### 1. SSOT 與載體

- `ingest.project_pos` 的 family 閉集改為 `"" | idiom | chengyu | suyu | yanyu`。
- `PosRow.family` 仍是單值；不新增傘欄或布林葉欄。
- carrier 只輸出高信任 family，沿用現有展示信任規則。
- TypeScript `PosFamily`、中文標籤和詞條面板 chip 支援四值。
- 新增單一三軸 filter matcher，輸入詞類集合、語彙族集合及語態集合：
  - 同一軸已選值採 OR；不同非空軸採 AND；
  - 三軸皆空時全部通過；
  - 詞類只匹配 carrier 的高信任 `show` 集合，不以中信任 `gate` 冒充創作者篩選標籤；
  - family 選到 `idiom` 時，四個非空 family 均通過；葉值只通過同名葉；
  - voice 只通過已選的 `active`／`passive`；
  - 缺 entry，或缺任何已啟用軸的高信任展示值時不通過。

matcher 只組合三個各自獨立的軸 matcher；不改任何一軸的存儲結構。campaign／工作台同桶繼續呼叫既有 gate POS helper，不經此創作者 filter。

### 2. 細分母體與審核帳

首次執行凍結當時 SSOT 中 `family=idiom` 的字面，形成排序穩定、git tracked 的母體。細分帳至少記錄：

- `literal`
- `current_family`
- `proposed_family`
- `source`
- `evidence`
- `confidence`
- `verdict`（`accept | keep_idiom | reject | pending`）
- `review_note`

`keep_idiom` 是必要終局，避免 SSOT 值未變時無法分辨「未審」和「已明確留傘」。apply 只接受合法且已過審的 `accept`／`keep_idiom`；重跑不得重複或改亂其他 POS 軸。

status 報告母體數、pending、三葉數、已審留傘數及終局覆蓋。品質抽樣以已審終局為宇宙，固定 seed，`OK + SOFT > 90%` 才通過。meta 記錄母體、覆蓋、各類數量、抽樣輪次與報告路徑。

### 3. China-idiom 協作流程

提案工具接受 `--china-idiom-csv`、`--source-commit`。它會：

1. 驗證 CSV 及 `word` 欄；
2. 用專案現有繁化能力轉換字面；
3. 去除空值及重複；
4. 與詞庫字面相交；
5. 再與凍結的 `idiom` 母體相交；
6. 產生 `chengyu` pending 提案及來源 sidecar（URL、commit、SHA-256、計數）。

外源命中只是 evidence，不會直接 apply。俗語與諺語沒有假裝對等的自動來源，主要由 agent／維護者按 CONTEXT 優先序審核。完整外源 CSV 存於 repo 外暫存目錄；完成提案後可刪除。

## 搜尋結果三軸篩選

搜尋控制列旁加入獨立漏斗按鈕。桌面版開啟錨定於按鈕的輕量 popover；窄屏改用 bottom sheet，不建立佔據搜尋主畫面的常駐面板。內容沿用本產品的紙墨／玫紅視覺語言，分成三組可鍵盤操作的 chips：

- 詞類：名詞／動詞／形容詞／副詞／虛詞；
- 語彙族：熟語／成語／俗語／諺語；
- 語態面：主動／被動。

選擇立即生效，不另設套用鍵。選中 chip 有文字、填色及 `aria-pressed` 三重狀態；漏斗顯示已選 chip 總數 badge，面板有條件時顯示「重設」。點擊外部、`Esc` 或關閉鍵只收起面板，不清除條件。`idiom` 是語彙族全族捷徑：選它會清除三個葉 chip；之後選葉會先清除 `idiom`，葉與葉之間仍可多選 OR，避免冗餘條件。

三軸條件套用到普通結果、近反義結果及聲母／韻母分組；外部近反義項若不在載體內，啟用任一 POS 軸時不入選。

篩選狀態屬於搜尋 tab，切 tab 後可恢復；第一期不加入 URL query parameter。新查詢沿用該 tab 的選擇；使用「重設」才一次清空三軸。

因搜尋原始結果分頁取得，不能只篩當前第一頁後宣稱零結果。開啟篩選時，若符合項少於一個 `RESULT_RENDER_BATCH` 且後端仍有下一頁，前端會逐頁續取，直到符合項填滿一個 render batch，或耗盡原始結果。使用者再捲動時重複同一規則。每次只允許一個 load-more，並沿用既有取消／查詢版本保護。

未耗盡時顯示「已載入 N 個符合」而不冒充全域總數；耗盡後才顯示最終符合總數。shuffle 只重排符合項。任一軸改變時重設可視視窗，不重新執行文字查詢。

## 句格工作台篩選

工作台候選區重用相同三軸 filter state 與 chips，但以工作台自身的 compact trigger 呈現，狀態只屬當前工作台 session。創作者三軸 filter 在既有詞類同桶之後套用於 `direct_syn`、`semantic_related`、`sound_only` 三組，以及使用者確認放寬後重新取得的 exact 結果。

三軸 filter 是使用者硬條件，不是可放寬條件。零結果不會自動取消任何軸，亦不會把 `candidateCount` 當作篩選後準確數字；若原建議計數未經三軸過濾，UI 不顯示誤導數字。

## 錯誤與降級

- carrier 缺失或載入失敗：維持現有「詞性缺標」降級；三軸 control disabled，搜尋與工作台本身仍可用。
- 外源 CSV 缺失、header 不符或 hash 無法計算：提案指令 fail closed，不寫 proposal／SSOT。
- 提案含非法 family、非母體字面或未審 verdict：apply fail closed，SSOT 不變。
- 三軸篩選得到零結果：清楚顯示是目前詞性條件下無結果，不改寫一般搜尋失敗語意。

## 測試與驗收

### 契約

- Python parser 接受四值並拒絕未知值。
- carrier round-trip 保留高信任葉值；低信任 family 不輸出。
- TypeScript matcher 覆蓋軸內 OR、軸間 AND、傘與三葉、主被動、高信任展示邊界、缺標及全空。
- `same_pos`、campaign hard gate、formal POS map 的既有測試不變且通過。

### 資料管線

- 用小型 fixture 驗證簡轉繁、去重、詞庫交集、母體交集及來源 sidecar。
- apply fixture 驗證 pending 不寫入、accept 改葉、keep_idiom 留傘、重跑冪等、其他三軸不變。
- 實際 China-idiom 輸入產生可審核 proposal；來源 commit/hash 可追溯。
- 固定 seed 品質抽樣 `>90%`，報告及 meta 一致。

### 產品

- 搜尋所有結果 layout 的三軸組合、葉精確與熟語傘匹配。
- 分頁首批零命中仍會續取；耗盡才顯示最終零結果。
- tab 切換、badge、重設、shuffle、查詢取消及結果計數正確。
- 工作台三組候選與放寬後結果均保留硬三軸條件。
- popover／bottom sheet control 有 label、`aria-pressed`、鍵盤操作、disabled 及零結果狀態。

### 完整驗證

執行 POS smoke、client POS self-check、相關工作台 self-check、TypeScript 檢查、lint、PWA build。正常 build／test 不提供 China-idiom 時仍須成功，並確認 dependency 與 lockfile 無變更。

## 交付邊界

本次會交付 schema、載體、提案／審核工具、實際 China-idiom 衍生提案、可合理完成的過審細分批次、搜尋及工作台三軸篩選。它不會交付成語接龍、外部釋義、全庫強制三選一、URL filter 契約、runtime 外部查詢或第二套詞庫。
