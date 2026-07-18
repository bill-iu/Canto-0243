# ADR-0060: 庫內難標 `u` — fragment 分流與 POS alias

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 詞性與分類（**詞性碎片**、**詞性字面別名**、**詞性雙軌覆蓋**）。

## 決策

1. **庫內** 仍 `pos=u` 的字面分流（唔一律 formal、唔一律踢庫）：
   - **residual**（複合詞殘字）→ 完整詞為真詞位；
   - **clause-slice**（截斷句／半語）→ 永 **未定**；
   - **opaque**（庫內有、暫不敢 formal）→ 永 **未定** 直至人手改判。
2. **殘字** 不進 **專案自建詞性清單** 主表作獨立 formal 列。權威對照在 **詞性字面別名** 表（`data/pos/alias.tsv`）：`source → target`。主表只收 **target**（完整詞）。
3. 完整詞若不存在：先經 **詞級標音 curated** 入詞庫（可與 POS／alias **同 PR**），再建 SSOT 列；**禁止** POS 腳本旁路寫詞庫。
4. 殘字 **暫留詞庫 membership**（lookup 仍可命中單字）；POS 查詢經 alias resolve 到完整詞標籤（載體可選附 alias；缺則當缺標）。
5. alias **入帳人手**；CLI 可出高信心 **提案**（唔 silent merge）。
6. 覆蓋指標 **雙軌**：`formal/all` 與 `formal/(all−fragment)`。庫內難標修復 v1 收工條件：`formal/(all−fragment) ≥ 95%` 且 fragment 皆有 `residual|clause-slice|opaque` 類型 token。
7. 大批 agent formal 晉升：**每批** 抽樣品質閘 **≥90%** 先合入。
8. 推進序：fragment／alias 管道 → 既有 u_repair + 模式熟語 → Essay 非 fragment top-N。

## 理由

Essay 高頻 `u` 頭係切詞殘片與殘字，再燒 agent 會重複撞同一批假詞位。主表收殘字 formal 會毒閘；踢庫過兇誤傷自由語素。獨立 alias + curated 補完整詞，對齊「SSOT ⊆ 詞庫字面」與「一 literal 一可標詞位」。

## 後果

- 新增 `data/pos/alias.tsv` 與提案檔；ingest 提供 propose／apply／status。
- 覆蓋報告須報雙軌；單報 formal/all 易誤讀。
- 載體／runtime resolve alias 可分期；第一期至少清單側清主表殘字。
- 與 ADR-0058（獨立詞性載體）相容；唔改 lyrics.db 主表權威。
