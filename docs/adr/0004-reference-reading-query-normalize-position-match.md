# 參考字讀音解析、查詢分派收斂與缺字型執行套件化

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 參考字讀音解析、查詢分派、缺字型查詢執行、韻／聲錨。延續 [ADR-0002](0002-mask-family-dispatch-spec-boundary.md)。

架構檢視後，**參考字讀音解析**編排散落、`mask_family_normalize` 與 `query_parse` 分裂、`position_match.py` 仍為巨石並保留 legacy seam。我們決定分三個工作包、固定實作順序 **#2 → #3 → #1**：

1. **#2 參考字讀音解析** — 新深模組於 `app/domain/lexicon/`，對外兩入口：**錨點音素選項**（韻／聲錨）與**等號參考讀音**（等號／碼夾等號）；呼叫端明示 `allow_inject`（查詢比對可注入，**詞庫快取索引**候選與預載不注入）；解析不隱式 sync，僅 `ensure_word_in_db` 注入成功後更新快取。多讀音：錨點 union 選項；等號取 `pron_rank` 單列（平手 → Essay 詞頻 → 略過 `aa` 變體 → 粵拼序）。刪 `phoneme_lookup.py`。
2. **#3 查詢分派收斂** — `mask_family_normalize.py` 併入 `query_parse.py`；正名 `normalize_to_match_spec`（`build_match_spec` 暫作 alias）；別名改寫（`HybridTailEqualsAlias`）在 `normalize_to_match_spec` 開頭；`query_dispatch` 保留薄 `_mask_family_search_result`，內部單次 normalize，**等號查詢**仍 `run_equals_query` 直至執行 registry 支援等號 spec。測試併入 `test_query_parser.py` 並更新 `test_mask_family_seam.py`。
3. **#1 缺字型查詢執行** — 先刪 `execute_mask_family_search` 與 `position_match` 對 normalize 的 re-export；再抽候選 registry 為 `app/services/position_match/`（`sources.py` + `engine.py`），`__init__.py` 僅 export `MatchSpec`、`SlotConstraint`、`execute_match_spec`、`run_equals_query`、`MaskFamilySearchResult`；`filters` 延後第三個 micro-PR。

**Considered Options**

- 參考字解析留在 `services/phoneme_lookup` 並允許索引建置時隱式 ensure — 與 CONTEXT「索引路徑不注入」衝突，查詢期意外寫庫。
- 等號與錨點共用單一 `resolve_reference` — 整詞等號要音節序列、錨點要 option set，介面過寬。
- `normalize` 併入 `query_dispatch` 或新檔 `query_normalize` — 分派檔變胖或仍三角跳轉；併入 `query_parse` 最符合 ADR-0002「分派層正規化」。
- 等號改走 `execute_match_spec` 與 #1 同 PR — registry 尚未支援等號 spec 形狀，綁死兩包 review。
- 一次拆完 `position_match`（registry + engine + filters）— rollback 面過大。

**Consequences**

- 實作 #2 應在或早於 #1 動 `position_match` 內 `phoneme_lookup` 呼叫點，避免同一檔雙重改動。
- `CompoundSyn`／`CompoundAnt` 的 `MatchSpec` 建構併入 `normalize_to_match_spec`，與缺字家族同一入口。
- 等號快路徑移除條件：#1 讓 `_resolve_mask_family_source` 處理等號 `MatchSpec` 後，可改為全 `execute_match_spec`。
- 架構檢視不應再建議恢復 `phoneme_lookup` 隱式 ensure／sync，或把 `mask_family_normalize` 獨立檔當長期 seam。