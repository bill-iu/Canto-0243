# Portable 讀路徑：連接詞合成唔寫庫 + word_cache disk 暖啟

**Portable** 就緒閘與搜尋唔應在請求路徑上為 **連接詞複合** 做 `ensure_word_rows` 逐條寫 SQLite（會鎖庫、令 `~與~` 卡死並拖垮並行嘅 `?+就=`／`23+就=`）。對齊 **PWA** 體驗：搜尋結果可含 **記憶體合成列**（音節拼接讀音），只存在結果集。**詞庫快取** 以 disk snapshot（`.cache/word_meta.bin`）restore 優先、冷建後必 persist，對齊「開現成索引」而非每次 ORM 全表重建。Seeds 亦唔在請求路徑寫庫。

拒絕：請求內 batch-commit 仍寫庫（仍爭鎖）、把查詢改打 PWA TS（範圍過大）。見 CONTEXT § 連接詞複合查詢、詞庫快取索引、就緒閘。
