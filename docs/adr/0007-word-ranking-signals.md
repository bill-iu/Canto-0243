# 詞條排序信號收斂於 domain/lexicon

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 詞條排序信號、搜尋結果排序、等號參考讀音選列、缺字查詢字面優先。

**搜尋結果排序**與**等號參考讀音選列**的 tier 信號散落 `essay_sort`、`mask_priority_key`、`reference_reading` 內部；`mask_priority_key` 將 curated 排在 essay 之前，與 CONTEXT 相反。我們決定：於 `app/domain/lexicon/` 提供單一深模組，對外三條 key 加 `sort_search_results` helper——`search_result_sort_key`（扁平 **搜尋結果排序**）、`authoritative_reading_sort_key`（**等號參考讀音選列**）、`literal_priority_sort_key`（**缺字查詢字面優先**：`-exact_count` 前綴後接扁平 key，不重寫 essay／curated 順序）。同 PR 刪 `essay_sort.py` 與 `mask_priority_key`，不保留 `default_word_sort_key` 別名。

**Considered Options**

- 只統一扁平排序、等號選列留在 `reference_reading` 私有函式 — tier 仍分散，信號來源易再次分叉。
- 兩條契約收成同一 tier 順序 — 與 CONTEXT「選列 pron_rank 優先、結果排序 essay 優先」衝突。
- 模組留 `app/services/essay_sort` — 與 ADR-0004 將 lexicon 領域契約放 `domain/lexicon/` 不一致。
- 保留 `default_word_sort_key` 別名過渡 — 延長雙名稱，無額外呼叫端收益。
- #1 順手收斂近義複合 tier 前綴或 `code_aware_ranker` 版面 — 範圍膨脹，模糊本 ADR 邊界。

**Consequences**

- 必備測試：扁平 tier 單元、等號選列單元、字面優先組合、essay／curated 衝突回歸、缺字與純碼整合一致。
- `domain/relations/ranking.py`（**近反義池**）維持獨立契約，不併入本模組。
- 架構檢視不應再建議恢復 `essay_sort`／`mask_priority_key`，或在缺字路徑另訂 essay／curated 順序。