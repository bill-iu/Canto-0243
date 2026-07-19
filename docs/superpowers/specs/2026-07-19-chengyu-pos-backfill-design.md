# China-idiom 成語 POS 補標設計

日期：2026-07-19  
基線：`00ef277`、ADR-0058、ADR-0061  
範圍：`family_leaf_review.tsv` 中 4,147 筆 `lexicon-pos-gap` 已審成語

## 目標與邊界

為已確認 `family=chengyu`、同時屬專案詞庫但尚未進入 `project_pos.tsv` 的 4,147 個字面補齊專案 POS。每筆加入主表後必須有保守審定的詞類，或在句法證據不足時明確標為 `u`；語態只在成語整體具有固定被動／遭受義時標 `passive`。

本批不擴張至 China-idiom 其他字面，不改詞庫 membership，不引入外部 dependency，不 vendor 外源 CSV，也不為普通成語自動標 `active`。China-idiom 仍只作離線審核證據，不是 runtime 或第二套權威。

## 已考慮方案

### A. 純釋義關鍵詞

用「形容」「比喻」「指」等詞直接映射 POS。速度快，但釋義的元語言不等於成語的句法功能；例如「形容某種做法」未必代表整體是形容詞。拒絕。

### B. 全部逐筆自由判讀

每筆不依共用規則獨立判斷。彈性高，但 4,147 筆難以維持一致與重現，來源更新後也無法穩定重跑。拒絕。

### C. 多證據候選＋保守覆核（採用）

合併例句槽位、釋義語義、內部結構及專案既有已審模式產生候選。證據一致才給正式 POS；衝突或不足降為 `u`。針對 `u`、`passive`、`x`、罕見多詞性及非四字詞作重點覆核，再以固定分層樣本把關。

## 審核帳與資料流

新增獨立 POS 審核帳，保留既有 family 審核歷史不變。每列至少包含：

- `literal`
- `pos`
- `family`
- `voice`
- `evidence`
- `confidence`
- `verdict`
- `review_note`

審核母體由既有 `family_leaf_review.tsv` 精確選出 `scope=lexicon-pos-gap`、`verdict=accept`、`proposed_family=chengyu` 的 4,147 筆。工具讀取本地 China-idiom CSV 前，必須核對既有 sidecar 的 source commit 與 SHA-256；不符即 fail closed，且不得寫 proposal、review 或 SSOT。

候選證據依序為：

1. China-idiom 例句中 `～` 的句法位置；
2. 釋義所指的實體、行為、狀態或方式；
3. 成語的內部語法結構；
4. 專案既有且已過審的相似模式。

每筆保留規則 ID 與簡短證據摘要。規則只建立候選，不以單一釋義關鍵詞直接取得權威。終局審核帳須一字面一列、無 pending，才能進入品質閘。

品質通過後，apply 將 4,147 筆全部 upsert 至 `project_pos.tsv`：`family=chengyu`，`pos` 為正式五主類的一個或多個值，或 `u`；`voice` 只可為明確的 `passive` 或空。note 記錄過審來源與規則。重跑必須零變更，且不得修改既有 22,716 筆的其他軸資料。

## 詞類判定

- `n`：成語整體指人、物、事件、處境、制度或抽象概念，且可佔名詞短語位置。
- `v`：成語整體表達動作、過程、行為或心理活動，且可作主要謂語。
- `a`：成語整體表達性質、狀態或評價，且可受程度修飾、作定語或狀態謂語。
- `r`：成語主要修飾另一動作或整句，表方式、時間、程度、範圍或語氣。
- `x`：只限真正的虛詞、感嘆／應答公式等封閉功能；不得作「其他」桶。
- `u`：完整分句、用法高度依賴語境、資料互相衝突，或沒有足夠句法證據。

多詞性只收現代句子中常見、且由釋義或例句分別支持的用法。理論上可臨時名詞化、形容化或狀語化不足以增加標籤；若證據只支持一種常見句法功能，就只標單一主詞類。

## 語態判定

語態預設為空。只有成語整體把主體固定表達成承受者或被處置者，而且該被動／遭受義是詞義的一部分時，才標 `passive`。來源故事偶然含被動句、只表無意願、困境或負面狀態，都不足以標被動。

本批不為「非被動」條目批量補 `active`。`active` 主要留給有成對對照需要的既有契約；名詞、形容詞、副詞及未定條目也不會因 voice 軸要求而被誤標主動。

## 信任與產品行為

通過審核的正式 `n/v/a/r/x` 列以 `review` provenance 進入高信任展示；`u` 是終局「證據不足」，不進創作者詞類篩選。`passive` 只有通過嚴格覆核才進高信任載體。family 已由前一輪審核確定，全部保持 `chengyu`。

因此，補標完成不代表每條成語都必須在三個軸上有非空值：family 必有 `chengyu`，詞類可能是正式值或 `u`，voice 可以合法留空。

## 品質閘

apply 前須同時滿足：

- source commit 與 CSV SHA-256 完全符合 sidecar；
- 審核帳恰有 4,147 個唯一字面，全部終局，且 family 全為 `chengyu`；
- POS、voice、confidence、verdict 均屬閉集；
- `u`、`passive`、`x`、低頻多詞性組合及其小型 strata 全數覆核；
- 其餘按 POS、單／多詞性、字數及證據類型作固定 seed 分層抽樣；樣本不少於母體 5%，且不少於 250 筆；
- `OK + SOFT > 90%`；所有抽到的 `BAD` 必須修正並重建報告，不能帶錯 apply。

品質報告記錄 seed、母體、各 stratum 大小、抽樣數、判決、修正及審核帳 SHA-256。apply 必須校驗報告所鎖定的 review hash，避免抽樣後帳目被替換。

## 錯誤處理與冪等

- 外源缺檔、header 缺欄、commit/hash 不符：fail closed，不寫任何衍生檔。
- 母體數量或成員漂移：fail closed，要求重新檢查 family 審核帳，不靜默擴張 scope。
- 候選證據衝突：降為 `u`，不得以覆蓋率為由硬猜。
- review 有 pending、重複、非法值或不屬母體字面：apply 拒絕。
- quality gate 未過或 review hash 不符：apply 拒絕。
- apply 只新增缺失的 4,147 列；若既有列意外出現，內容不一致即 fail closed，不覆蓋未知改動。
- 首次 apply 後重跑 changed 必須為 0。

## 測試與驗收

fixture 覆蓋：母體選取、source pin、例句槽位、釋義與結構證據、多詞性保守聯集、`x` 邊界、`u` 降級、被動門檻、非法值、review hash gate、apply 衝突及冪等。

實際套用後核對：

- 主表新增恰好 4,147 筆；
- 新列 family 全為 `chengyu`；
- family status 的 `deferred_missing_project_pos` 由 4,147 變為 0；
- 原有列及其三軸資料不被改動；
- carrier 重建後，高信任正式 POS 與明確 `passive` 可供三軸篩選；
- `package.json`、`client/package.json`、lockfile、`skills-lock.json` 與完整外源 CSV 無變更。

完整驗證執行 POS smoke、family leaf smoke、metadata/filter self-check、TypeScript 檢查、Vite build 與 `git diff --check`。完成後 commit 並 push `dev`；未經維護者確認不建立 `dev -> main` PR。
