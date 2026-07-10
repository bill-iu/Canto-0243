# 平仄模式錨語法覆蓋與介面收斂：實作計劃

> **供執行代理使用：** 本文件是此功能唯一的實作計劃與依賴任務清單；實作時逐項更新核取狀態。

**目標：** 在平仄模式讓 `P`／`Z` 可出現在所有既有的非粵拼錨語法數字碼位，並在搜尋欄下方提供緊湊的三段子模式切換。

**架構：** 平仄輸入先把 `P`／`Z` 暫換成既有語法可理解的 `?`，以原有 parser 決定語法族與錨語意，再用原始字串的 `P`／`Z` 覆寫對應 MatchSpec slot 為 `tone_class`。數字與 `?` 維持既有語法；P/Z 永遠用 394052 平仄分類。前後端採同一轉換與 MatchSpec 規則。

**技術：** Python 後端服務、TypeScript 離線搜尋引擎、React、既有 Position Match、Open Design CSS tokens。

## 全域限制

- 只在 `mode=pz` 解析大寫 `P`／`Z`；粵拼 `p`／`z` 及粵拼錨保持既有行為。
- 粵拼錨在平仄模式維持明確拒絕提示。
- 不改動純漢字、近反義、關係查詢等沒有數字碼位的語法。
- UI 只新增 header 下拉選單的平仄入口，以及搜尋欄下方的三個小 segmented pills；沿用 Open Design tokens。
- 全部程式與文件改動只在 `dev` 分支提交並推送。

## 檔案邊界

- `app/services/query_parse.py`、`app/services/query_types.py`：後端以既有語法解析平仄錨並保留 P/Z slot 資訊。
- `app/services/query_match_spec_registry.py`：以既有 base MatchSpec 為基礎覆寫 P/Z tone slots。
- `client/src/db/query-types.ts`、`client/src/db/query/parse.ts`、`client/src/db/position-match/match-spec-registry.ts`：離線引擎的等價實作。
- `client/src/mode-menu.tsx`、`client/src/App.tsx`、現有 PWA 樣式檔：將子模式控制移出下拉選單並置於搜尋欄下方。
- `tests/test_ping_ze_serial.py`、既有 TS parser／registry self-check：涵蓋各非粵拼錨族與 UI state。

## 依賴順序任務

### WP-01：定義可包裝的平仄錨查詢

- [x] 後端及 TypeScript `PingZeSerialQuery` 加入已解析的 base query 與 P/Z slot 對應；保留目前無錨的 serial 查詢。
  - 依賴：無。
  - 邊界：`app/services/query_types.py`、`client/src/db/query-types.ts`。
  - 完成條件：一個平仄查詢可攜帶原始字串、子模式、既有語法解析結果及 P/Z slot 位置。
  - 驗證：型別檢查與 parser self-check 成功。

### WP-02：以既有文法解析 P/Z 錨

- [x] 將 P/Z 暫換成中性的數字碼位後送入既有 parser，排除粵拼錨；成功時包裝 base query，失敗時維持既有 fallback 與提示。
  - 依賴：WP-01。
  - 邊界：`app/services/query_parse.py`、`client/src/db/query/parse.ts`。
  - 完成條件：韻母錨、聲母錨、literal、plus、wildcard、partial／serial phoneme 及其數字位可含 P/Z；純數字 PZ serial 仍可查。
  - 驗證：新增具體 parser 測例；粵拼錨仍得到「平仄模式不支援粵拼錨」提示。

### WP-03：以 MatchSpec 疊加 P/Z 平仄限制

- [x] 先建立 base query 的既有 MatchSpec，再把原始 P/Z 對應的碼位改成 `tone_class`，並保留所有既有 anchor slots 及 m1/m2/m3 的數字規則。
  - 依賴：WP-01、WP-02。
  - 邊界：`app/services/query_match_spec_registry.py`、`client/src/db/position-match/match-spec-registry.ts`。
  - 完成條件：`P=0/3`、`Z=其他` 固定 394052；同一查詢的數字 slot 使用所選子模式。
  - 驗證：Python 與 TypeScript MatchSpec 測試比較 slot kind、位置與 code mode。

### WP-04：回歸測試所有適用錨語法族

- [x] 針對韻母、聲母、literal、plus、partial rhyme、serial phoneme 與碼位中間韻錨加入 P/Z parser／MatchSpec 測例；沒有數字碼位的語法維持原路徑。
  - 依賴：WP-02、WP-03。
  - 邊界：`tests/test_ping_ze_serial.py`、`client/scripts/parser-self-check.ts`、`client/scripts/match-spec-registry-self-check.ts`。
  - 完成條件：每族至少一個 P/Z 範例可解析並保有既有語意；沒有數字碼位的語法不被攔截。
  - 驗證：Python targeted unittest、TypeScript self-check、`npx tsc --noEmit`。

### WP-05：把子模式 pills 移至搜尋欄下方

- [x] 下拉選單只保留「平仄模式」入口；平仄模式激活時，在搜尋欄下方顯示 `0243`、`02493`、`394052` 三個小 segmented pills。
  - 依賴：無。
  - 邊界：`client/src/mode-menu.tsx`、`client/src/App.tsx`、現有 PWA 樣式檔。
  - 完成條件：pill 可隨時切換並保留 URL/tab state；非平仄模式完全不顯示；無額外 header 或殼層改動。
  - 驗證：既有 URL/tab state 測試、typecheck、production build；目視確認 tokens、間距與 focus state。

### WP-06：整合驗證、提交與進度記錄

- [x] 執行後端、前端、typecheck、build 與 diff 檢查；更新本文件結果後只 stage 本功能檔案並提交推送 `dev`。
  - 依賴：WP-04、WP-05。
  - 邊界：本文件與本計劃列出的程式／測試檔。
  - 完成條件：所有 target checks 成功；無關的既有 dirty files 不會被 stage。
  - 驗證：`python -m unittest tests.test_ping_ze_serial`、`npx tsx scripts/parser-self-check.ts`、`npx tsx scripts/match-spec-registry-self-check.ts`、`npx tsc --noEmit -p tsconfig.json`、`npm run build`、`git diff --check`。

## 驗收

- 在平仄模式，`PZ?`、`?PZ`、`PZ好=` 與既有非粵拼錨語法中的 P/Z code slots 都能搜尋。
- `P/Z` 從不吞掉一般模式的粵拼 p/z；平仄模式的粵拼錨有可理解的拒絕提示。
- 數字 slot 服從 selected submode，P/Z 始終服從 394052。
- 子模式 UI 是搜尋欄下方的微型 segmented pills，而非 dropdown 內的群組。

## 進度記錄

- 2026-07-10：建立本單一繁中工作計劃，取代後續拆分的 plan/tasks 文件。
- 2026-07-10：完成 non-Jyutping 錨語法的 P/Z 包裝、MatchSpec 疊加、緊湊子模式 pills，並通過所有列出的 target checks。
