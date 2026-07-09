# ADR-0050: 近反義 runtime — 直寫、池投影與衍生反義

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 關係直寫、近反義池投影、詞林衍生反義、反義端點鏡射、關係圖、靜態詞林埠。

整合並取代：[0041](./0041-p2-relation-write-and-pool-projection.md)、[0043](./0043-runtime-derived-antonyms.md)（及舊 0023-runtime stub 鏈）。

## 1. 關係寫入（ingest）

1. Release／`build-db` 熱路徑 **只** `build_word_relations`（記憶體集 + bulk）。
2. Legacy CLI（`ingest-cilin` 等）**委派**同一路徑；`ingest_cilin_leaf_direct` 僅 tests／legacy。
3. bake／expand snapshot 可獨立，**唔**當第二套 bulk 寫入契約。

## 2. 近反義池投影（讀）

1. Runtime 只經 `project_relation_pool`／`projectRelationPool`；builder 為內部。
2. **Inject 不對稱**：Portable 可 `allow_inject`；PWA **永不** inject。
3. 測試可直 call builder。

## 3. Runtime 衍生反義

1. **查詢時**展開詞林衍生 + 反義端點鏡射；**唔**寫 `word_relations`、唔 inject 建庫熱路徑。
2. **近反義模式**與 **`!`** 共用池；順序：先詞林衍生，再鏡射。
3. 詞林鄰居：靜態 cilin-only；鏡射：關係圖全源 syn。
4. 候選須在 membership 內。
5. 忽略 DB 舊 `ant_cilin_exanded`／`ant_syn_mirror` 等 source。
6. 關係圖 **進程級 lazy cache**。
7. TSV 快照僅 maintainer 回歸，非創作者 SSOT。
8. 優化須同時守搜尋 bench 與建庫 ≤10 分。

**Consequences** — 建庫較快；首次近反義可能付建圖成本；CLI expand 保留 debug。
