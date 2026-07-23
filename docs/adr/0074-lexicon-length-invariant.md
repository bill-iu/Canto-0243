# ADR-0074: 詞條庫字數不變式

## 問題

正式 `lyrics.db` 已無 `NULL`、零值或錯誤 `words.length`，但 Python 與 PWA 約二十條 runtime 查詢仍保留 `length(char)` OR fallback。SQLite 因此放棄 `(length, code, finals)` 複合索引；實際詞庫代表性查詢由 indexed search 約 0.04 ms 退化成全表掃描約 12.9 ms。

## 決定

1. **正式詞條庫嚴格**：建置 finalize 與雙端開庫驗證每列 `length` 存在、非零且等於 `length(char)`；失敗不得通過就緒閘。
2. **本機 legacy 修復**：Desktop 本機舊庫只經顯式 repair adapter，以單一 transaction 修正全部錯列並再次驗證；修復完成前不提供搜尋。
3. **PWA 恢復**：開庫不合格時關閉 backend、清除該版本快取並從交付頻道重開一次；重開仍不合格即失敗。
4. **runtime 收斂**：正常 Python／PWA 查詢只用 `length = ?`；移除 `OR length(char)` 與 `wordMatchesWidth` 防守。
5. **不重建資料表**：不為此遷移既有 SQLite 表加入 `NOT NULL CHECK`；不可變發佈物由建置／開庫 validator 保證，所有寫入入口仍須產生正確 `length`。
6. **驗收**：release gate 以 `EXPLAIN QUERY PLAN` 保證代表性 length／code／finals 查詢命中指定複合索引，並跑雙端黃金查詢 parity；wall time 只記錄，不作易波動硬閘。

## 後果

- 一般搜尋與句格工作台共用索引收益，兼容知識不再散落 caller。
- 壞正式資產會顯式失敗或重下載，不再以較慢但看似正常的查詢掩蓋。
- 開庫增加一次完整性 probe；相對詞庫下載、開庫與快取預載成本很小。
