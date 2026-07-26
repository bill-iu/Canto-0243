# Candidate 02：Deep Query Workspace 剩餘實作計劃

日期：2026-07-26

狀態：grilling 完成，待續作

目標分支：`dev`

GitHub issue：[#146](https://github.com/bill-iu/Canto-0243/issues/146)

## Problem Statement

Candidate 02 已建立 Query Workspace state seam、Query Engine Adapter，以及第一段
React 接線；查詢 request 已開始由 workspace 管理，但原計劃尚未完成。

產品外框仍持有查詢結果投影、cached/live 切換、POS filter、shuffle、頁籤
checkpoint、scroll restore、navigation 修補、詞條 detail identity、分段 enrichment、
錯誤呈現及多組 generation refs。Query Workspace 與產品外框因而同時擁有同一
查詢工作面的部分真相。

這個中間狀態可以攔截部分 stale query completion，但仍不能完整證明以下操作
不會競態：

- 快速輸入後立即提交、切 mode、切頁籤或使用 Back／Forward。
- 新查詢與 load-more、filter auto-fill、shuffle 同時發生。
- 切頁籤或關閉 detail 後，舊 core／relation enrichment 才返回。
- inactive tab 的 cached snapshot、目前 runtime state 與 browser history 分裂。
- 手機端局部 loading、results 或 detail 更新拖動整個產品外框 render。

因此 #146 不能以「查詢已經經過一個 hook」作完成標準。完成標準是 Query
Workspace 成為 active search workflow 的唯一 owner，而產品外框只保留路由、
全域設定、PWA／Portable chrome、ready gate capability 及 sibling views。

## Solution

### 由現有 seam 繼續深化

保留已完成的純 state 核心、frame identity、query adapter 與首段 React 接線，
以 strangler migration 逐項接管餘下責任。每接管一項，立即刪除產品外框內的
舊 state、effect、ref 或 handler；不建立第二套長期並行 coordinator。

### 單一 runtime authority

Query Workspace runtime state 是 active search tab 的唯一即時真相。頁籤資料是
事件式 checkpoint，不是逐 render 雙向同步的第二份 state。

Checkpoint 只在已定義事件產生：

- 明確提交查詢。
- 首頁或 load-more 成功完成。
- POS filter 或 shuffle 可見狀態改變。
- 離開、切換或關閉 search tab。
- 需要保存目前 scroll position 的 navigation 事件。

Snapshot 保存 committed query、mode、平仄子模式、已完成而且目前可見的結果
次序、total、offset、POS filter、shuffle 狀態及 scroll position。它不保存
draft、preview、loading、error、request identity、AbortController、完整 detail
model 或 relation enrichment。

本次不新增結果截斷、頁籤 eviction 或新的記憶體上限。Inactive tab 保留目前
已載入的完整可見結果，以維持切回時的使用者語意；若量度證明多頁籤快照是
記憶體瓶頸，另開候選處理。

### Draft、preview 與 commit

保留邊打邊查，但明確分成三種狀態：

- draft 是輸入框內尚未提交的文字。
- preview 是 debounce 後可取消、不可建立 history 的暫時 frame。
- commit 由 Enter、搜尋按鈕或等價明確意圖建立 navigation frame。

Preview error 不覆蓋最後完成結果，只產生非阻塞狀態。Commit error 不顯示與
新 query 不相符的舊結果；目前頁籤顯示可重試錯誤，原本的其他頁籤 snapshot
保持不變。

若詞庫尚未 ready，保留最新 draft；preview 不排隊。明確 commit 立即建立
navigation frame，但只保留最後一個 pending committed frame，待 ready 後執行。

純漢字 lookup、生成詞條、MatchSpec dispatch、ranking、去重、page size 及
redirect hint 語意全部沿用現有 Query Engine Adapter，不在 workspace 重新實作。

### Request identity、paging 與 shuffle

每個 active frame 使用不透明且單調遞增的 identity。Abort 節省資源，identity
才是 correctness seam。Inactive identity 的 success、error、finally 或
loading completion 一律沒有可觀察副作用。

每個視窗只有 active search tab 可以執行查詢。切走或離開 search view 時取消
first-page、load-more 及 detail enrichment；inactive tabs 只保留最後完成的
snapshot。

Load-more 同一時間最多一個 request，只能附加到原 frame。失敗時保留既有
結果並容許以相同 offset 重試。POS filter auto-fill 沿用目前規則，逐頁請求，
直到可見結果達到既有門檻、沒有更多結果，或 frame 失效；不得平行搶頁。

Shuffle 保存目前可見次序。Load-more 不重新排列已顯示項目，只按現有 merge
規則加入新結果；新 commit 重設 shuffle。切回頁籤時先恢復原次序，不因 hydrate
重新抽樣。

### Navigation transaction

頁籤 checkpoint 與 browser history 由同一個 Navigation Adapter 操作。產品
外框及 workspace view 不得分別以後置 effect 修補 query、mode、title、URL 或
snapshot。

Adapter 對 caller 只回報一次 transaction 成功或失敗。若 host history 操作
失敗，Adapter 負責補償或回復一致 snapshot，workspace 保持目前可操作狀態並
產生可恢復 navigation error，不留下半個新頁籤或錯配 URL。

Popstate 只轉成 restore intent。恢復 completed snapshot 時先直接呈現；同一
詞庫版本下不自動背景刷新。Snapshot 不存在、資料版本失效，或使用者明確
提交／retry 時才建立新 frame。

### Entry Detail lifecycle

每個 search tab 在記憶體保存 detail identity、開啟狀態與偏好讀音。完整 core
及 relation model 仍由 Detail Adapter 與既有 cache 擁有，不寫進 URL、
history 或 session storage。

切換頁籤、關閉 detail、關閉頁籤或建立較新的 detail identity 後，較舊的
core／relation completion 一律被忽略。Detail error 只影響相同 identity，
不清除查詢結果或污染另一頁籤。

Escape 與明確關閉保持現有行為；關閉後焦點回到觸發該 detail 的結果項目。
跨頁籤恢復 detail 時，只有目標仍存在才恢復焦點，不建立虛構 DOM target。

### Module Interface 與 Adapter seams

Query Workspace 對 React 只提供穩定的 view model slices 與使用者 actions。
Reducer dispatch、任意 setters、results refs、generation identity、
AbortController 及 adapter completion 不穿過公開 Interface。

Module 內保留三個私有 seam：

- Query Engine Adapter：首頁、load-more、取消及查詢結果 metadata。
- Navigation Adapter：commit transaction、checkpoint、tab activation 與
  popstate restore。
- Entry Detail Adapter：instant model、core、relation enrichment、cache 與取消。

每個 seam 都有 production adapter 及測試 fake。三者不合併為大型 App adapter，
也不變成頁面需要理解的大包 callbacks。

### Render locality

Search controls、Results、Detail 與 product shell 建立獨立 render boundary。
Draft、loading、load-more、filter、shuffle 或 detail enrichment 不應觸發產品
外框或 sibling views render。

本次不加入 virtualization。完整可見結果留在 DOM，保留 browser find、目前
scroll、鍵盤操作及無障礙讀取。列表本身若仍是瓶頸，必須由完成後量度證明，
再另開候選。

### Cross-host 與 accessibility

PWA、手機／桌面瀏覽器及 Portable Desktop 使用同一 state 核心與 transitions。
Host 差異只存在於 production adapters 與 capability input，不建立分叉的
workspace implementation。

Loading、error、retry、result count 及 detail loading 維持可理解的 aria-live
announcement。鍵盤提交、頁籤切換、Back／Forward、load-more、detail
開啟／關閉及 focus restore 都列入跨 host 驗收。

## Commits

以下只列剩餘 commits；已完成的 state seam、Query Engine Adapter 與第一段
React 接線不重做。每個 commit 都必須可建置、可測試及可回退。

### Phase R0：固定目前中間狀態

#### Commit R1：加入未接管責任的 architecture characterization

- 固定產品外框目前仍擁有 results projection、filter、shuffle、checkpoint、
  navigation 與 detail lifecycle 的可觀察行為。
- 固定 active／inactive tab、cached restore、scroll restore 及 sibling view
  切換的現況。
- 測試只描述使用者結果，避免把中間狀態的私有 refs 寫成永久 contract。

#### Commit R2：加入 pending-ready 與 error／retry matrix

- 用可控制完成次序的 fake Query Engine Adapter 固定 preview、commit、
  first-page 及 load-more 的 ready gate 行為。
- 固定 preview error、commit error、load-more error 與 retry 的不同結果。
- 固定 stale success、error 及 finally 不改 loading、snapshot 或目前結果。

#### Commit R3：加入 navigation 與 detail race matrix

- 用 fake adapters 固定 commit transaction、popstate、tab switch、tab close
  及 navigation failure。
- 固定 detail instant、core、relation、close、switch 及 stale enrichment。
- 固定 Escape、明確關閉與 focus restore 的公開行為。

#### Commit R4：保存剩餘遷移的效能基線

- 沿用 opt-in performance instrumentation，加入 workspace、search controls、
  results、detail 與 product shell render counters。
- 保存桌面與手機 viewport 的固定查詢、load-more、filter、shuffle 及 detail
  劇本。
- 記錄詞庫版本、暖機條件、查詢集合與量度方法，不產生 production log。

### Phase R1：完成 runtime authority

#### Commit R5：擴充 durable snapshot projection

- 納入 committed frame、結果次序、total、offset、filter、shuffle 及 scroll。
- 明確排除 draft、preview、request、error 及完整 detail model。
- 加入 snapshot round-trip、inactive tab isolation 與資料版本失效測試。

#### Commit R6：把 visible results 與 cached/live policy 收入 workspace

- 令 workspace 直接產生目前可見結果，不再由產品外框複製 live／cached rows。
- 保留純漢字 lookup 的 pick merge 與目前結果順序。
- 接線後立即刪除舊 results、cached total 及 live projection owner。

#### Commit R7：把 POS filter 與 auto-fill 收入 workspace

- Workspace 擁有 normalized filter、filtered projection 及 auto-fill intent。
- Auto-fill 只串行載入相同 frame 的下一頁，遵守既有門檻及終止條件。
- 接線後刪除產品外框的 filter state、patch effect 及 load-more 觸發 policy。

#### Commit R8：把 shuffle generation 與 merge 收入 workspace

- 新 commit 原子重設 shuffle；同 frame load-more 保留既有可見次序。
- Checkpoint／hydrate 恢復相同 shuffled order。
- 接線後刪除產品外框的 shuffle state、generation 及 merge effects。

#### Commit R9：完成 ready gate、error 與 retry transitions

- Ready 前只保留最新 committed frame，preview 不排隊。
- First-page error、load-more error、retry 與 stale completion 由同一 state
  transition 管理。
- View 只讀結構化狀態，不自行推斷應否保留或清空結果。

### Phase R2：完成 Adapter seams

#### Commit R10：建立 Navigation Adapter contract 與 fake

- 封裝 commit transaction、checkpoint、activate、leave、close 及 popstate。
- Production adapter 復用既有 query-tabs 與 search-navigation policy。
- Fake adapter 可注入成功、失敗及不同完成次序，驗證 caller 不做後置修補。

#### Commit R11：把 tab checkpoint 改由 Navigation Adapter 執行

- 只有已定義事件可以投影 durable snapshot。
- 離開、切換、關閉及 scroll checkpoint 經同一 adapter。
- 接線後刪除產品外框的 save-leaving、逐 render patch 及 hydrate 補同步。

#### Commit R12：把 commit／popstate 改成原子 navigation transaction

- 明確提交同時建立 committed frame、tab state 與 history frame。
- Popstate 只送 restore intent，不直接改多份 React state。
- 加入失敗補償與可恢復 error，刪除 URL、mode、query 及 title 修補 effects。

#### Commit R13：建立 Entry Detail Adapter contract 與 fake

- 封裝 instant model、core load、relation enrichment、cache、取消及 error。
- Completion 帶回 detail identity；fake 可控制分段完成次序。
- 保留既有 idle scheduling、preferred reading 及 cache 行為。

#### Commit R14：把 detail lifecycle 收入 workspace

- Workspace 擁有 per-tab detail identity、open／close／restore 及 focus token。
- Adapter completion 只能更新相同 identity。
- 接線後刪除產品外框的 detail map、generation refs、load effects 及 enrichment
  orchestration。

### Phase R3：收窄 React Interface

#### Commit R15：建立穩定 Search Controls model 與 actions

- 只暴露 draft、mode presentation、hint、loading／error view model，以及提交、
  retry 等使用者 actions。
- 移除任意 setters、flush／hydrate internals 及 request facts。
- 驗證輸入、debounce、Enter、搜尋按鈕及 redirect presentation。

#### Commit R16：建立穩定 Results model 與 actions

- 只暴露可見 rows、total、filter、shuffle、has-more、loading-more 及結果 actions。
- 結果 view 不接觸 adapter、offset merge 或 checkpoint implementation。
- 驗證 first page、empty、load-more、filter auto-fill、shuffle 與 cached restore。

#### Commit R17：建立穩定 Detail model 與 actions

- 只暴露目前 detail presentation、loading／error 與 close／reading actions。
- Detail view 不接觸 generation identity、cache 或 enrichment lifecycle。
- 驗證 per-tab restore、stale completion、Escape 及 focus restore。

#### Commit R18：建立最終 Query Workspace render boundary

- Search controls、Results 及 Detail 掛在 workspace boundary 下。
- Product shell 只傳 capability、全域 presentation inputs 及少量跨 view intents。
- 固定 draft、loading、paging 及 detail enrichment 不重繪 shell 或 sibling views。

#### Commit R19：刪除舊 product-shell query coordinator

- 刪除所有已退役 query、results、paging、filter、shuffle、snapshot、navigation
  及 detail state、refs、effects、handlers 與 wrappers。
- 加入 architecture seam check，阻止 shell 再直接擁有 request identity、
  pagination merge、detail generation 或 checkpoint policy。
- 以 deletion test 驗證 workspace 移除時只影響 search workflow。

### Phase R4：驗收與收尾

#### Commit R20：補齊跨 host 與 accessibility 驗收

- 在 PWA、手機／桌面 viewport 及 Portable host 跑同一 transition matrix。
- 覆蓋鍵盤提交、tab、Back／Forward、retry、load-more、detail close 及焦點。
- 驗證 aria-live、result count、loading／error 及完整結果 DOM。

#### Commit R21：比較效能基線並修復本重構 regression

- 使用 R4 相同環境比較 input-to-frame、engine timing 及 render counters。
- Engine median／p95 不得退步超過 10%。
- Draft、loading、load-more 及 detail enrichment 不得觸發 product shell render。
- 若原有 UI p95 瓶頸可量度，目標至少改善 20%；否則不虛報效能收益。

#### Commit R22：完成架構文件及 issue 驗收證據

- 記錄 ownership、Interface、三個私有 adapter seams、snapshot projection、
  navigation transaction、cancellation、detail 及跨 host contract。
- 記錄量度方法、已知限制及另案處理的 memory／virtualization 候選。
- 確認沒有 feature flag、雙軌 coordinator 或 migration-only scaffolding。
- 在 #146 留下測試、效能、commit、PR 及 merge 證據；合併進 `main` 後才關閉。

## Decision Document

1. #146 的完成標準維持原計劃：產品外框不再擁有 search workflow policy。
2. Query Workspace runtime state 是唯一即時真相；頁籤資料是事件式 checkpoint。
3. 同一視窗只有 active search tab 執行查詢；inactive tabs 保留完成快照。
4. 保留 debounced preview；只有明確提交建立 navigation history。
5. Detail identity 按頁籤留在記憶體；完整 detail／relation model 不持久化。
6. React 公開 Interface 只提供 view model slices 與使用者 actions。
7. Query Engine、Navigation、Entry Detail 是三個私有 adapter seams。
8. 本次建立 render boundaries，不加入 virtualization。
9. Engine median／p95 不得退步超過 10%；可量度 UI p95 目標改善至少 20%。
10. 保留並深化目前 state seam、query adapter 及 React 接線，不重新開始。
11. Snapshot 保存 committed frame、完整可見結果次序、total、offset、filter、
    shuffle 及 scroll；不保存 ephemeral workflow。
12. 本次不新增 snapshot 截斷、memory cap 或 inactive-tab eviction。
13. Completed snapshot 在相同資料版本下切回時不自動刷新；明確提交、retry、
    缺少 snapshot 或版本失效才建立新 frame。
14. Navigation Adapter 對 caller 呈現單一 transaction；失敗時由 adapter
    補償，不以頁面 effects 修補半完成狀態。
15. Ready 前保留最新 draft 與最後一個 committed frame；preview 不排隊。
16. Preview error 非阻塞；commit error 顯示可重試狀態；load-more error 保留
    既有結果及 offset。
17. Load-more 與 filter auto-fill 串行執行，綁定原 frame，禁止平行搶頁。
18. Shuffle 保留目前可見次序；load-more 不重排既有 rows；新 commit 重設。
19. Detail completion 綁定 per-tab identity；close／switch 後失效，關閉時恢復
    合理焦點。
20. 純漢字 lookup、生成詞條、grammar、ranking、page size、去重及結果語意
    全部凍結。
21. PWA、手機／桌面瀏覽器及 Portable Desktop 共用同一 state 核心與
    transitions；差異只在 adapters／capabilities。
22. Loading、error、retry、detail 及 result count 必須保留 aria-live、鍵盤
    操作及 focus restore。
23. 遷移採小 commit strangler；每次接管立即刪除舊 owner，完成後不留 feature
    flag 或雙軌 coordinator。
24. 測試只沿公開 Interface、user intent、adapter completion 及可觀察結果；
    不固定 reducer 欄位排列、hook 數量或私有 helper。
25. #146 只有在舊 shell coordinator 已刪除、跨 host／無障礙／效能驗收通過、
    架構文件更新及 PR 合併進 `main` 後才可關閉。

## Testing Decisions

好的測試沿 Query Workspace 公開 Interface 驗證 user intent、adapter
completion 與可觀察結果；不依賴 reducer 欄位順序、React hook 數量、私有 refs
或檔案行數。

必須覆蓋：

- State 核心：draft、preview、commit、pending-ready、checkpoint、hydrate、
  filter、shuffle、paging、detail identity、leave 及 stale completion。
- Query Engine Adapter：first page、load-more、取消、error、retry、純漢字
  lookup、生成詞條與跨 host parity。
- Navigation Adapter：commit transaction、checkpoint、activate、close、
  popstate、失敗補償及資料版本失效。
- Entry Detail Adapter：instant、core、relation、cache、取消、error、偏好讀音
  及 stale enrichment。
- React integration：輸入、結果、filter、shuffle、load-more、detail、tab、
  Back／Forward、sibling views、focus 與 aria-live。
- Performance：input-to-frame、engine median／p95，以及 controls、results、
  detail、workspace 與 product shell render counters。

優先沿用現有 query workspace、committed search、query navigation、query tabs、
entry detail、search performance、PWA shell、Portable mount、accessibility 及
reported regression self-check／smoke infrastructure。只有現有 harness 無法
觀察已確認的公開行為時，才補 browser-level 測試；不新增 runtime state
dependency。

## Out of Scope

- 修改 query grammar、query kinds、MatchSpec、ranking、去重、page size 或
  POS taxonomy。
- 修改純漢字 lookup 或生成詞條的結果語意。
- 資料庫 schema、SQL／OPFS physical plan、詞庫初始化或 service worker 重構。
- 結果 virtualization、infinite-window library、UI redesign 或新的 memory
  eviction policy。
- 把完整 detail model 寫入 URL、history、session storage 或跨重啟恢復。
- 為 PWA、瀏覽器及 Portable 建立不同 Query Workspace implementation。
- 引入 Redux、XState 或其他 runtime state framework。
- Candidate 01、03、04、05 的後續擴張或與 #146 無關的既有錯誤。
- 在 PR 合併進 `main` 前關閉 #146。

## Further Notes

- 產品外框行數下降只是責任刪除的結果，不是獨立 KPI。
- Query Engine、query-tabs、search-navigation 及 entry-detail 的既有
  implementation 應作 adapters 的起點，不應重寫其 domain logic。
- 完成後使用 deletion test：移除 Query Workspace 應只移除 search workflow，
  不應同時破壞 PWA／Portable chrome、工作台或其他 sibling views。
- 若效能量度顯示主要瓶頸在 SQL／OPFS 或列表 DOM，而非 workflow/render
  locality，記錄結果並另開候選，不擴張 #146。
