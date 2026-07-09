# ADR-0039: Cilin 葉碼存儲 + 無向 syn 度上限

`word_relations` ~19 MB 中，Cilin 邊帶完整 `group_codes` JSON 階層（~40B／行，約 7.7 MB 字節），排序卻只用葉碼與深度（`leaf_code_to_hierarchy_codes` 可還原）。syn 邊由葉組 **完全圖** 物化，單字度可 >200，與 **靜態詞林埠** runtime 重疊。

**GC1**：欄位存 **葉碼字串**（如 `Aa01A01=`）；讀取時 expand 為階層。相容舊 JSON 陣列。

**S1 CAP-U@20**：入庫／修剪時 greedy 保留高 score、優先 cilin，使每端點無向 syn 鄰居 ≤20。ant／semantic 唔 cap。

**S2（後續）**：改葉組成員表、查詢 expand，取代完全圖物化。

**後果**：大組遠鄰可能只靠 static 補；近義排序仍可用葉碼。`python -m ingest.trim_relations_adr0039 lyrics.db` 改現庫；`build_word_relations` 寫入已 cap + 葉碼。
