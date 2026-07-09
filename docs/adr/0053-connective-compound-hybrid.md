# 連接詞複合：詞庫 ∪ 合成 + syn/ant 互斥

**連接詞複合查詢**（`~與~`／`!與!` 等）候選改為 **詞庫已有三字 ∪ 由 ~~／!! flank 合成**（缺庫者以單字＋連接詞讀音拼粵拼／碼），詞庫命中優先、合成殿後；~ 與 ! **嚴格互斥（ant-wins）**：~ 剔除亦屬 ant 嘅對，! 保留完整 ant primary；flank **雙向**。雙端（Portable Python + PWA TS）對齊。拒絕「只掃三字詞庫」（數量遠低於 ~~）同「~ 混入反義對」。Portable **請求路徑唔寫庫**（記憶體合成列）見 [ADR-0054](./0054-portable-read-path-no-write-connective.md)。
