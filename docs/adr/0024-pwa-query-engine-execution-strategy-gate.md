# ADR-0024: PWA 查詢引擎執行策略決策閘（方案 D vs 方案 E）

## Status

**Accepted（執行路徑 D）** — 2026-07-02 起依 **方案 D** 實作：TypeScript query-engine port → golden parity → 再評估 wasm-sqlite + OPFS。**方案 E（Pyodide）** POC 暫緩，保留 §5.1 門檻供日後覆核。

## Context

PWA（`client/`）須與 PC portable 在**同一 `lyrics.db`** 下呈現**等價查詢結果**（見 `specs/001-pwa-offline-coexist/`、`contracts/versioned-lexicon-package.md`）。

目前存在兩條候選執行路徑：

| 代號 | 查詢邏輯 | SQLite 存取 | 狀態 |
|------|----------|-------------|------|
| **D** | TypeScript port（`client/src/db/query-engine.ts`） | sql.js（現況）；目標 wasm-sqlite + OPFS | golden parity **18/18 + 15/15**（2026-07-02） |
| **E** | 瀏覽器內 Python（Pyodide）執行 portable 同源引擎 | sqlite3 / SQLAlchemy + OPFS | 未實作 |

ADR-0023 已選 React + Vite + PWA +「port 查詢引擎至 JS」，但 **parity 未達標** 且 **Pyodide 優化路線**（Lazy、Worker、OPFS、trim）是否足以改變決策，需以數據與 POC 驗證，而非架構討論直接定案。

**決策閘腳本**：`scripts/pwa_golden_parity.py`（對照 `tests/smoke/golden_queries.py` 共 **18** 條 journey）。

---

## 1. Python Query Engine 實際規模（2026-07-02 量測）

### 1.1 量測範圍

自 `query_dispatch.search_words` 可達之執行路徑，含 parse、grammar、position_match、lookup、relation syn/ant、ranking、jyutping codec、word cache 等（**不含** FastAPI、ingest、ML）。

| 指標 | 數值 |
|------|------|
| Python 模組檔數 | **58** |
| Python LOC（約） | **~8,700** |
| 含 `sqlalchemy` 字樣之檔案 | **21** |
| 使用 `Session` / ORM `.query()` 之檔案 | **23** |
| 最大單檔 | `position_match/filters.py`（~667 LOC） |

### 1.2 SQLAlchemy 耦合程度

| 層級 | 說明 | 代表模組 |
|------|------|----------|
| **入口耦合** | `SearchContext.db: Session`；所有 dispatch 假設 ORM | `query_dispatch.py` |
| **執行耦合** | 候選集、filter、relation 圖均以 `Word` / `WordRelation` ORM 操作 | `position_match/*`, `relation_syntax_executor.py`, `domain/relations/*` |
| **低耦合** | 純 parse / token / MatchSpec 建構，可不依賴 DB | `query_lexer.py`, `query_grammar/*`, `query_types.py`（部分） |

**結論**：引擎並非「`sqlite3` + `re` + `json`」等級；**syn 模式與 mask-family 執行**深度依賴 SQLAlchemy 與 `word_relations` 表。

### 1.3 可抽離程度（供 Pyodide trim 評估）

| 抽離策略 | 可行性 | 預估工作量 | 備註 |
|----------|--------|------------|------|
| **A. 整包 ORM 進 Pyodide**（micropip `sqlalchemy`） | 技術上常見 | POC 1–2 週 | WASM 體積與冷啟動是主要風險 |
| **B. 薄 API `search_offline(q, mode) -> list[dict]` + 保留 ORM** | 中 | 1 週包裝 + 與 D 並行維護介面 | 不解決 SQLAlchemy 體積 |
| **C. 重寫為 sqlite3 直查（去 ORM）** | 難 | **數週～數月** | 等於在 Python 內做第二套執行層；完成後 E 與 portable 仍要雙軌測試 |
| **D. 只抽 parse 進瀏覽器、執行仍 TS** | 易 | 已部分存在於 TS | 本質回到方案 D |

**可抽離結論**：語法解析約 **30–40%** LOC 可無 DB 單測；**執行與排名 ~60%** 與 ORM / SQLite 綁定。建議 E 的 POC **預設採策略 A**；若冷啟或體積不達標，**不得**假設策略 C 能短期救火。

---

## 2. Pyodide POC（方案 E 驗證程序）

### 2.1 POC 範圍（最小）

```
PWA Shell (React + Vite，可沿用 client/)
  → Web Worker
      → Pyodide（Lazy：第一次查詢才載入）
      → Python：query_dispatch.search_words（策略 A：含 SQLAlchemy）
      → lyrics.db via OPFS VFS（禁止整檔 read into RAM）
```

**不在 POC 範圍**：FastAPI 線上混合、完整 query_explain UI、非 golden 語法。

### 2.2 量測環境（硬性）

| 項目 | 要求 |
|------|------|
| 裝置 | **至少 2 台 iPhone**（不同晶片代：如 A 系列相鄰兩代；或 1 台 iPhone + 1 台 iPad 僅作補充，主指標仍須兩台 iPhone） |
| 安裝形態 | 主畫面 PWA（與驗收 spec 一致） |
| 網路 | Wi‑Fi 下完成離線就緒後，**飛航模式**量測 |
| 詞庫 | 與 release 相同之 `lyrics.db`（或 fixture + memory seed 僅用於開發；**Go 門檻以正式尺寸 db 為準**） |

### 2.3 量測項目與操作腳本

| # | 指標 | 操作 | 記錄 |
|---|------|------|------|
| M1 | **冷啟時間** | 殺掉 PWA 進程 → 主畫面重開 → 到 UI 可輸入 | 中位數 × 10 次 |
| M2 | **首次查詢時間** | 冷啟後第一次按 Search（含 Pyodide Lazy 載入） | 中位數 × 10 次 |
| M3 | **暖查詢時間** | 同 session 第 2、10 次查詢 | 中位數 |
| M4 | **記憶體峰值** | Safari Web Inspector → Memory / Performance | 首次查詢前後、查詢中峰值 |
| M5 | **背景恢復** | 查詢成功 → 切到 LINE 30s → 切回 → 再查同一 query | **50 次**試驗 |

### 2.4 POC 交付物

- `docs/pwa/pyodide-poc-results.md`（或 spec quickstart 附錄）：原始數據表
- Worker 原型程式碼（可 `client/poc/pyodide-worker/`）
- `golden_queries` 全 **18** 條在 POC 內之 **Python 端**結果（作為 E 側基線）

---

## 3. TypeScript Port 成本（方案 D 評估）

### 3.1 現況

| 項目 | 數值 |
|------|------|
| `query-engine.ts` LOC | **~1,134** |
| 相對 Python 執行層 LOC | **~13%** 骨架 |
| Golden parity | **18/18** journeys、**15/15** match_spec（`scripts/pwa_golden_parity.py --gate all`） |
| 已知阻斷 | 無（parity 閘門已達標） |
| 技術債 | `executeMaskFamily` 仍為 LIKE stub（見 §6）；長尾 jyutping parser 已補齊（2026-07-02） |

### 3.2 需重寫／補齊範圍

| 區塊 | 對應 Python | 預估 |
|------|-------------|------|
| P0 schema + 基本 lookup | `word_lookup_executor` | 數日 |
| Parser + registry 對齊 | `query_parse`, `query_grammar/*`, registries | **1–2 週** |
| Mask-family 執行 | `position_match/*` | **2–3 週** |
| Syn / relation | `relation_syntax_executor`, `domain/relations/*` | **1–2 週** |
| 排名 / 去重 | `ranking`, `word_serializer` | 數日 |
| OPFS + wasm-sqlite（Phase 2） | `init.ts` | **與 parity 分階段**；約 1 週 |

**粗估**：全量 parity 約 **4–8 人週**（視測試與邊角語法而定），之後每次 portable 查詢行為變更需同步 TS + 跑 parity。

### 3.3 Golden tests 能否 100% 通過？

| 測試集 | 現況 | D 目標 |
|--------|------|--------|
| `GOLDEN_QUERY_JOURNEYS`（18） | Python ✅；TS ❌ | **必須 18/18** |
| `MATCH_SPEC_REPRESENTATIVE_CASES` | 僅 Python registry smoke | 建議 parity 腳本 **第二階段** 納入 |
| `test_query_journey` CI | 已覆蓋 Python | TS 由 `pwa_golden_parity.py` 閘門 |

**結論**：D 之成功定義 = **`pwa_golden_parity.py` exit 0**（可擴充案例，但不得少於現行 18）。

### 3.4 維護成本（長期）

- 每次 `app/services/query_*` 或 `position_match` 變更 → 需評估 TS port + parity
- 優勢：無 Pyodide 體積／iOS VM 回收問題；與 ADR-0023、現有 `client/` 一致

---

## 4. 使用者需求（產品假設與待確認項）

### 4.1 已由 Spec 鎖定（視為約束，非待辯）

| 需求 | 來源 |
|------|------|
| 首次成功載入後可**完全離線**查詢 | `spec.md` US1、FR-003 |
| 與 portable **同版** `lyrics.db` | FR-007、Scenario C |
| **不**引入第二條資料建置 pipeline | plan.md |
| 免 Apple Developer、靜態 Pages 部署 | plan.md constraints |
| 大檔下載可提示 Wi‑Fi | 已實作於 `App.tsx` |

### 4.2 待維護者／產品確認（寫入 POC 前應有明確答案）

| 問題 | 建議預設 | 若答案為「否」之影響 |
|------|----------|---------------------|
| 目標使用者是否**多數**需要飛航級離線？ | **是**（PWA 渠道存在理由） | 可降級為線上 SPA，整個 feature 動機動搖 |
| 是否接受 **~90MB 級**離線資料包（+ 引擎體積）？ | **是**（已有 portable 先例） | 需縮減詞庫或分卷（超出本 ADR） |
| 是否接受**首次查詢**等待數秒？ | **有条件**：見 §5 門檻 | 若不接受 → E 禁用 Lazy；D 優先 |
| 是否接受切 App 後**偶發**再載入引擎？ | **有条件**：恢復成功率见 §5 | 若不接受 → E 不適合 |

**記錄方式**：確認結果填入 `specs/001-pwa-offline-coexist/research.md` 或本 ADR 之 **Status → Accepted** 修訂，避免口頭假設。

---

## 5. 成功門檻（Go / No-Go）

### 5.1 方案 E（Pyodide + OPFS）— **全部**達標才 Go

| ID | 門檻 | 通過條件 |
|----|------|----------|
| **E-G1** | iPhone 首次查詢延遲 | 兩台裝置 M2 **中位數 < 5s**（Wi‑Fi 就緒後、飛航模式查詢） |
| **E-G2** | 背景恢復 | M5 **成功率 ≥ 95%**（50 次試驗；失敗 = 查詢無結果或 >10s 或 crash） |
| **E-G3** | Golden parity | Python POC 路徑對 `GOLDEN_QUERY_JOURNEYS` **18/18** 與 portable 一致 |
| **E-G4** | 離線資料包總量 | Pyodide runtime + 依賴 + `lyrics.db` 首次安裝 **≤ 120MB**（可調；預設比現行 portable zip ~92MB 多不超過 ~30MB 引擎稅） |
| **E-G5** | 記憶體 | M4 峰值 **< 512MB** 且不因單次查詢觸發 tab crash（兩台均須滿足） |
| **E-G6** | 暖查詢 | M3 **中位數 < 1s**（證明 Lazy 僅第一次付全價） |

**任一未達標 → No-Go E，採用方案 D。**

### 5.2 方案 D（TS port + wasm SQLite + OPFS）— 預設路徑之完成定義

| ID | 門檻 | 通過條件 |
|----|------|----------|
| **D-G1** | Golden parity | `python scripts/pwa_golden_parity.py` → **18/18** |
| **D-G2** | 離線就緒 | 契約 `offline-readiness.md`：含**真查詢**驗證（非僅 `COUNT(*)`） |
| **D-G3** | Quickstart | Scenario A/B/C 實機通過（spec tasks T017–T018） |
| **D-G4** | OPFS（Phase 2） | 不阻擋 D-G1–G3；全綠後再做；目標降低 RAM、非 parity 前提 |

### 5.3 決策規則（摘要）

```text
IF  E-G1..E-G6 全通過 AND POC 審閱通過
THEN 選 E；TS port 降級為薄 UI 層（或移除 query-engine 執行職責）
ELSE 選 D；Pyodide POC 歸檔；繼續 TS parity + 條件成熟時 OPFS
```

**本 ADR 在 E POC 完成前不修改 ADR-0023 之技術棧敘述**；POC No-Go 時維持「port 至 JS」路線。

---

## Decision（暫緩）

**已選定方案 D 為執行路徑**（TS port + sql.js → 目標 wasm-sqlite/wa-sqlite + OPFS）。方案 E 不刪除，但不在目前 sprint 執行 POC。

下一工作項（分階段，見 §6–§7）：

1. ~~**P0**：schema（`char`）、基本 lookup、離線就緒真查詢驗證~~ ✅
2. ~~**P1**：golden parity 逐條拉高~~ ✅（18/18 + 15/15）
3. **P1.5**：缺字型查詢執行收斂至 `MatchSpec` 管線（§6 MF-0…MF-6）
4. **P2**：wasm-sqlite + OPFS（D-G4，§7 DB-0…DB-5）
5. **（可選）** 時間盒 E POC：僅在 D parity 連續受阻時啟動

---

## 6. 缺字型查詢執行（`executeMaskFamily`）分階段實作

### 6.0 Grill 結論（術語與邊界）

| 常見誤解 | 實際 |
|----------|------|
| 「把 `executeMaskFamily` 寫完整」 | TS 內該函式目前是 **SQL `LIKE` stub**，不是 Python 的缺字型執行 |
| Python 對應物 | `query_dispatch._mask_family_search_result` → `normalize_to_match_spec` → `execute_match_spec` |
| 領域用語（CONTEXT） | **缺字型查詢執行**只收 **比對規格**（`MatchSpec`），不在執行層 `isinstance` 分派（ADR-0002） |
| Parity 現況 | Golden **已綠**；多數 `QueryKind` 已有**獨立 executor**；stub 僅承接 **4 種**未實作 kind |

**仍走 stub 的 QueryKind**（`client/src/db/query-engine.ts` `dispatch` fallback）：

- `WILDCARD_CODE_ANCHOR`（例 `?30人`）
- `TRIPLE_RHYME_ANCHOR`（例 `?+人=?`）
- `CODE_REF_MIDDLE_RHYME`（例 `?3人=?`）
- `HYBRID_TAIL_EQUALS_ALIAS`（例 `23就=` → 改寫為 hybrid_q 再 LIKE）

**建議**：不要擴寫 stub；按 ADR-0002 建 **MatchSpec 管線**，逐 kind 遷移後刪除 stub。

### 6.1 目標架構（對齊 Python）

```text
ParsedQuery
  → normalizeToMatchSpec(parsed)     # port query_match_spec_registry.py
  → executeMatchSpec(spec, ctx)      # port position_match/engine.py
       ├─ resolveMaskFamilySource    # sources.py
       ├─ getCandidatesForLength     # sql.js 直查 width
       └─ applyMatchSpec             # filters.py
```

TS 目錄建議（ponytail：先一檔，長大再拆）：

```text
client/src/db/position-match/
  spec.ts          # SlotConstraint, MatchSpec, EqualsSpan
  match-spec.ts    # buildMatchSpecForParsed（registry）
  sources.ts       # 候選來源
  filters.ts       # slot 過濾
  engine.ts        # executeMatchSpec 入口
```

### 6.2 分階段步驟（每步可獨立 merge + self-check）

| 步驟 | ID | 交付物 | 通過條件 | 依賴 |
|------|-----|--------|----------|------|
| 0 | **MF-0** | 將 stub 重新命名為 `executeMaskFamilyStub`；`dispatch` 註解標明過渡 | `pwa_golden_parity.py --gate all` 仍綠 | — |
| 1 | **MF-1** | `position-match/spec.ts`：完整 `MatchSpec` / `SlotConstraint`（自 `query-engine.ts` 抽出） | TypeScript 編譯；既有 equals self-check 仍過 | MF-0 |
| 2 | **MF-2** | `match-spec.ts`：port `build_match_spec_for_parsed` | Node self-check 對 `MATCH_SPEC_REPRESENTATIVE_CASES` 欄位與 Python 一致 | MF-1 |
| 3 | **MF-3** | `sources.ts`：`getCandidatesForLength`（`length` / `char` 長度 + 可選 `code` 前綴） | 單元 self-check：`width=2` 候選數 > 0（fixture db） | MF-1 |
| 4 | **MF-4** | **垂直切片**：上述 4 種 stub kind 各一條 `executeMatchSpec` 路徑 | 4 條代表查詢有結果且與 Python fixture 一致 | MF-2, MF-3 |
| 5 | **MF-5** | `filters.ts` 分批 port（見下表） | 每批合併後 parity 不 regress | MF-4 |
| 6 | **MF-6** | `dispatch` MASK_FAMILY 預設走 `executeMatchSpec`；逐 kind 移除重複 executor | stub 刪除；parity 全綠 | MF-5 |

**MF-5 過濾器分批**（對應 `position_match/filters.py` ~667 LOC）：

| 批次 | 約束 kind | 覆蓋 QueryKind 示例 |
|------|-----------|---------------------|
| F1 | `code_digit`, `literal_char`, `wildcard` | `MASK`, `LITERAL_REF`, `WILDCARD_CODE_ANCHOR` |
| F2 | `final_anchor`, `initial_anchor` | `RHYME_ANCHOR`, `PARTIAL_*_MASK` |
| F3 | `rhyme_letters`, `syllable_letters`, `initial_letters` | `JYUTPING_ANCHOR`, `TRIPLE_RHYME_ANCHOR` |
| F4 | `equals_span` + `mask_adapter` | `EQUALS`, `PREFIX_WILDCARD_EQUALS`, `HYBRID_TAIL_EQUALS_ALIAS` |
| F5 | `compound_kind` source 注入 | 已由 `compound.ts` 覆蓋；MF-6 時改為 source registry 統一 |

**複雜度控制原則**：

- 每步 **只加一層**；MF-4 先讓 4 種 stub kind 走通，不等待 F1–F5 全完
- 已有獨立 executor 的 kind **暫不動**，直到 MF-6 證明 `executeMatchSpec` 等價
- 每步附 **最小 runnable check**（`client/scripts/*-self-check.ts` 或 parity 子集）

---

## 7. wasm-sqlite + OPFS（D-G4）分階段實作

### 7.0 Grill 結論

| 問題 | 建議答案 |
|------|----------|
| OPFS 是否阻擋 parity？ | **否**（ADR D-G4）；現行 sql.js 全檔 `fetch` + RAM 已滿足 D-G1–G3 |
| 何時切換？ | **parity 全綠且 MF-4 完成後**再動儲存層，避免同時 debug 執行與 I/O |
| iOS 風險 | OPFS 持久化 ≠ 免重新下載；SW cache 與 OPFS 職責需分開（契約 `offline-readiness.md`） |

### 7.1 現況（`client/src/db/init.ts`）

- sql.js + **整檔 `arrayBuffer` 進 RAM**
- 註解已說明：避免 iOS range request 碎片化
- 目標：wa-sqlite + OPFS VFS → 查詢時 mmap 式讀取、降低峰值 RAM

### 7.2 分階段步驟

| 步驟 | ID | 交付物 | 通過條件 | 依賴 |
|------|-----|--------|----------|------|
| 0 | **DB-0** | Spike：`client/poc/wa-sqlite-opfs/` 最小 open + `SELECT COUNT(*)` | 本機 Chrome + 一台 iOS 手動 OK | — |
| 1 | **DB-1** | `DatabaseBackend` 介面；sql.js 實作適配現有 `prepare/step` | 現有 parity **零改動**通過 | DB-0 |
| 2 | **DB-2** | OPFS import：版本化 `lyrics.{semver}.db` 寫入 OPFS（一次性） | 二次開啟不重新 `fetch` 全檔 | DB-1 |
| 3 | **DB-3** | `init.ts` feature flag（`VITE_DB_BACKEND=opfs`）；預設仍 sql.js | CI / parity 預設路徑不變 | DB-2 |
| 4 | **DB-4** | SW 策略：HTML/JS cache 不變；db 可由 OPFS 或 SW 雙路復原 | `offline-readiness.md` 契約更新 + 手動 Scenario B | DB-3 |
| 5 | **DB-5** | 實機量測：冷啟 RAM 峰值、飛航查詢 | 記錄於 `research.md`；較 sql.js 峰值下降為成功 | DB-4 |

**不做的（YAGNI）**：

- 不在 Phase 2 引入 Worker 內 SQL（除非 DB-0 證明主線程 jank）
- 不為 OPFS 改 query-engine 語意
- 不刪 sql.js 路徑，直至 DB-5 連續兩版 release 穩定


## Consequences

### 若最終為 D

- 維持靜態 bundle 較小、iOS PWA 風險較可控
- 承擔雙實作維護；以 `pwa_golden_parity.py` 為 CI 閘門
- OPFS 作為體驗優化，不影響等價性判定

### 若最終為 E

- 查詢邏輯單一真源（Python），parity 由同源保證
- 接受較大下載與 iOS 背景回收工程；需 Worker 恢復策略與使用者可見狀態
- `client/src/db/query-engine.ts` 執行角色下線或僅留 parse 對照

### 無論哪條路

- **詞庫資料包**維持單一 release pipeline（不變）
- **不得**引入 PWA 依賴常駐 FastAPI 作為預設路徑（與 spec 衝突之混合架構不在本 ADR 範圍）

---

## Related

- [ADR-0023: Introduce Static Client Bundle and PWA Delivery Channel](./0023-introduce-static-client-bundle-and-pwa-delivery-channel.md)
- [specs/001-pwa-offline-coexist/spec.md](../../specs/001-pwa-offline-coexist/spec.md)
- [contracts/offline-readiness.md](../../specs/001-pwa-offline-coexist/contracts/offline-readiness.md)
- `scripts/pwa_golden_parity.py`
- `tests/smoke/golden_queries.py`
