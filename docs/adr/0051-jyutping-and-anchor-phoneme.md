# ADR-0051: 粵拼錨、歧義雙列與錨點選項

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 粵拼錨、獨立鼻音韻母、歧義粵拼錨雙列結果、錨點選項、語境錨點選項、等號參考讀音。

整合並取代：[0005](./0005-jyutping-anchor-query-syntax.md)、[0009](./0009-ambiguous-jyutping-anchor-dual-results.md)、[0029](./0029-anchor-phoneme-options-exclude-rare-pron-rank.md)。  
相關但**獨立**：位置錨語法（通配碼錨／slot 連接符／串列）見 [0052](./0052-positional-anchor-query-syntax.md)；碼夾等號 [0028](./0028-code-sandwich-equals-unification-and-per-digit-loose-variants.md)。分派 seam 見 [0046](./0046-query-dispatch-seams-and-ssot.md)。

## 1. 粵拼錨與三格韻錨（語法）

1. **三格韻錨** — `?{字}=?` 中格韻母；優先於 mask／WordLookup 誤判。
2. **粵拼錨三子類** — 聲母、韻母（含獨立 `m`≡`ng` 片段規則）、完整音節（唔限調）。
3. **碼＋拉丁** — 二字／三字模板（`3hon4`、`3?hon4`、`23o` 等）見原 0005 細節。
4. **分派** — 缺字家族優先於整段粵拼查詢；讀音唔到則提示，唔空降級。
5. **範圍** — 僅 0243 搜尋模式；近反義唔收粵拼錨。

## 2. 歧義 `m`／`ng` 雙列

1. 碼夾或三格中格為 **`m`／`ng`** → 並行 **聲母列** + **韻母列**（獨立鼻音）；其餘單列。
2. 獨立鼻音音節**只**韻母維；韻母列 `m`≡`ng`，聲母列 `m`≠`ng`。
3. `gw`／`kw` 等雙聲母僅聲母、無雙列。
4. `limit`／`offset` 對合併序列；結果帶 `anchor_dimension`。

## 3. 錨點選項剔罕見

1. **錨點選項** union：剔 rime **罕見**；預設／常用／未知仍入。
2. **語境錨點選項**：唔剔罕見（組詞讀音）。
3. **等號參考讀音**：仍 pron_rank 單列；唔改成「尾韻全走權威單列」（與 0028 一致）。
4. 雙端 parity（Python + PWA）。

**Consequences** — `39難` 唔再因罕見 `no4` 噴 `o` 韻；`3m4` 雙列分節；解釋層用「第 N 個字」。
