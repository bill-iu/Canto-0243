# P2：關係直寫熱路徑 + 近反義池投影讀入口

Architecture review Phase 2：ingest 對 `word_relations` 曾有 leaf_direct／static／build 多條寫入；runtime **近反義池** 名義上有 **近反義池投影**，但 PWA entry-detail 仍直 call builder。P2 **只做入口紀律**，唔要求雙引擎池 merge 行為合一套、唔改 inject 不對稱。

**#6 關係寫入**

- Release／`build-db` 熱路徑 **只** 經 `build_word_relations`（**關係直寫**：記憶體集 + bulk）。
- Legacy CLI `ingest-cilin` **委派** 同一路徑（驗證 cilin 存在後 call `build_word_relations`）；`ingest-static-relations` 早已委派。
- `ingest_cilin_leaf_direct` 僅 tests／legacy helper；**唔**作 release 寫入口。
- bake／expand／衍生反義 snapshot 可獨立存在，但唔另開第二套 bulk 契約取代直寫。

**#4 近反義池投影**

- Runtime 讀：Python 只 `project_relation_pool*`；PWA 只 `projectRelationPool`／facade 投影 API（唔 re-export `buildRelationPool`）。
- Builder 為 projection 內部 implementation；seam 鎖 services／entry-detail 唔 import `build_pool`／`buildRelationPool`。
- **Inject 不對稱**（刻意）：Portable 可 `allow_inject` ensure 詞條列；PWA **永不** inject。入口統一，政策旗標語意可不同。

**Considered Options**

- 刪除所有旁路 CLI — 拒：破壞 maintainer 增量習慣；委派即可。
- 雙引擎池 golden parity — 拒：P2 範圍過大；另開。
- PWA 加 inject 對齊 — 拒：行為變、超出入口紀律。

**Consequences**

- 改 static 關係入庫：走 `build-word-relations`（或委派 CLI）。
- 改 runtime 近反義讀：改 projection／builder 內部，唔在 entry-detail 旁路建池。
- 測試可用 `build_pool`／`buildRelationPool` 直測 implementation。
