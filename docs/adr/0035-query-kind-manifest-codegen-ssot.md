# 查詢種類 meta：中立 manifest + codegen（雙引擎 SSOT）

在 ADR-0024 雙引擎（Portable Python + PWA TS）下，**查詢種類**的 route／MatchSpec 旗標曾手抄兩表，結構 parity 只靠行為／golden，locality 差。我們決定：以 `contracts/query-kind-manifest.json` 為**中立單一寫入點**（kind id 全集 + `route` + `match_spec`；**不含** MatchSpec builders）；codegen 產出 `app/services/_generated/` 與 `client/src/db/_generated/`；既有 `query_kind_registry` facade **只 re-export**，call site 路徑不變；CI `codegen --check` 鎖生成物 clean。kind id **零 rename**，對齊現有 `QueryKind` 字串。

**Considered Options**

- Runtime 雙端直接 load JSON — 弱化靜態型別與現有 `QueryKind.*` 用法。
- Python 為作者 SSOT、codegen 只出 TS — 看起來偏 Portable，違背中立 seam。
- 雙表手維 + CI 集合相等 — 測得到 drift，仍非單一寫入點。
- Manifest 含 MatchSpec builders — 邏輯不可資料化；builders 維持雙 port（後續相）。

**Consequences**

- 新增**查詢種類**：改 manifest → 跑 codegen → 再補 parse／builder（若需要）；唔再手改兩份 meta 表。
- 生成檔勿手改；dirty 生成物 PR 應紅。
- 與 ADR-0002（缺字型正規化在分派、執行只收比對規格）相容：本 ADR 只鎖 **種類→路由／是否 MatchSpec** 的 meta，唔搬 normalize 實作。
