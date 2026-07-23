# ADR-0071: Workbench unanchored full-width scan and bounded POS over-fetch

句格工作台將 0243 碼設為「不限定」後，仍然應按目前啓用嘅音／碼／語意條件誠實掃描；無音位錨時不應因 planner safety gate 靜默變成空結果。創作者 POS 篩選係前端三軸篩選，不能靠只取首批原始候選後判斷，否則稀疏 POS 會漏結果。

## Decision

1. 無有效碼約束、無同韻／同聲錨時，planner 掃描完整替換寬度候選池；其他已啓用條件仍然生效。
2. 有語意種子時，先以當前碼／同韻／同聲 MatchSpec 篩選，再把仍符合條件嘅候選固定合併為直接近義、語意相關、其餘；按字面去重後才套 `offset`／`limit`。關係候選不得繞過 MatchSpec，亦不得因原 canonical 位置落在首批之外而消失。`semanticIntent=off` 時全部歸 `只合音格`。
3. API 與 PWA 每次最多回傳 400 筆；`engineTotal` 代表 canonical 合併池總數。
4. POS 篩選留喺 client candidate session。啓用 POS 時，每個 fetch cycle 最多自動探測 5 頁（2,000 筆原始候選）；不足篩後目標即停，保留 `hasMore` 讓使用者繼續載入。缺 POS 載體嘅字面不入選。
5. 未啓用 POS 時不預先灌完整詞庫；按 400 筆頁面按需載入。

## Considered

| Option | Result |
|--------|--------|
| Keep unanchored queries empty | Rejected — violates honest unrestricted-code scanning |
| Filter POS only in the first engine page | Rejected — sparse passive candidates disappear |
| One unbounded response | Rejected — unsafe for the 74k+ two-character pool |
| Auto-scan until 400 POS matches without a cap | Rejected — can issue ~188 requests for a sparse filter |
| Put POS data into `ReplacementPlanV1` | Deferred — duplicates the project POS carrier in both runtimes |

## Consequences

- `engineTotal` and every offset refer to one stable canonical pool.
- Portable and PWA planners must keep their full-bucket and grouping behavior in parity.
- A sparse POS result may need an explicit「載入更多」before all matches are seen; `hasMore` makes that state visible.
- Existing 400-page contract (ADR-0064) remains the transport limit; this ADR adds the bounded POS over-fetch rule.
