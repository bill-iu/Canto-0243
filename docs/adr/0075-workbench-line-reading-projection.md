# ADR-0075：工作台讀音投影批次、快取與取消

## 問題

Portable 整行讀音 resolver 逐字呼叫權威讀音入口再查 `words`，同一字可重複查詢，亦可能在工作台讀取路徑注入詞條。PWA 雖已有單次 `IN` 查詢，但兩端生命週期不同；畫面各編輯入口會重解整行，只以版本丟棄晚到結果，未真正取消，並可能覆蓋未改格的創作者選擇。

## 決定

1. **唯讀邊界**：工作台讀音投影只讀既有 `words`；不注入詞條。純漢字 lookup 的記憶體臨時詞條生成維持不變。
2. **批次與 parity**：Portable／PWA 對每批不同字面各查一次，再按輸入 Unicode code point 順序展開，重複位置仍可獨立選讀音。
3. **adapter 快取**：每個 adapter instance 由詞庫身份綁定一個最多 1,024 字的 LRU；resolved、unresolved 與 punctuation 均可快取，相同進行中 miss 批次共用 promise。
4. **合作式取消**：共享批次追蹤等待者；所有等待者取消時才 abort 底層 fetch。單一編輯請求因此會真正取消，又不會誤殺仍在等待的共用 caller。
5. **單一 coordinator**：新增、貼上、單格／區段修改、還原及重試均經同一讀音 coordinator。新請求先取消舊請求；只有沒有既有選定讀音的漢字格會送 resolver，未改格保留創作者選擇。
6. **驗收**：公開 resolver／adapter／coordinator 測試查詢與請求次數、無寫庫、negative cache、LRU、coalescing、cancellation、latest-wins 與選讀音保留；wall time 只記錄。

## 後果

- Portable 整行讀音由每格最多兩次查詢收斂為每批一次 SELECT。
- 連續編輯主要命中 adapter cache，重複字及未收錄字不再反覆查庫。
- 讀音投影與 lookup admission 分離，雙端語意一致；工作台不再因讀取而改變詞庫。
- 快取只活於 adapter，詞庫版本切換或工作台 adapter 重建時自然失效。
