# Candidate 02：Deep Query Workspace Module 實作計劃

日期：2026-07-26

狀態：實作中（已完成 state seam、query adapter 及首個 React 接線切片）

目標分支：`dev`

GitHub issue：[#146](https://github.com/bill-iu/Canto-0243/issues/146)

## Problem Statement

目前查詢畫面的個別能力已有一定 Module depth：查詢引擎負責執行及分頁，
頁籤 Module 負責頁籤與部分 history 規則，詞條詳情亦有載入及快取能力。
但把這些能力串成一次使用者操作的 policy，仍集中在超過一千行的 App
Implementation。

App 同時持有輸入中與已執行查詢、模式及平仄子模式、live／cached 結果、
詞性篩選、分頁、shuffle、頁籤快照、捲動位置、詞條詳情、非同步 generation
identity、瀏覽器返回、PWA 就緒閘、安裝提示及 Portable 更新。多組 effects
及 refs 負責在 React state、QueryTab 快照、URL、history 與非同步結果之間
補同步。

同一份查詢狀態因此有多個競爭中的真相來源。快速輸入、切換頁籤、返回、
載入更多或打開詞條詳情時，舊 completion 可能在新的 active tab 已出現後
才返回；現有守衛分散在不同 locality，難以證明所有競態都被攔截。即使
沒有產生錯誤，查詢中的局部更新亦可能拖動 App shell 及不相關頁面重新
render，尤其影響手機 CPU、記憶體與電量。

本重構要建立一個深層 Query Workspace Module，讓一次查詢工作面的生命週期
有單一 owner、窄 Interface 和可替換 Adapter。App 只保留產品外框、全域
能力及選擇顯示哪個頂層頁面。重構必須保持現有查詢引擎、純漢字 lookup、
生成詞條、排序、分頁大小及跨 host 使用者語意。

## Solution

### Module ownership

Query Workspace Module 擁有 active search tab 的工作流程：

- draft 輸入、debounced preview 及 committed search frame。
- 模式、平仄子模式、fallback 模式與 redirect hint。
- active frame identity、取消、首次查詢及 load-more completion。
- live／cached 結果、總數、篩選、shuffle 及結果投影。
- active tab 的可恢復 snapshot 與一次性 hydrate。
- 詞條選取、按頁籤暫存的 detail identity，以及 detail transition。
- 查詢專用 loading、錯誤、retry 及 UI view model。

App shell 繼續擁有：

- 頂層頁面／host chrome 與全域頁籤列。
- PWA 安裝提示、Portable 更新及離線就緒閘。
- 全域語言、主題及字體／詞條尺寸設定。
- 工作台、說明、關於、關聯及校訂等 sibling views 的掛載。

查詢引擎、頁籤／history、詞條詳情及 host capability 保持獨立
Implementation，經窄 Adapter 接入 Query Workspace。Module 不吸收 SQL、
OPFS、詞庫初始化、service worker 或其他頁面的 policy。

### State authority

active Query Workspace state 是唯一即時真相；QueryTab 只是可恢復快照。

- 進入 search tab 時 hydrate 一次，不維持逐 render 的雙向同步。
- 只在提交查詢、完成結果頁、修改篩選及離開頁籤等明確事件 checkpoint。
- history 只保存 navigation frame，不保存結果集合或完整 detail model。
- 切回頁籤先顯示最後完成快照；如需 live refresh，由新的 frame 明確發起。
- detail 只按頁籤在記憶體保存開啟狀態、詞條及偏好讀音。
- 完整 detail／relation model 不寫入 session storage 或 URL；關閉頁籤即清除。

### Draft, preview and commit

保留現有邊打邊查的使用體驗，但明確分離三種狀態：

- draft 是輸入框正在編輯的值。
- preview 是 debounce 後執行、可隨下一次輸入取消的暫時查詢。
- committed frame 只在明確提交時建立頁籤及瀏覽器 navigation history。

Preview 不得建立逐字 history。Enter／搜尋意圖會把當前有效 draft、mode
及 pzmode 原子提交，重設 paging identity，並建立可返回的 committed
frame。純漢字 lookup、生成詞條及 query dispatch 仍走既有 query engine
Adapter，不改查詢語意。

### Request identity and cancellation

每個 active search frame 有不透明、單調遞增的 identity：

- 查詢、load-more 及相關 completion 必須帶回發起時的 identity。
- identity 不再 active 時，completion、error 及 loading 結束事件均被忽略。
- 修改 query／mode、切換頁籤、popstate restore 或離開 search view 時，
  取消舊 Adapter request。
- 同一視窗只執行一個 active search frame；inactive tabs 不在背景查詢。
- 已完成的頁籤結果快照保留，取消中的不完整頁不寫入快照。
- Load-more 綁定原 frame；不得把舊 offset 的資料附加到新結果。

AbortController 用於節省實際工作，frame identity 則是 correctness boundary。
即使底層 Adapter 不能即時停止，過期 completion 仍不能改狀態。

### Navigation transaction

頁籤快照及瀏覽器 history 是同一次 navigation transaction：

- 提交時由 navigation Adapter 原子更新頁籤及 browser history。
- popstate 只轉成 restore intent，不直接修改多份 React state。
- 恢復 frame 後由 Query Workspace 決定 hydrate、取消及重新查詢。
- Preview 不 push history。
- 禁止以後置 effect 分別修補 URL、mode、query 或 tab title。

沿用現有 search-navigation 及 query-tabs policy；本候選加深其 Seam，
不另造第二套 history 規則。

### Internal structure

Module 內部使用純 reducer 與薄 effect driver：

- reducer 接收使用者 intent、navigation event 及 Adapter completion。
- reducer 只計算下一狀態及宣告 effect，不直接存取 DOM、history 或資料庫。
- effect driver 執行 query、navigation、detail 及 host Adapter。
- completion 必須以原 frame identity 回送 reducer。
- React hook／Component 只接駁 lifecycle 及呈現，不承擔隱藏 policy。

不引入 XState、Redux 或其他 runtime state dependency。

### Public Interface

Query Workspace 對外只接受：

- active search tab 的 snapshot identity。
- 語言及資料庫 capability／readiness。
- navigation、query engine、detail 及必要 host Adapter。
- 少量跨頂層 view 的 intent callbacks。

Module 對 View 提供穩定的 model 與 actions。Results、loading、detail model、
refs、generation identity、AbortController 及任意 setter 不得穿過公開
Interface。

PWA、手機瀏覽器及 Portable Desktop 使用同一 Query Workspace Module。
平台差異只能存在於 Adapter 與 responsive presentation，不分叉查詢
transition。

### Render locality

Query Workspace Component 擁有查詢局部狀態，使 draft、loading、result、
load-more 及 detail enrichment 不再觸發 App shell render。

輸入控制、結果列表及 detail panel 建立清楚的 render boundary，使用穩定
model slice 與 actions。第一階段不加入 virtualization；先量度本重構後的
結果，再以獨立候選處理仍被證明存在的列表瓶頸。

## Preflight

1. 保持在 `dev` 並同步 `origin/dev`；確認 working tree 沒有不相關改動。
2. 確認 repo git hooks 已安裝，所有文字檔使用 LF。
3. 跑現有 client build、Python suite、query/navigation self-check、detail
   self-check、PWA shell self-check 及 Portable mount smoke，記錄 baseline。
4. 使用現有 search performance 開關，在同一機器、同一資料版本及暖機詞庫
   下保存桌面與手機模擬的 input-to-frame、engine timing 及 list renders。
5. 補記 App shell 在固定查詢劇本中的 render 次數。
6. 若 baseline 已失敗，先記錄為既有問題；不要把無關修復混入本候選。

## Commits

每個 commit 都必須保持可建置、可測試及可回退。遷移期間可以建立只供測試
使用的新 Module，但 production 中同一責任不可長期雙跑。每切換一段責任，
同一 commit 或緊接的刪減 commit 必須移除舊 effects、refs 及 handlers。

### Phase A：鎖定行為與量度

#### Commit 1：加入 active search tab characterization

- 以公開行為固定首次進入、切換頁籤、離開後返回及 cached snapshot restore。
- 固定每個頁籤的 query、mode、filter、results、total 及 scroll 狀態不串頁。
- 固定非 search sibling view 不會被誤 hydrate 成查詢。

#### Commit 2：加入 draft／preview／commit navigation characterization

- 固定 draft 可以 debounce preview，但不建立逐字 browser history。
- 固定明確提交會建立一個 committed frame 並重設 paging。
- 固定 Back／Forward 恢復 query、mode 及 pzmode 的同一 frame。
- 固定 preview completion 不可改寫較新的 committed frame。

#### Commit 3：加入 stale completion 與取消矩陣

- 使用可控制完成次序的 fake query Adapter。
- 覆蓋快速輸入、改 mode、切 tab、popstate、離開 search view 及 close tab。
- 覆蓋 first-page、load-more、error 及 finally/loading completion。
- 斷言 inactive identity 的所有 completion 都沒有可觀察副作用。

#### Commit 4：擴充 search performance baseline

- 擴充現有 opt-in performance instrumentation，而不產生 production log。
- 計數 Query Workspace、結果列表、detail panel 及 App shell renders。
- 建立可重複的桌面與手機模擬查詢劇本及結果摘要。
- 保存改動前基準，並把環境、暖機條件及查詢集合寫入維護文件。

### Phase B：建立深 Module 核心

#### Commit 5：建立 Query Workspace state 與 event contract

- 定義 reducer 的 state、user intents、navigation events 及 completion events。
- 明確區分 durable snapshot fields 與 ephemeral runtime fields。
- 建立不透明 frame identity，不把 React ref 或 AbortController 放入 state。
- 加入純 reducer self-check；尚不接入 production App。

#### Commit 6：實作 draft、preview 與 committed frame transitions

- 實作輸入、debounce ready、preview start、explicit commit 及 mode transition。
- 把 redirect plan 視為既有 policy Adapter 的輸出，不在 reducer 複製語法規則。
- 確保 commit 原子重設 offset、shuffle generation 及 active request identity。
- 以 Phase A characterization 驗證 transition。

#### Commit 7：實作 snapshot hydrate 與 checkpoint projection

- 建立 snapshot 到 runtime state 的一次性 hydrate。
- 建立 runtime state 到 snapshot 的純 projection。
- 只允許已確認事件產生 checkpoint；取消中及 stale frame 不得寫入。
- 固定 tab close 後對應 runtime／detail state 可被回收。

#### Commit 8：實作 result、filter、shuffle 與 paging transitions

- 把 first page、load-more、merge、filter auto-fill 及 shuffle generation
  收入同一 reducer locality。
- Load-more 只可附加到相同 frame identity。
- First-page replacement 與 shuffled merge 保持現行使用者可見排序。
- 不改 page size、query ranking 或 POS taxonomy。

#### Commit 9：實作按頁籤 detail identity transitions

- 收入 open、close、restore、tab leave 及 tab close 的 detail identity 規則。
- 完整 detail model 仍由 Detail Adapter 擁有。
- 固定過期 core／relation enrichment 不可改寫新詞條。
- 不新增 detail deep link 或跨重啟持久化。

### Phase C：建立 Adapter Seam

#### Commit 10：建立 Query Engine Adapter contract

- 封裝 first-page、load-more、取消、result metadata 及 query-specific error。
- 以現有 search hook／engine Implementation 實作 production Adapter。
- 保留既有純漢字 lookup、生成詞條、MatchSpec dispatch、hint 及 total 語意。
- 用 fake Adapter 驗證慢 completion、取消及 retry。

#### Commit 11：建立 Navigation Adapter contract

- 封裝 committed transaction、snapshot checkpoint、tab activate 及 popstate restore。
- 以現有 query-tabs／search-navigation Module 實作 production Adapter。
- 保留現有 PWA view sanitization 及 Portable host 能力差異。
- 以現有 navigation tests 加上 atomic tab／browser history assertions。

#### Commit 12：建立 Entry Detail Adapter contract

- 封裝 instant model、core load、relation enrichment、cache 及取消。
- 把 detail generation correctness 收入 Adapter／frame identity 邊界。
- 保留現有 idle enrichment、preferred reading 及 cache behavior。
- Load／enrichment error 只影響對應 detail identity。

#### Commit 13：建立 Query Workspace effect driver

- 把 reducer 宣告的 query、navigation、checkpoint 及 detail effects 接至 Adapter。
- 所有 completion 帶回原 identity；driver 不直接修改 View state。
- Component unmount、tab leave 及新 frame 建立時集中取消。
- 加入 fake Adapter integration self-check。

### Phase D：逐段接管 React 查詢工作面

#### Commit 14：接管輸入、模式及 redirect presentation

- 讓 Query Workspace 接管 draft、debounce、commit、mode、pzmode 及 hint。
- Search View 改讀 workspace model/actions。
- 移除 App 中已被接管的 state、effects、refs 及 handlers。
- 保持輸入、Enter、模式選單、placeholder、explain 及焦點行為。

#### Commit 15：接管 search request 與結果呈現

- 讓 effect driver 成為 first-page query 的唯一 production caller。
- Results View 改讀 workspace result slice。
- 移除 App 中 live/cached result 同步及 search generation glue。
- 驗證初次查詢、cached restore、empty、hint、loading 及 error。

#### Commit 16：接管 paging、filter 與 shuffle

- 讓 workspace 成為 load-more、POS filter auto-fill 及 shuffle 的 owner。
- 移除 App 中對應 merge、offset、total、filter 及 generation policy。
- 保持可見結果、排序、去重、filter chips 及 scroll behavior。
- 驗證 load-more 與新 frame／tab switch 競態。

#### Commit 17：接管 detail lifecycle

- 結果選取改送 workspace intent。
- Detail View 改讀 workspace detail slice，完整 model 由 Detail Adapter 提供。
- 移除 App 中 detail refs、per-tab map、load generation 及 enrichment glue。
- 保持 Escape、明確關閉、偏好讀音、instant content 及 idle enrichment。

#### Commit 18：切換 snapshot 與 navigation transaction

- Query Workspace 經 Navigation Adapter 成為 search tab checkpoint／restore owner。
- popstate、tab switch、new tab、close tab 及 leave search view 改送明確 intent。
- 移除 App 中 save-leaving、hydrate 補同步及 URL/history 修補 effects。
- 驗證頁籤與 browser history 不會分裂。

#### Commit 19：建立最終 Query Workspace Component render boundary

- Search View 與 Detail View 完整掛在 Query Workspace Component 下。
- App shell 只傳遞窄 props／Adapter，不接觸 workspace internal state。
- 穩定 model slice 與 actions，避免無關 result/detail subtree render。
- 固定 sibling views、global tabs、PWA gate、install prompt 及 Portable update
  仍由 shell 擁有。

#### Commit 20：刪除舊 App coordinator

- 刪除所有已退役 query lifecycle effects、refs、handlers、imports 及 wrappers。
- 刪除只為舊雙向同步存在的 helper；可復用的 engine／navigation／detail
  Module 保留。
- 加入 architecture seam check，防止 App 再直接持有 query request、
  pagination 或 detail generation policy。
- 以責任刪除作完成標準，不以單純行數作標準。

### Phase E：跨 host 驗收與文件

#### Commit 21：補齊跨 host 互動與無障礙回歸

- 在瀏覽器 PWA、手機 viewport 及 Portable host 跑相同 query transition matrix。
- 覆蓋鍵盤提交、返回、頁籤切換、load-more、detail close 及 focus restore。
- 確認 loading／error announcement、focus order 及結果操作的現有無障礙語意。
- 不因 render isolation 犧牲 browser find 或完整結果 DOM。

#### Commit 22：比較效能基準並處理可證明的 regression

- 以 Phase A 相同環境比較 input-to-frame、engine timing 及 render counts。
- 查詢引擎 median／p95 不得比 baseline 退步超過 10%。
- draft、loading、load-more 及 detail enrichment 不得觸發 App shell render。
- 原本存在可量度 UI 瓶頸時，UI p95 目標至少改善 20%。
- 只修理由本重構造成或阻止驗收的 regression；virtualization 另案處理。

#### Commit 23：完成架構文件及刪除測試

- 記錄 Query Workspace ownership、state authority、Adapter Seam 及 cancellation
  contract。
- 更新維護文件的效能量度方法與跨 host 驗證步驟。
- 記錄不持久化完整 detail、單一 active request 及不分叉平台 Module 的決策。
- 確認舊 coordinator、臨時 Adapter 及遷移 scaffolding 已全部刪除。

## Decision Document

- App 是 product shell，不是查詢生命週期 owner。
- Query Workspace 是 active search workflow 的深 Module。
- active runtime state 是即時真相；QueryTab 是事件式 checkpoint 快照。
- 保留 debounced live preview；只有明確提交建立 navigation history。
- 頁籤 history 與 browser history 是同一次原子 transaction。
- 每個 active frame 使用不透明 identity；Abort 是資源優化，identity 是正確性
  邊界。
- 同一視窗只執行一個 active query；inactive tabs 不在背景完成查詢。
- 切回頁籤先顯示最後完成快照。
- Detail identity 按頁籤暫存在記憶體；完整 model 不跨重啟持久化。
- reducer 處理純 transition，薄 driver 執行 Adapter effects。
- 公開 Interface 只暴露 snapshot/capability/adapters 及少量跨 view intents。
- 手機瀏覽器、桌面瀏覽器及 Portable Desktop 共用同一 Module。
- 先建立 render locality；virtualization 必須由後續量度證明。
- 不新增狀態管理 runtime dependency。
- 遷移採小 commit strangler，但完成後不保留 feature flag 或雙軌 coordinator。

## Testing Decisions

好的測試只驗證公開事件與可觀察結果，不依賴 reducer 欄位排列、React hook
數量、Component 行數或私有 helper。

必須測試：

- Query Workspace reducer：draft、preview、commit、hydrate、checkpoint、
  paging、detail identity 及 stale completion。
- Query Engine Adapter：first page、load-more、取消、error、retry、純漢字
  lookup 及生成詞條不變。
- Navigation Adapter：tab snapshot 與 browser history 原子更新、popstate
  restore 及跨 host view policy。
- Detail Adapter：instant/core/relation enrichment、取消、cache 及 preferred
  reading。
- React integration：Search View 的輸入、結果、分頁、篩選、詳情、焦點及
  sibling view 切換。
- Performance：input-to-frame、engine timing、result/detail/App shell renders。

測試先例沿用現有 committed-search、search-navigation、query-tabs、
search-performance、entry-detail-core、PWA search shell 及 Portable app
mount self-check。優先擴充現有輕量 self-check／smoke infrastructure；
除非現有工具無法觀察必要的公開行為，不新增測試 runtime dependency。

## Out of Scope

- 修改 query grammar、query kinds、MatchSpec、dispatch 或查詢結果語意。
- 修改純漢字 lookup、生成詞條、排序、去重、page size 或 POS taxonomy。
- 資料庫 schema、SQL／OPFS physical plan、詞庫載入及 service worker 重構。
- 結果列表 virtualization、infinite-window library 或 UI redesign。
- 新增 detail URL/deep link，或跨重啟保存完整 detail model。
- 新增手機／瀏覽器／Portable 各自的 Query Workspace implementation。
- 重構工作台 session；它屬 Candidate 04。
- 退役 release RC 路徑；它屬 Candidate 05。
- Candidate 01 本地化目錄或 Candidate 03 compiler 的後續擴張。
- 全域 Redux、XState 或其他 state framework。
- 與本候選無關的既有測試失敗或功能修復。

## Further Notes

- `useSearch`、query-tabs、search-navigation 及 entry-detail 現有 Module 應視為
  可復用 Implementation／Adapter 起點，不應因 App 過深而全部重寫。
- App 行數下降是責任轉移及刪除的結果，不是獨立 KPI。
- 若 baseline 顯示 engine time 而非 render 是主要瓶頸，記錄結果並另開候選；
  不把 physical query 優化塞進本結構重構。
- 完成後以 deletion test 驗證：移除 Query Workspace 應只移除查詢工作面，
  不應同時破壞 PWA shell、Portable update、工作台或其他 sibling views。
