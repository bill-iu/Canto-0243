# P3：候選來源 policy 中立 contract（+ 雙引擎可表化 inventory）

雙引擎（ADR-0024）下，**缺字型查詢執行** 的 length-bucket 截斷曾靠 comment「keep in sync」（Python `sources.CANDIDATE_FALLBACK_LIMIT` ↔ TS `candidate-policy.ts`）。P3 決定：

**#7 候選來源 policy**

- SSOT：`contracts/candidate-source-policy.json`（`candidateFallbackLimit`，現行 `2000`）。
- Codegen：`scripts/codegen_candidate_source_policy.py` → `_generated`（Python／TS）；CI `--check`。
- Call sites import 生成常數；equals 路徑 `LIMIT` 同用此值。
- **Unlimited** length-bucket 仍由 adapter 傳 flag（`lengthBucketNeedsUnlimited`）；**唔**在 contract 枚舉「邊種 anchor unlimited」（mapping 易 drift）。
- **唔**把 MatchSpec builders 資料化（ADR-0035 已拒）。

**#5 其餘契約（本 phase 範圍）**

- 本 ADR 附 **inventory**（下一批可表化候選）；本 phase **唔**強制落地第二個 contract，除非極便宜。

### Inventory（下一批可表化）

| 候選 | 現況 | 建議 |
|------|------|------|
| FILLWORD 字母表 | 已 SSOT（ADR-0040） | — |
| 轉接 detect cases | 已 SSOT（ADR-0040） | — |
| 候選 fallback limit | 本 ADR | — |
| ADR-0039 CAP-U@20 | Python domain 常數 | 可 contract 數字 |
| 關係池 DEFAULT_PAGE_SIZE | 雙端常數 | 可 contract |
| query-explain-parity fixtures | 已有 contract，可擴案例 | 擴表即可 |
| MatchSpec builders | 雙 port 邏輯 | **仍唔** JSON 化 |

**Considered Options**

- Runtime 雙端 load JSON — 弱靜態型別。
- Policy 表含 unlimited 規則枚舉 — mapping 層仍手維，收益小。
- 本 phase 大搞 builders／explain 行為表 — 超出「政策／表格式」；拒。

**Consequences**

- 改截斷上限：改 contract → codegen。
- 新 candidate source adapter：讀 `CANDIDATE_FALLBACK_LIMIT`，unlimited 用 flag。
