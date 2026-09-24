# Candidate 04：Workbench Session Coordinator 實作計劃

日期：2026-07-26

狀態：**已完成**（2026-08-05 closeout）

目標分支：`dev`

GitHub issue：[#147](https://github.com/bill-iu/Canto-0243/issues/147)

## Closeout（2026-08-05）

- 實作本體已在 `dev`／`main`（coordinator core、React facade、touch recognizer、render isolation、reading lifecycle）。
- 本地窄屏 manual acceptance：OK（owner）。
- 最小 closeout：`stale_candidate` structured notice＋三語文案；coordinator self-check 納入 CI tag；本節 ownership 記錄。
- 豁免：Playwright 窄屏 browser harness 與改前／改後 latency 對照（以 pure gesture self-check＋本地窄屏驗收代替）。

### Ownership（維護契約）

| 層 | 擁有 | 不擁有 |
|---|---|---|
| `workbench-coordinator.ts` | session／version／readings／preview／relaxation／POS filter／structured notice；cleanup matrix | pointer 座標、DOM、焦點、未提交 input |
| `useWorkbenchSessionCoordinator.ts` | 執行 reading／persistence effects；identity-gated completion | candidate paging／cache |
| `touch-gesture.ts` + `SentenceCanvas` | lock／edit intents from touch／pen | session state |
| `WorkbenchPage` | intents in、view model out；文案翻譯 aria-live | durable session refs |

- 正式 session 唯一權威 = coordinator state；hook 的 `stateRef` 只讀。
- 讀音／preview／apply 以 `session.version`／selectionVersion 作 correctness boundary。
- 只持久化正式 session payload（既有 storage schema）。
- Production 無 feature flag、無雙軌 coordinator。

---

## Problem Statement

句格工作台已有可復用的 session reducer、候選 snapshot／paging module 與
逐字讀音 coordinator，但把它們串成一次使用者操作的 policy，仍集中在頁面
component。頁面同時持有正式 session、readings、preview、relaxation、POS
filter、訊息、欄位錯誤及多個 current refs，handlers 又混合 reducer
transition、非同步讀音、候選 identity、焦點、本機儲存及 bridge 操作。

同一份工作狀態因此存在 React state 與 current ref 兩份權威。快速鎖格時，
caller 需要先手動改 ref 再 set state，避免下一次點擊讀到舊 session；
讀音 completion、候選 completion、undo 與 preview cleanup 則各自用不同的
version、surface 或 ref 判斷。規則分散後，很難證明手機快速連點、轉讀音、
修改句格或套用候選時，較舊的 completion 一定不能污染新版本。

窄屏另有觸控歧義。使用者依次連點 A、B 格時，肥指命中邊界可能令事件序列
交疊；A 收到意外的第二次觸控後，瀏覽器合成的 double-click 會開啟手改
輸入。工作台仍需要保留觸控雙擊修改，因此不能單純停用 double-click。

本重構要建立深層 Workbench Session Coordinator，讓正式 session、版本、
讀音生命週期、preview／relaxation cleanup、候選 identity、POS filter、
持久化及結構化結果事件有單一 owner。頁面只送出使用者 intents 及渲染
view model。現有候選 session、讀音 coordinator、查詢語意、儲存格式及
跨 host 行為必須保留。

## Solution

### Ownership boundary

Workbench Session Coordinator 擁有會影響工作流程正確性的狀態：

- 正式 session、單調遞增 version 與 undo。
- 逐字讀音結果、解析狀態、request identity 及自動選讀 completion。
- preview、active relaxation 及其版本生命週期。
- 與候選 identity 綁定的 POS filter。
- 欄位驗證、非同步失敗及操作結果的結構化事件。
- 正式 session 的 hydrate、save 及 clear policy。

頁面及 presentation components 繼續擁有：

- 尚未提交的起句輸入。
- 焦點、捲動、IntersectionObserver 及 compare panel focus restore。
- 語言、主題、字體／詞條尺寸、選單及頁面導航。
- DOM、pointer gesture 與 inline editor 的開關。
- PWA／Portable host chrome 及跨頁 bridge。

Coordinator 不吸收全域 UI state，也不成為巨型 reducer。

### Internal structure

內部採用純狀態核心與薄 React hook 外殼：

- 純核心接收 user intent、lifecycle event 及 adapter completion。
- 核心原子計算下一個 coordinator state 及需要執行的 effects。
- React hook 執行讀音、候選及儲存 effects，再把帶 identity 的 completion
  送回核心。
- 頁面只取得穩定的 view model 與 actions。
- 不引入 Redux、XState 或其他 runtime state dependency。
- 不建立 global store 或跨頁 singleton。

### Single state authority

Coordinator state 是唯一正式真相：

- 所有同步 intent 經同一 functional update queue 按順序處理。
- 頁面不再保存 session、readings、preview 或 pending request 的 current
  refs。
- hook 若因 React callback 需要 latest-state ref，只可作讀取橋樑，不能
  先改 ref、後補 state。
- 非同步 correctness 依賴明確 version／request token，不依賴 closure
  碰巧讀到最新 state。

### Reading lifecycle

讀音解析期間介面保持可操作，採最新版勝出：

- 每次改變正式句格的 intent 建立新 session version。
- 新版本取消舊讀音工作；Abort 用於節省資源，identity 是 correctness
  boundary。
- 較舊 completion 即使返回，也不得改 readings、session、message 或
  loading 狀態。
- 新版本可沿用位置與字面仍相符的既有讀音。
- 自動選讀只可填入 completion 所屬版本中仍未被使用者選定的格。
- 使用者手選讀音後，遲到的自動 completion 不得覆蓋。

現有逐字讀音 coordinator 保持獨立，作為 production adapter 復用；不重寫
它的取消、request identity、merge 或 auto-choice 能力。

### Candidate integration

現有 candidate session 繼續擁有查詢、分頁、快取、generation 及淘汰過期
回應：

- Coordinator 提供一致的候選 identity，包括 session version、constraints、
  preview／relaxation 狀態及 POS filter。
- React hook 外殼組合 candidate session，向頁面提供候選、loading、error
  與 load-more action。
- 套用候選必須攜帶候選 response 的 selection version。
- selection version 已過期時，apply intent 沒有狀態副作用，並可輸出穩定
  的 stale-candidate notice。
- 不複製候選 paging、cache 或 generation policy。

### Preview, relaxation and undo

暫態與正式變更採單一 cleanup matrix：

- Preview 只屬於建立它的 session version，不持久化，不進入 undo。
- 正式套用候選建立新 version，並清除 preview。
- Relaxation 是正式 session transition，因此可以 undo。
- Active relaxation 只作 presentation marker，不獨立改變查詢語意。
- 新編輯、鎖定、constraint 變更、clear 或 undo 統一清除舊 preview 與
  active relaxation marker。
- Cleanup 由 coordinator transition 集中執行，頁面 handlers 不再逐個
  補 set-null。

### Persistence

維持現有儲存格式與相容範圍：

- 只保存正式 draft、constraints、locks、選定讀音及 undo snapshot。
- 不保存讀音請求、候選結果、preview、active relaxation、notice 或 error。
- 初始化 hydrate 完成前，不啟動候選與讀音 effects。
- 每個成功提交的新 version 最多寫入一次。
- 儲存失敗輸出非阻塞事件，不回滾記憶體中的工作。
- 不改用 IndexedDB，不加入 schema migration。

### Structured events

核心不保存已翻譯的顯示字串：

- 結果、驗證及失敗以穩定 code 加必要 payload 表示。
- View 按目前語言翻譯，並繼續負責 aria-live announcement。
- 欄位錯誤保留到該欄位修正或相關 session transition。
- 一次性 notice 可被下一個 intent 取代，不持久化。
- 正常被淘汰的 stale／aborted completion 不產生可見錯誤。

### Touch double-tap recognizer

觸控／筆保留雙擊修改，但不採信瀏覽器合成的 touch double-click：

- Gesture helper 以全域最近的有效 taps 判斷雙擊。
- 只有最近連續兩次有效 tap 都完成於同一格，且在允許時間內，才輸出
  edit intent。
- 中間任何另一格的 tap 都重置前一格的 double-tap candidate；A、B、A
  不可被拼成 A 的雙擊。
- 每個 pointer lifecycle 最多輸出一次 lock intent。
- 多個 pointer 同時活動、按下／放開跨格、超過 movement slop、cancel 或
  scroll，均令當次 double-tap candidate 失效。
- 第一下仍即時鎖定；真正同格的第二下不再次 toggle，而是開啟修改。
- 滑鼠保留原生 double-click；鍵盤保留 Enter／F2 編輯及空白鍵鎖定。

Gesture helper 留在 presentation 層，只輸出 lock／edit；pointer、座標與
時間不進入 Workbench Session Coordinator。

### Render locality

本候選同時建立可量度的 render boundary：

- Session／句格變更只更新句格、constraints 及必要的候選 identity。
- 候選 loading、分頁或 error 不應令句格逐格重繪。
- Message、preview 與 host chrome 使用窄 model slice。
- 使用穩定 actions 及普通 React memoization，不建立自製 selector
  framework。
- 行數下降不是 KPI；責任刪除、競態測試及 render 量度才是完成標準。

### Rollout

採小 commit strangler migration，但不保留 feature flag 或雙軌
coordinator：

- 每次搬遷一組責任，立即刪除原 owner 的 state、effect、ref 或 handler。
- 過渡相容層只在 migration commits 存在。
- 後端 API、儲存格式、查詢結果及使用者操作語意保持不變。
- 每個 commit 都可建置、可測試及可回退。

## Preflight

1. 保持在 `dev`，同步 `origin/dev`，確認 working tree 沒有不相關改動。
2. 確認 git hooks 已安裝，所有文字檔使用 LF。
3. 跑 client build、CI self-check、Python workbench smoke、accessibility
   self-check、manual slot self-check 及現有 reported regression tests。
4. 保存固定句稿下的桌面與窄屏基準：四次連續鎖格 latency、句格 render
   次數、候選 first page／load-more 時的句格 render 次數。
5. 在真實窄屏或瀏覽器觸控模擬器重現 A、B 交疊事件劇本，保存事件序列。
6. 若 baseline 已有無關失敗，記錄後保持隔離，不順便擴張本候選。

## Commits

### Phase A：鎖定現行行為與量度

#### Commit 1：加入 session workflow characterization

- 以公開 intents 固定起句、鎖格、改讀音、手改、clear 及 undo 的可觀察
  session 結果。
- 固定每次正式變更只產生一個新 version。
- 固定無效 intent 不改 version、undo 或 selection。
- 使用現有輕量 TypeScript self-check infrastructure。

#### Commit 2：加入 async completion 競態矩陣

- 建立可控制 completion 次序的 fake reading adapter。
- 覆蓋快速鎖格、改字、手選讀音、clear 及 undo 後的舊讀音 completion。
- 斷言 stale success、error 及 finally/loading completion 均無可見副作用。
- 固定使用者選擇優先於遲到的 auto-choice。

#### Commit 3：加入 preview、relaxation、candidate version characterization

- 固定 preview 不改正式 session 或 undo。
- 固定 session-changing intents 的 cleanup matrix。
- 固定 relaxation 可 undo，但 active marker 不持久化。
- 固定舊 selection version 的候選不能套用到新 session。

#### Commit 4：加入 touch gesture regression harness

- 建立不依賴 DOM 的 pointer/tap sequence harness。
- 固定同格連續兩 tap 產生一次 lock 及一次 edit。
- 固定 A、B、A 不產生 A edit。
- 固定跨格 release、多指、scroll、movement slop 及 cancel 不產生錯誤
  double-tap。
- 固定每個 pointer lifecycle 最多產生一次 lock。

#### Commit 5：加入 render 與互動 baseline

- 加入 opt-in development instrumentation，不產生 production log。
- 記錄句格、constraints、candidate region、preview 及 page shell commits。
- 建立桌面與窄屏固定互動劇本。
- 保存改動前 baseline 與量度環境。

### Phase B：建立純 Coordinator 核心

#### Commit 6：定義 coordinator state、intent 與 completion contract

- 定義 durable session、ephemeral workflow、structured event 及 effect
  descriptors。
- 明確區分 user intents、lifecycle events 與 adapter completions。
- 將 request identity 設為不透明 token，不把 AbortController 或 DOM ref
  放入 state。
- 加入 initial／hydrate transition 的純測試，尚不接 production UI。

#### Commit 7：接入原子 session intents

- 讓核心包裝現有 session reducer，而不是重寫 domain transitions。
- 實作 create、replace、insert、lock、clear-locks、reading choice、manual
  slot／span、constraints、clear 及 undo intents。
- 每個 intent 以單一 functional transition 取得最新 session。
- 以 characterization 確認 rapid intents 不需要外部 current ref。

#### Commit 8：集中 cleanup matrix

- 把 preview、active relaxation、field error 及一次性 notice 的清理規則
  接到相關 session intents。
- 實作 preview open／close、candidate apply 及 relaxation transitions。
- 對 stale candidate selection 輸出結構化 notice，不改 session。
- 刪除純核心外重複 cleanup 的測試 scaffolding。

#### Commit 9：加入 reading lifecycle state

- 建立 idle、waiting-for-ready、resolving、resolved 及 failed 的窄狀態。
- 每次需要解析的新 version 宣告帶 identity 的 effect。
- completion 只有在 version、request token 及仍相容的 draft identity 一致
  時才可套用。
- 實作可沿用位置／字面的 previous readings projection。

#### Commit 10：加入 structured event model

- 將 validation、operation result、reading failure、storage failure 及 stale
  selection 表示為 code 與 payload。
- 定義欄位錯誤與一次性 notice 的清除時機。
- 明確將 abort／stale completion 視為沉默結果。
- 加入語言切換不改核心 event 的測試。

#### Commit 11：加入 durable persistence projection

- 建立 coordinator state 到現有 session storage payload 的純 projection。
- 建立現有 payload 到 coordinator initial state 的 hydrate transition。
- 排除 readings、candidate、preview、relaxation marker 及 events。
- 固定 hydrate 完成前不宣告 reading 或 candidate effects。

### Phase C：建立 Effect 與 Adapter 接線

#### Commit 12：接入既有 reading coordinator

- 以現有 reading coordinator 實作 production reading adapter。
- 將 resolve、cancel、merge 與 auto-choice completion 轉成 coordinator
  events。
- 新 version、inactive view 及 unmount 時集中取消。
- 保留現有 cache 與 adapter 行為，不建立第二份 reading cache。

#### Commit 13：接入 reference-reading effects

- 將韻腳／聲母參考字讀音解析納入同一 effect identity 規則。
- 只 merge completion 所屬 constraints version 仍需要的參考字。
- 失敗時保留 surface fallback，不污染主 reading error。
- 移除獨立於 coordinator 的 reference-reading lifecycle。

#### Commit 14：接入 persistence effect

- 每個 durable version 最多宣告一次 save 或 clear。
- Hydrate 期間不回寫未完成狀態。
- Storage failure 送回結構化非阻塞 event。
- 驗證 reload 只恢復正式 session。

#### Commit 15：建立 React hook facade

- 用 React hook 承接 coordinator core、effects 與 lifecycle。
- 對 View 提供穩定的 model slices 及 intent actions。
- 不暴露 reducer dispatch、setters、AbortController、request token 或 current
  refs。
- 以 fake adapters 加入 hook-independent integration self-check。

#### Commit 16：組合既有 candidate session

- 由 hook facade 產生穩定 plan identity 與 POS filter。
- 現有 candidate session 繼續負責 fetch、paging、cache 及 generation。
- 將 response selection version 帶入 apply-candidate action。
- 驗證 candidate load-more 不改 session 或 reading state。

### Phase D：逐段接管 Workbench Page

#### Commit 17：接管起句、ingest 與手改 intents

- 將 submit、跨頁 ingest、replace／insert、manual slot 及 manual span 改為
  coordinator actions。
- View 只保留未提交 input 與 DOM focus。
- 移除對應 page-level session/readings cleanup 及 nested async calls。
- 保持所有現有文案、橋接及焦點結果。

#### Commit 18：接管鎖格、clear-locks 與 undo

- 將鎖格、解除全部鎖定、clear 及 undo 改為 coordinator actions。
- 移除先寫 current ref 再 set state 的做法。
- 驗證同一 event loop 的多次鎖格按順序套用。
- 保持 selection width、constraint fitting 及 undo 使用者語意。

#### Commit 19：接管 constraints 與 reference readings

- 將 mode、semantic、code、rhyme、initial 及 reference intents 接到
  coordinator。
- 移除頁面逐個清除 active relaxation 的 handlers。
- 移除頁面 reference-reading effect。
- 保持現有 constraints presentation 與候選 plan 語意。

#### Commit 20：接管 preview、relaxation 與 candidate apply

- View 改讀 coordinator preview／relaxation model。
- Open、close、apply、stale apply 及 relaxation 都經 actions。
- 焦點移動仍由 View 的 effect callback 執行，不進入核心。
- 移除 page-level candidate/current-preview refs。

#### Commit 21：接管 readings、events 與 persistence

- Sentence presentation 改讀 coordinator readings slice。
- View 把 structured events 翻譯成目前語言的文案及 aria-live status。
- 移除 page-level pending resolve、reading ref、message string authority 及
  storage effect。
- 驗證 inactive／unmount cleanup。

#### Commit 22：刪除舊 page coordinator

- 刪除所有已退役 state、refs、effects、handlers、imports 及相容 wrappers。
- 保留 input、focus、scroll、language、theme、host navigation 及 presentation
  state。
- 加入 architecture seam check，防止頁面重新直接擁有 reading request、
  candidate selection version 或 durable session persistence。
- 以責任刪除作完成標準，不以檔案行數作標準。

### Phase E：觸控判定與 Render Isolation

#### Commit 23：引入純 touch gesture recognizer

- 將全域有效 tap sequence、active pointers、target、時間及 movement 狀態
  收入小型純 recognizer。
- 輸出 lock、edit 或 no-op，不直接改 React／session state。
- 使用 Phase A 的 A、B、A、多指及跨格劇本固定規則。
- 不處理 mouse／keyboard policy。

#### Commit 24：切換 Sentence Canvas pointer wiring

- Touch／pen pointer events 改用 recognizer，不採信合成 touch double-click。
- Mouse 保留原生 double-click；keyboard 保留 Enter／F2／Space。
- 第一下 touch lock 即時送出，真正同格第二下只送 edit。
- 保持 inline editor、span hand input、focus 及 accessible labels。

#### Commit 25：建立 coordinator model render boundaries

- Sentence、constraints、candidate、preview 及 status 只訂閱所需 model slice。
- 穩定 actions，避免候選 loading／paging 令句格逐格重繪。
- 避免 message 或 host chrome 變更重算候選 identity。
- 不加入自製 selector framework 或全域 store。

### Phase F：跨 Host 驗收與文件

#### Commit 26：補齊窄屏 pointer integration 驗收

- 用可選 browser harness 在手機 viewport 重播同格雙擊、A／B 快速鎖定、
  A／B／A、跨格 release、scroll 及 multi-touch cancellation。
- 驗證觸控雙擊仍可開 inline edit。
- 驗證正常 A、B 連點沒有額外延遲，而且不會誤開 A 的 editor。
- 保留 mouse、keyboard 及 accessibility self-check。

#### Commit 27：比較效能與競態基準

- 以 Phase A 相同環境重跑桌面與窄屏劇本。
- 四次快速鎖格 latency 不得比 baseline 倒退超過 10%。
- Candidate first page／load-more 不得增加 Sentence Canvas commit。
- Stale reading／candidate completion 的全部競態測試必須確定性通過。
- 只修理由本重構造成或阻止驗收的 regression。

#### Commit 28：完成維護文件與刪除 migration scaffolding

- 記錄 coordinator ownership、state authority、effect identity、adapter seam
  及 touch recognizer contract。
- 記錄 persistence 邊界、structured events 及跨 host 驗證步驟。
- 刪除臨時 compatibility adapters、debug counters 及 migration-only hooks。
- 確認 production 沒有 feature flag、雙軌 coordinator 或新增 runtime
  dependency。

## Decision Document

- Coordinator 只擁有 correctness-critical workflow，不吸收純 UI state。
- 內部採純核心加薄 React hook，不引入全域 store 或狀態框架。
- Coordinator state 是 session、readings、preview、relaxation、POS filter
  與 workflow events 的唯一權威。
- 所有同步 intent 經 functional update queue；不以 current ref 作第二份
  state。
- 讀音解析期間保持可操作；version identity 決定 completion 是否有效。
- 使用者手選讀音永遠優先於較遲的 auto-choice。
- 復用現有 reading coordinator 及 candidate session，不重寫它們的 cache、
  paging 或 cancellation。
- Preview 是 version-bound transient state；relaxation 是可 undo 的正式
  transition。
- Cleanup matrix 集中於 coordinator。
- 只持久化現有正式 session payload，不改 schema 或 storage technology。
- 核心輸出結構化 event，View 負責翻譯及 aria-live。
- Touch／pen 保留雙擊修改，但使用自訂全域連續 tap recognizer。
- A、B、A、跨格 release、多指及 scroll 不可產生錯誤 double-tap。
- Gesture recognition 留在 presentation；coordinator 不理解 pointer。
- 候選 paging 不得驅動 Sentence Canvas render。
- 手機、桌面瀏覽器及 Portable 共用同一 coordinator core。
- 遷移採小 commit，但完成後不保留 feature flag 或 legacy coordinator。

## Testing Decisions

好的測試只驗證 intent、adapter completion、gesture sequence 與可觀察結果，
不依賴 reducer 欄位排序、hook 數量、component 行數或私有 helper 名稱。

必須測試：

- Coordinator core：session intents、version、undo、cleanup matrix、
  structured events、hydrate 及 persistence projection。
- Reading adapter：ready gate、取消、stale success／error／finally、
  previous reading reuse 及 auto-choice priority。
- Candidate composition：plan identity、POS filter、load-more 隔離及 stale
  selection apply。
- Touch recognizer：同格雙擊、A／B、A／B／A、跨格 release、slop、scroll、
  cancel、多指及每個 pointer 一次 lock。
- React integration：起句、鎖格、手改、constraints、preview、relaxation、
  undo、focus restore、status translation 及 accessibility。
- Persistence：reload 只恢復正式 session，storage failure 不阻塞操作。
- Performance：rapid lock latency 與 candidate-to-sentence render isolation。

測試先例沿用現有 workbench session、candidate session、manual slot、
accessibility、UI、bridge、reported regression 及 Python client seam
self-check。純 coordinator 與 gesture recognizer 使用現有 TypeScript
self-check harness；瀏覽器 pointer 驗收沿用 repo 可選 Playwright
infrastructure。除非現有 harness 無法觀察已確認的公開行為，不新增前端
測試 runtime dependency。

## Out of Scope

- 修改候選查詢 grammar、MatchSpec、ranking、分頁大小、去重或 POS taxonomy。
- 重寫 candidate cache、paging、generation 或 reading cache。
- 修改後端 API、資料庫 schema、SQL／OPFS、詞庫初始化或 service worker。
- 修改現有 session storage schema或改用 IndexedDB。
- 改動 PWA／Portable navigation、全域語言／主題或 host chrome。
- UI redesign、格子 virtualization 或全域狀態框架。
- 停用觸控雙擊修改，或把手機改字強制改成只用手打按鈕。
- 把 pointer 座標、雙擊時間或 inline editor state 放入 coordinator。
- Candidate 01、02、03 的後續擴張，或已退役 Candidate 05 release RC 工作。
- 與本候選無關的既有測試失敗或功能修復。

## Further Notes

- 現有 session reducer 是 domain transition 起點；新 coordinator 應組合它，
  不複製它。
- 現有 reading coordinator 已正確處理 abort、request identity 與 merge；
  新 seam 的價值在於把 page-level workflow 統一，而非重做 adapter。
- 現有 candidate session 已擁有 paging cursor 與 generation；coordinator
  只提供穩定 identity 及 apply boundary。
- 若量度顯示瓶頸來自候選 DOM 數量而不是 render propagation，應另開
  virtualization 候選，不把它塞入本重構。
- 完成後以 deletion test 驗證：移除 coordinator 應只移除句格工作流程，
  不應同時破壞 host chrome、查韻頁、詞庫初始化或其他 sibling views。
