# ADR-0046: 查詢分派 seam 與雙引擎 SSOT

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 查詢分派、缺字型查詢執行、比對規格、查詢種類、搜尋模式轉接。

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

1. `contracts/candidate-source-policy.json` → `CANDIDATE_FALLBACK_LIMIT`。
2. Unlimited 桶由 adapter flag，唔枚舉在 contract。

**Consequences** — 新語法：改 parse／builder／manifest；執行層只動 filters／sources。雙引擎可表化規則優先進 `contracts/`。
