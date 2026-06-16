# 近義／反義複合併入缺字型查詢執行

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 查詢分派、缺字型查詢執行、近義複合詞、反義複合詞。延續 [ADR-0002](0002-mask-family-dispatch-spec-boundary.md)、[ADR-0004](0004-reference-reading-query-normalize-position-match.md)。

~~／!! 已由 **查詢分派** 分類為 `CompoundSynQuery`／`CompoundAntQuery`，但執行仍經獨立 executor 直呼 `run_position_query`，與缺字家族走 `execute_match_spec` 的 seam 分裂；反義複合候選規則亦散落在 executor glue。我們決定：

1. **查詢分派** 以 `uses_match_spec(parsed)` 路由（缺字家族 ＋ 複合詞）；語法上 ~~／!! **仍非**缺字型查詢家族。
2. `normalize_to_match_spec` 為複合詞填入 `MatchSpec.compound_kind`（`syn`／`ant`）。
3. **缺字型查詢執行** registry（`_resolve_mask_family_source`）依 `compound_kind` 呼叫 domain 候選 API，注入 `CompoundSynCandidateSource`／`CompoundAntCandidateSource`（cache-first）。
4. 刪除 `compound_syn_executor`、`compound_ant_executor`；反義候選收斂至 `domain/relations/compound_ant.py`。

**Considered Options**

- 擴充 `is_mask_family_query` 含複合詞 — 與 CONTEXT「缺字家族不含 ~~／!!」矛盾。
- Domain 直接實作 `CandidateSource` — domain 反向依賴 execution protocol。
- 保留 executor 作 deprecated wrapper — deletion test 失敗，seam 未關閉。

**Consequences**

- 新增複合變體時：改 `query_parse` 分類、`normalize_to_match_spec`、domain 候選 API；`query_dispatch` 不再增 handler。
- 反義複合與近義複合在詞條投影上均 cache-first。
- ADR-0004「CompoundSyn／CompoundAnt MatchSpec 併入同一入口」於 dispatch 層落地。
