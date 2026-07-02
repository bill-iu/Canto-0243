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
| 已知阻斷 | relation derived_ant 未 port |

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

下一工作項：

1. **P0**：schema（`char`）、基本 lookup、離線就緒真查詢驗證
2. **P1**：golden parity 逐條拉高
3. **P2**：wasm-sqlite + OPFS（D-G4）
4. **（可選）** 時間盒 E POC：僅在 D parity 連續受阻時啟動

---

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
