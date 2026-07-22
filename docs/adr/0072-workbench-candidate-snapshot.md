# ADR-0072: 句格工作台候選快照

**Status:** accepted

句格工作台二字無約束池現有 74,909 列，但每個 400 筆擷取頁可重新掃描、過濾、排序完整池；PWA 更會把完整列跨 worker seam 傳回 main thread。為保留 ADR-0064／0071 的誠實完整池、穩定 `engineTotal` 與顯式續頁，同時移除重複成本，我們決定引入 **候選快照**。

## Decision

1. 同一候選查詢身份只建立一次 immutable **候選快照**：MatchSpec 過濾、固定排序、語意優先與按字面去重後、POS 投影前的完整池。第一頁等待快照完成；不顯示 provisional 排序。
2. 快照身份包含正規化比對規格、模式、語意意圖／種子、詞庫身份與關係資料 generation；不含 POS、offset／limit、`selectionVersion`。`selectionVersion` 只防舊候選套落新句稿。
3. 快照以 compact ordered handles 保存；字面／粵拼／碼／原因按 400 筆擷取頁 materialize。PWA 快照留在 browser query worker，Desktop 快照留在 Python 查詢進程；opaque handle 藏在既有 `WorkbenchAdapter` seam 後，不暴露給 React candidate session。
4. 每個工作台頁面一個 active snapshot；新 identity latest-wins，同 identity 合併等待。舊快照只可作 stale 顯示，新快照就緒後立即釋放；舊快照不可再續頁。POS 切換與續頁重用 active snapshot。
5. 零結果 relaxation 每個原快照只 probe 至第一個可用建議；創作者確認放寬後，放寬 plan 建立新快照。快照遺失時從第 0 頁原子重建，不把新頁 append 到舊候選。
6. Desktop 每個快照 idle TTL 10 分鐘，進程 retained snapshot budget 32 MB；PWA 由頁面 worker 生命週期回收。單一 active compact snapshot retained heap ≤8 MB；新舊切換短暫峰值 ≤16 MB。
7. 硬效能閘：同 identity 只做一次完整池 build；續頁／POS 不重掃完整池；worker／HTTP 每次最多傳當頁；過時 plan 不進 relaxation；main thread 無 >50 ms 候選 long task。暖庫 p95：中階手機無約束首頁 ≤1.5 s、桌面 PWA ≤750 ms、sql.js 降級 ≤2.5 s、續頁 ≤150 ms、已載資料足夠時 POS 切換 ≤100 ms 且零查詢。

## Considered Options

- React candidate session 保存完整候選物件 — rejected：完整池跨 seam、手機記憶體與 render 成本過高。
- 每個擷取頁維持 stateless 重算 — rejected：同一 plan 重複 full-pool implementation，POS 最多放大五次。
- 多 plan LRU 或跨 reload／磁碟快照 — rejected：YAGNI；先守每頁一個 active snapshot 與明確記憶體 budget。
- 未完成排序先出 provisional 400 — rejected：會破壞 offset、去重、`engineTotal` 與候選次序穩定性。

## Consequences

- PWA 與 Desktop implementation 可不同，但 observable paging、失效、relaxation 與 parity 契約相同；兩端同時通過才切換產品路徑，不保留長期新舊雙軌。
- 新測試以 deep module interface 為 test surface；覆蓋真庫 first/next page、POS reuse、latest-wins、原子重建、跨頁隔離、傳輸列數與效能／記憶體 budget，取代只釘住舊淺 implementation call shape 的測試。
- 本 ADR 不改 ranking、400 擷取頁、候選領域規則、CandidateGrid windowing、詞條庫 length invariant、整句讀音或一般搜尋 worker 形狀。
