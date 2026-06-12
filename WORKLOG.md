# 0243 離線押韻字典 — Worklog

**期間**：2026-05 ~ 2026-06 · **棧**：FastAPI + SQLAlchemy + SQLite（離線）+ HTML/JS  
**目標**：快速粵語押韻搜尋（0243／等號韻／wildcard／近反義）。**原則**：ingest 重型、runtime 無 ML、純 SQL + static thesaurus。

**Enforcement**（每次實質變更）：`python -m unittest discover -s tests -q` + `python scripts/enforce_bench.py`。關鍵 case：`事業`、`門0`、`好23`、`_識_`、`香港=`、`香=?`（慢）、`23就`、`2=我3`、syn `快樂`。

---

## 硬性規範

- 禁 `hanzi` → 用 `canto` / `chars`
- Regex 僅 Python 解析輸入；**禁** DB regex
- Schema/backfill → `ensure_*`，lifespan/`__main__` 顯式呼叫；禁 import side-effect
- 瞬間搜尋：preload 後常見查詢 <0.2s（慢 case `香=?` 除外）；**禁**為加速改結果集／排序

---

## Schema 與模組（現況）

| 件 | 說明 |
|----|------|
| `words` | char / jyutping / code / length / finals / embedding(optional) |
| `word_relations` | syn \| ant \| semantic_related；BigInt FK + 複合索引 |
| `app/services/query_engine.py` | parse + registry dispatch |
| `app/services/position_match.py` | MatchSpec / PositionMatchEngine / 位置比對 |
| `app/services/equals_query_handler.py` | 等號 framed 查詢（獨立於 engine） |
| `app/services/essay_sort.py` | 統一搜尋結果排序（純漢字 → essay → curated → pron_rank） |
| `app/services/word_lookup_executor.py` | 純數字／粵拼片段／字面 lookup |
| `app/lexicon/essay_index.py` | Essay 語料 → 記憶體詞頻 dict（不寫 DB） |
| `app/services/lexicon_port.py` | 詞庫埠（收錄門檻 + 讀音） |
| `app/db/*` | connection · bootstrap · dialect；`database.py` facade |
| ingest | `scripts/ingest/import_data.py` · `python -m ingest` · `scripts/legacy/generate_relationships.py` |

---

## 時間線（壓縮）

### 初期 — 基礎搜尋 + 效能

- 等號韻 `香港=`、wildcard、hybrid、char 去重 + tier 排序
- `length` 欄 + 索引 + 背景 backfill；word_cache preload
- 離線：`start.sh`、file:// 提示

### 2026-06 — Syn/Ant ingest 重構

- **動機**：runtime 不裝 ML；ingest 預算 `word_relations`
- `requirements-dev.txt` 分離 sentence-transformers
- `handle_syn_ant_search`：SQL 主路 + static fallback（cilin + guotong）
- **Guotong 修復**：簡→繁 + pair **雙向**展開（「熱」↔「冷」）；`convert_guodict.py`
- **Cilin**：OpenCC s2t → `data/cilin/new_cilin.txt`

### 2026-06-12 — QueryEngine（C1）+ PositionMatchEngine（Phase 2）

**C1 — 查詢分派**（`query_engine.py` + `word_query_parser.py`）

- `search_words` → `QueryEngine.execute`；19 golden tests 鎖 **parse 優先序**
- 順序：relation → `23就=` alias → framed equals → code_tail → @ → rhyme → hybrid → mask → fallback

**Phase 2 — 位置匹配內聚**

| Phase | 內容 |
|-------|------|
| 2.1 | helpers 搬至 `position_match.py`；5× `handle_*` 薄層 + `engine.match` |
| 2.2 | registry 取代 isinstance 梯子 |
| 2.3 | `CodeTailQuery` / `LiteralRefQuery` / `RhymeAnchorQuery.to_match_spec()` |
| 2.4–2.6 | `run_position_query`、CandidateSource seam、`MaskQuery.to_match_spec` |
| 2.7 | `EqualsQueryHandler` 獨立 |

**門0 bug**（混合 literal+digit）

- 根因：mask 內 digit 未進 `required_codes` → 回傳所有 `門?`
- 修：`SlotConstraint(code_digit)` + `filter_words_by_code_and_mask` overlay mask digit
- 結果：第二碼須 =0（`門人`/`門前`/`門匙`…）

**其他架構**

- `syn_ant_service.fetch_relations` + `ThesaurusPort`；刪 `syn_ant_thesaurus_adapter`
- `relation_graph` / repo 分層
- `app/` 使用 `app.utils.*` / `app.thesaurus.static_index`；根目錄 `utils.py` 已刪
- `database.py` → `app/db/{connection,bootstrap,dialect}`

### 2026-06-12 — P0 等號 + 詞庫 P1–P4

- **P0**：`start_pos = len(left_code) - target_length`（`23=你4` 錨 pos 1）；語意見 `CONTEXT.md` § 碼夾等號查詢
- **P1–P4**：詞庫埠 · rime 單字 ensure · essay 詞頻 · curated + pron_rank 排序 ✅

### 2026-06-12 — PostgreSQL 凍結

- 交付 = **離線 SQLite**；PG scaffold **Freeze**（code 留、不投資）
- Schema 新變更 **僅 SQLite**（bootstrap）；Alembic 不再更新
- `psycopg2`/`alembic` → `requirements-postgres.txt`；PG URL 啟動警告
- PG issue：best-effort patch，無 CI、無承諾

---

## Bug 精選

| 症狀 | 修 |
|------|-----|
| 結果重複／不穩 | char 去重 + listener 清理 |
| 同字多 code 污染 | code-aware tier |
| syn 無反義 | guotong 雙向 pair |
| length NULL → 0 結果 | `_length_filter` + backfill |
| reload 崩 | ensure_* + daemon thread |
| framed `2=我3` literal | equals filter 強制 anchor 字面值 |
| `門0` 第二碼不限 | mask digit → code_digit slot |

---

## 現況（2026-06-13）

- Syn/ant：DB relations + static thesaurus；runtime 無 torch
- 詞庫：詞庫埠 + rime 單字 + essay 記憶體詞頻 + curated；詳見 `CONTEXT.md`
- 排序：扁平結果統一 `essay_sort`；tier 純漢字 → essay → curated → pron_rank；貼近 0243 常用度、非逐詞快照
- Essay：`data/essay/essay-cantonese.txt` 隨 repo（[rime-cantonese](https://github.com/rime/rime-cantonese)）；**不** ingest 詞頻表
- DB：SQLite 產品路徑；PG 凍結
- 測試：117 unittest；`test_search_sort` 覆蓋排序 tier + 四條整合 tracer
- 純數字：essay 排序 + `X-Search-Total` + 前端「已載入 N / total」

**限制**：超大結果集（如 `33`）仍 Python 排序後分頁；full relations 需 ingest

**待辦（非阻塞）**：guotong 註冊 `sources.yaml`；高頻 pair 預算 relations

---

## 參考 commit / 標記

- Phase 2.3 + 門0：`527ba31`
- 詳細 enforcement timing dump → git history / `scripts/enforce_bench.py` 輸出

### 2026-06-12 — P-C2：WordLookupExecutor + search_words alias（候選 2 partial ✅）

- 新 `word_lookup_executor.py`：`pure_digit` / `pure_canto` / `jyut_fragment` / `lookup`
- `QueryEngine` registry 直調 lookup + relation executors；刪 C1 wrapper
- `search_words` → `query_engine` alias（`execute_search`）；`word_search_service` 只留 `!!` handler
- 測試／bench import 改 `query_engine.search_words`

### 2026-06-13 — C3：`!!` 反義複合 → MatchSpec（CompoundAntExecutor + CandidateSource） ✅

- 新 `compound_ant_executor.py`：`CompoundAntExecutor.compound_ant_page`
- 新 `CompoundAntCandidateSource`（position_match.py）：由 `build_char_antonym_pairs` 展開 2-char compounds，char IN + code 過濾（行為貼近 legacy 候選取得）
- `CompoundAntQuery.to_match_spec()`：width=2、code_prefix、rhyme_char → `final_anchor` slot (pos=1)
- `QueryEngine` registry 直調 executor（移除最後一個 `to_handler_dict()` roundtrip 與 lazy word_search_service import）
- **刪除** 整個 `app/services/word_search_service.py`（69 行，硬性 AC）
- 對照 architecture review candidate 2「CompoundAntExecutor → MatchSpec」與 P-C executor 模式
- 決策重點（grill 後）：
  - Executor 擁有 ant pair 特殊候選邏輯；spec 統一由 parsed 產生（與 CodeTail/RhymeAnchor 一致）
  - CandidateSource 隔離「語意候選集」；engine 負責 rhyme final_anchor 等位置約束
  - SQL shape 維持 char IN + code（C3 不做大改；後續 bench 再優化）
  - rhyme_char 永遠對應結果詞最後一格 final（pos=1 for width=2）
- 測試：`tests/test_word_detail` 內 4 個 !! golden case（`!!`、`33!!`、`!!你`、`33!!你`）全綠；`ParseQueryGoldenTests` 通過；discover 維持 OK
- Bench：`enforce_bench.py` 跑畢（BENCH_DONE），關鍵位置型 case 無明顯退化
- 符合 handoff-c3-grill-20260612.md 所有 locked 決策與建議實作順序

### 2026-06-12 — P-C1：RelationSyntaxExecutor（候選 2 partial ✅）

- 新 `relation_syntax_executor.py`：`syn_mode_page` + `relation_lookup_page`（typed `RelationLookupQuery`）
- `QueryEngine`：`mode=syn` 短路 + registry 直調 executor；kill `to_handler_dict()` on relation path
- `words_for_relation_chars` 搬入 executor；`handle_*` 留 1 行 wrapper（C2 刪）
- 測試：108 unittest OK

### 2026-06-12 — P-B：RelationRanker（候選 3 ✅）

- 新 `relation_ranker.py`：`RelationRanker(db, thesaurus).rank()` → `RankedPools`
- `RankedPools.page()` / `.chars(kind, expand=…)`；`search_syn_ant` / `search_relation_chars` 薄 adapter
- 移除 `search_relation_chars` → `search_syn_ant(limit=10**9)` 反模式
- ant expand：`chars("ant", expand=True)` only；`mode=syn` page 路徑不 expand
- 測試：105 unittest OK

### 2026-06-12 — P-A：位置型 pipeline 收斂（候選 1 ✅）

- 刪 `mask_search.py`；`QueryEngine` registry 直調 `run_position_query` + `CandidateSource`
- `HybridCodeQuery.to_match_spec()`；dispatch helpers `_dispatch_*` 在 `query_engine.py`
- `PositionMatchEngine.match` → `filter_candidates_by_match_spec`（原生吃 `MatchSpec.slots`）
- 測試：105 unittest OK；+`HybridCodeQuery` / `filter_candidates_by_match_spec` 門0 case

**最後更新**：2026-06-13（刪除根目錄 utils.py facade）

### 2026-06-13 — 刪除根目錄 utils.py

- ingest / scripts / tests 改 import `app.utils.*` · `app.thesaurus.static_index`
- 刪 `utils.py`；portable build 不再 copy
- 108 unittest OK

### 2026-06-13 — 根目錄整理（grill B + D）

- 刪死碼：`jyutping_table.py`、`add_jyutping_to_0243.py`、`convert_guodict.py`
- 搬 `scripts/fetch/`、`scripts/db/`、`scripts/ingest/`、`scripts/legacy/`
- `ingest_syn_ant.py` → `ingest/cli.py`；入口 `python -m ingest`
- 根目錄保留：產品入口 + `WORKLOG.md` + `skills-lock.json`
- README 路徑全更新；108 unittest OK

### 2026-06-13 — 搜尋排序統一 + `!!` curated + CONTEXT 整理

**Grill 決策（排序／essay）**

- 扁平詞條清單共用排序信號；tier：**純漢字 → essay → curated → pron_rank**
- Essay 詞頻：記憶體 dict，**不** ingest DB（Q7-A）
- 不維護 0243 逐詞快照；embedding **不**取代 essay 詞頻
- Essay 語料納入 repo（來源 [rime-cantonese](https://github.com/rime/rime-cantonese)）

**實作**

- 新／強化 `app/services/essay_sort.py`：`default_word_sort_key` + `sort_words`
- 統一排序：`pure_digit`、`equals_query_handler`、`jyut_fragment`、無 `q` code 篩選（原 `Word.char` 序）
- 純數字：`X-Search-Total` header；前端 `已載入 N / total` + 載入更多
- `!!`：僅 `compound_antonyms.txt` ∩ DB（刪 ant pair 展開污染）
- 新 `tests/test_search_sort.py`（tier unit + `33`／`門0`／`香港=`／`mun4` 整合）
- **`CONTEXT.md` 重寫**：導覽表、碼夾等號查詢獨立詞、移除 P0–P4 路線圖與實作名

**驗證**：117 unittest OK

---

**最後更新**：2026-06-13（README／WORKLOG 與 CONTEXT 同步）
