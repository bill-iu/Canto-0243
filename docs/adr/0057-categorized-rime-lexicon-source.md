# ADR-0057: Rime 分類詞語來源取代 legacy phrase

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 分類詞語來源、短語補缺來源、短語收錄門檻。

取代 [ADR-0047](./0047-lexicon-volume-and-phoneme-contract.md) § 1.2 以後綴拒收表清洗預設短語來源嘅做法。

## 決策

1. 預設詞庫直接讀 `rime-cantonese-upstream` 分類 CSV：`word`、`fixed_expressions`、`phrase_fragment`、`onomatopoeia`、`trending`。
2. 資料入口排除 `proper_nouns`；唔靠字面 classifier 或 Essay 詞頻判斷專名。
3. 沿用 `rime_words` source id／bitmask；舊 `rime_phrase` parser 保留作維護者顯式分析，但預設停用。
4. 值得保留而其他分類未覆蓋嘅 legacy 短語，經審核後移入 curated，唔建立長期 rescue 黑名單流水線。

## 理由與後果

舊 phrase 檔混合輸入法用戶詞庫同城市資訊；大量噪音係同模板專名，唔係 literal duplicate。來源分類白名單可以同時排除專名家族同保留真正三／四字詞，亦令每次重建結果可重現。維護者需先執行分類 CSV fetch；缺檔時按既有 `local_only` 規則跳過。
