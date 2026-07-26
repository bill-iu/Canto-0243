# ADR-0046: 查詢分派 seam 與雙引擎 SSOT

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 查詢分派、缺字型查詢執行、候選來源截斷、語意完整候選宇宙、比對規格、查詢種類、搜尋模式轉接。

整合並取代：[0002](./0002-mask-family-dispatch-spec-boundary.md)、[0004](./0004-reference-reading-query-normalize-position-match.md)（工作包計畫）、[0035](./0035-query-kind-manifest-codegen-ssot.md)、[0040](./0040-p1-query-dispatch-locality.md)、[0042](./0042-p3-candidate-source-policy-contract.md) 之**分派／SSOT 活決策**。語法家族細節（粵拼錨、串列等）仍見各專題 ADR（0005、0009、0012–0014…）。

## 1. 缺字型 seam

1. **正規化在分派** — ParsedQuery → **比對規格**（MatchSpec）在查詢分派完成。
2. **執行只收規格** — `execute_match_spec`／PWA 對等路徑**唔**再按 ParsedQuery 型別梯分支。
3. **參考字讀音** — 錨點選項 vs 等號參考讀音兩入口；呼叫端明示 inject（見 domain `reference_reading`）。

## 2. 查詢種類 meta SSOT

1. **`contracts/query-kind-manifest.json`** — kind id + `route` + `match_spec` 旗標；**不含** MatchSpec builders。
2. Codegen → `_generated`（Python／TS）；facade re-export；CI `--check`。

## 3. 分派 locality（P1）

1. PWA 搜尋入口唯一：`QueryEngine.execute`（無 shadow `executeSearch`）。
2. FILLWORD：`contracts/fillword-connectives.json` + codegen；mode-detect inline。
3. 轉接 detect：full-parse vs regex 雙 adapter；案例表 `relation-syntax-detect-cases.json` + parity 測。
4. PWA `query/grammar/*` 鏡像 Python `query_grammar/*`。

## 4. 候選來源 policy（P3）

Grill 2026-07（跟進 `$獅`／`9太=2` 漏命中）：**唔**取消所有候選來源截斷；保留預設上限，用正確性準則決定何時必須 **語意完整候選宇宙**。

1. `contracts/candidate-source-policy.json` → `CANDIDATE_FALLBACK_LIMIT`（預設 **候選來源截斷** 數字）。
2. 何時改用完整宇宙由 adapter／執行層 flag 表達，**唔**枚舉在 contract。
3. **正確性準則（B1）**：只保證**語意後置過濾**嘅召回。截斷後仍會因語意約束剔詞 → 必須語意完整候選宇宙。純碼／純 mask、無語意後置約束嘅冷路徑可截；大結果集冷路徑唔完整係已知取捨，**唔**當同款 bug。
4. **權威表達（T1）**：抽象規則如上；**最小列舉**（目前必用語意完整候選宇宙）：粵拼字母槽、聲韻錨、等號／碼夾 span（含 `phoneme_anchor_only`）。新家族預設過呢條，唔係預設截斷。
5. **唔做**：一律 `unlimited`；只調高上限當根治；把結果分頁 `limit` 叫候選來源截斷。

**Consequences** — 新語法：改 parse／builder／manifest；執行層只動 filters／sources，並核對是否觸發語意完整候選宇宙。雙引擎可表化規則優先進 `contracts/`。漏網路徑（例如整詞等號仍截斷、雙端判斷出口未統一）另開稽核，唔綁死本決策。
> Superseded by [ADR-0076](./0076-canonical-matchspec-compiler.md). The historical dispatch and execution decisions remain here for context.
