# 句格工作台「只合音格」候選排序設計

## 已確認決策

- `sound_only` 不再使用查詢頁／快照中的 `rowRank` 作為主要排序依據。
- 主要排序採現有 canonical search ranking：Essay 詞頻降冪，並沿用 curated boost、讀音優先級、字面與粵拼穩定 tie-break。
- `direct_syn` 與 `semantic_related` 維持關係來源順位，不被詞頻排序改寫。
- PWA 與 Portable 兩端使用同一個排序契約，避免同一查詢在不同執行端出現不同候選順序。
- 押韻、同聲等替換條件，以及 POS 詞性篩選，均在 canonical 結果上運作；POS 只移除不符合項目，不重新打亂剩餘順序。

## 原因

關係 priority pool 會先插入快照，且候選頁會逐頁投影；`rowRank` 反映的是當前輸入列／頁面位置，不是候選詞條的常用度。只在 `sound_only` 分組後套 canonical ranking，可以修復常用詞不在前面的問題，同時保留關係組的產品順位。

## 驗收

1. 輸入列順序與詞頻相反時，`sound_only` 仍按 Essay 詞頻由高至低顯示。
2. 詞頻相同時，仍有 deterministic tie-break，不依賴 SQLite／陣列插入順序。
3. `direct_syn`／`semantic_related` 的 relation rank 與既有順序不變。
4. 加上 POS 篩選後，保留 `sound_only` 的 canonical 順序。
5. 押韻／同聲 dual union 在分頁前完成 canonical merge sort。
6. PWA build、Portable/Python workbench test 與既有 smoke test 全部通過。
