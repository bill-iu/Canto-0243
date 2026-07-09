# P1：查詢分派 locality 地基（fillword SSOT、轉接 detect parity、PWA grammar 分家族）

Architecture review 後，**查詢分派** 在雙引擎（ADR-0024）下的摩擦集中於：連接詞字母表手抄、**搜尋模式轉接** 雙判定無共享案例表、PWA `parse.ts` 巨型淺 bag、以及 shadow `executeSearch` footgun。P1 **不**合併雙引擎、**不**把 MatchSpec builders 資料化（ADR-0035 已拒）。我們決定：

1. **搜尋入口唯一**（PWA）：只經 `QueryEngine.execute`／`query/engine.ts`；`query/dispatch.ts` **不得** export `executeSearch`（seam 鎖）。
2. **連接詞複合字母表**：`contracts/fillword-connectives.json` 為中立 SSOT；codegen 出 `_generated` 供 Python／TS import；`mode-detect.ts` **inline** 同字串（保持無 import，既有 mjs codegen 不變）。
3. **搜尋模式轉接 detect**：維持雙 adapter——Python `is_relation_syntax_query` 用 full parse；TS／frontend 用 regex。行為閘為 `contracts/relation-syntax-detect-cases.json`（家族代表集），`tests/smoke/test_mode_detect_parity` 強制兩邊一致。
4. **PWA 查詢分派地圖**：`client/src/db/query/grammar/*` 鏡像 `app/services/query_grammar/*`；`parse.ts` 只做 **分派優先序** chain；`rowToResult`／sort／equals empty-hint 歸 `result-map`／`equals-empty-hint`。P1 搬家 **禁止** 順手修跨引擎行為差。

**Considered Options**

- Detect 兩邊都 full parse／都 regex — 拒：UI 早期轉接要便宜；API 保險要以 parse 為準；parity 用案例表鎖即可。
- FILLWORD 以 Python 或 TS 單邊為 SSOT — 拒：偏渠道，違背 ADR-0035 中立精神。
- P1 只拆 relation、其餘留 megafile — 拒：locality 目標未達。
- P1 順手修 PWA／Python drift — 拒：審查面爆炸；另開 issue。

**Consequences**

- 改連接詞字母表：改 contract → `python scripts/codegen_fillword_connectives.py`。
- 改轉接判定語意：先擴 case 表再改兩 adapter，至 parity 綠。
- 新缺字／錨語法家族：PWA 落 `grammar/<family>.ts`，唔再塞回 mega `parse.ts`。
- 後續 P2／P3（近反義池投影、關係直寫、候選來源 contract）唔屬本 ADR。
