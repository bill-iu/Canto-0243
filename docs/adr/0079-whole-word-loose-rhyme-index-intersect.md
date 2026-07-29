# ADR-0079: 整詞放寬韻用 runtime 音位索引 ∪／∩（唔加 DB 欄）

領域：見 [CONTEXT.md](../../CONTEXT.md) § **整詞放寬韻索引併查**、**韻母比對檔**、**韻母分組表**。  
相關：[0078](./0078-rhyme-match-profile.md)、[0047](./0047-lexicon-volume-and-phoneme-contract.md)。Grill 共識（2026-07-29）。

## 問題

**韻母比對檔** 非正韻時，整詞 `=`（whole-word equals）不能再用 `finals` 等值 SQL，一度 **unlimited 掃 length 桶** 再 filter——正確但慢。若在 **詞條庫** 加分組 id 欄會增大 lyrics.db，與體積契約相悖。

## 決定

1. **R1**：純 **runtime** 優化；**唔**在 words 表／lyrics.db 加通韻／腹／尾分組欄。
2. **S1**：只優化 **整詞 + 韻維 + 非正韻**；正韻整詞維持精準 `finals` 等值；prefix-wildcard 等第一期唔動。
3. **演算法**：既有 `(length, pos, final)` 音位索引——每位對參考韻母 **expand** 後多 key **∪**，跨位 **∩**；再 **C1** 既有碼鬆檔過濾；**R2** 正韻層優先排序不變。
4. **F1**：索引未就緒 → 回退掃桶 + 分組 filter（正確優先）；就緒即用併查。
5. **P1**：**Desktop** 與 **PWA** 行為一致（各接 word_cache／phoneme-index）。
6. **否決第一期**：分組 id 入主表；phoneme index 鍵加入 code digit（C2）。

## 考慮過

| 方案 | 結論 |
|------|------|
| 掃桶維持唯一路徑 | 太慢；拒絕作正路 |
| DB 分組欄 | 脹庫；拒絕第一期 |
| Index 鍵含碼 | 鍵約 2.8×、鬆檔 union 更嘈、邊際收益小；拒絕第一期 |
| 只優化 PWA | 結果分叉；拒絕 |

## Status

`accepted`（grill；實作跟本 ADR）
