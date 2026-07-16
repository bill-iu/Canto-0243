# frontend 與 client 殼層重複與遷移風險

**日期**：2026-07-16  
**對象專案**：bill-iu/Canto-0243（離線粵語填詞查韻；Portable 免安裝 + PWA 雙渠道）  
**票**：[#85](https://github.com/bill-iu/Canto-0243/issues/85)  
**結論摘要**：兩邊已共享大量 **殼層狀態／文案／CSS／結果合併**（`frontend/*.mjs` 被 `client/src` 直接 import），但 **UI 編排與查詢執行路徑仍雙實作**。Portable 唯一依賴本機 Python 後端（`/words/search/`、`/ready`、關係補錄／詞庫勘誤 view、chrome-tabs）；PWA 唯一依賴瀏覽器查詢引擎、OPFS／SW、懶載詞庫與安裝提示。若以 `client/` 為唯一 UI，最大風險是 **Portable 發佈／啟動鏈仍硬綁 `frontend/`**，以及 **維護者工具 view 與後端 API 殼** 尚無 PWA 對等物。

**非範圍**：不改產品碼；不提出退役實作步驟（供後續 grilling）；不處理 #84／#86／#87／#83。

---

## 1. Summary（摘要）

| 面向 | 現狀 |
|------|------|
| 交付渠道 | **Portable**：Python FastAPI + 靜態 `frontend/`（ADR-0044）。**PWA**：`client/` Vite 束 + SW／Pages（ADR-0045）。 |
| 殼層重疊 | 分頁狀態、URL／history、committed search、i18n 文案、結果統計／合併、就緒閘視覺 CSS、lang／theme 常數 — 多已落在 `frontend/`，PWA 再包一層 React。 |
| 唯一依賴（Portable） | 本機後端搜尋與就緒輪詢、關係補錄／勘誤 UI、chrome-tabs + Draggabilly、整包 `frontend/` 進 zip／tar、`local_launch` 開 `/frontend/index.html`。 |
| 唯一依賴（PWA） | TS 查詢引擎、sql.js／OPFS、`lexicon-manifest`、SW 預取、debounce 即時搜尋、PWA install banner、過濾 relation／corrections view。 |
| 退役含義 | 「以 `client/` 為唯一 UI」≠ 刪 `frontend/` 即可：大量 **共享邏輯與 CSS SSOT** 仍掛在 `frontend/`；Portable 若續存，要嘛把殼搬進 `client` 並改伺服／打包，要嘛把共享模組抽到中立目錄。 |

---

## 2. Duty overlap（殼層職責重複點）

「重複」= 兩邊各自有編排／掛載，但語意或程式來源重疊（含 **共享模組** 與 **平行實作**）。

| 職責 | Portable（`frontend/`） | PWA（`client/src`） | 重疊性質 | 主要來源 |
|------|-------------------------|---------------------|----------|----------|
| App 入口／殼編排 | `main.mjs` + `index.html` DOM | `App.tsx` + `main.tsx` | **平行 UI 編排**；行為對齊意圖 | `frontend/main.mjs`；`client/src/App.tsx`；`client/src/main.tsx` |
| 就緒閘／landing | `gate.mjs` 輪詢 `GET /ready`；HTML `#preloadOverlay` | `ready-gate.tsx` + `pwa-shell-boot.ts`；offline／下載進度 | **視覺／儀式重疊**；解鎖條件不同（後端探針 vs 開庫＋離線探針） | `frontend/gate.mjs`；`client/src/ready-gate.tsx`；ADR-0044 §3；ADR-0045 §3；CONTEXT §就緒閘 |
| 分頁狀態／URL | `query-tabs-state.mjs`、`tabs-core.mjs`、`tabs-ui.mjs` | `useQueryTabs.ts` import 同一 state／navigation／committed-search | **共享狀態層** + PWA 過濾 view | `frontend/query-tabs-state.mjs`；`frontend/search-navigation.mjs`；`frontend/committed-search.mjs`；`client/src/query-tabs/useQueryTabs.ts`（`PWA_VIEWS`） |
| 分頁列 UI | Chrome-tabs（`chrome-tabs-layout.mjs` + CSS） | Pill 列 `QueryTabsBar` | **同職責不同 UI** | `frontend/chrome-tabs-layout.mjs`；`frontend/index.html`（chrome-tabs.css）；`client/src/query-tabs/query-tabs-bar.tsx`；specs/001-pwa-offline-coexist/tasks.md |
| 模式選單／文案 | `search-workbench.mjs` + `mode-i18n.mjs` | `mode-menu.tsx` + `mode-meta.ts` → `mode-i18n.mjs` | **文案共享**；選單 UI 平行 | `frontend/mode-i18n.mjs`；`client/src/mode-meta.ts`；`client/src/mode-menu.tsx` |
| 搜尋送出／轉接 | `search-workbench.mjs` → `fetch /words/search/`；`mode-policy.mjs`（regex） | `useSearch`／`planCommitSearch` → 瀏覽器引擎；`mode-policy.ts`（regex＋full-parse） | **職責同、引擎異**；policy 雙份 | `frontend/search-workbench.mjs`；`frontend/mode-policy.mjs`；`client/src/db/query/mode-policy.ts`；ADR-0045 §1 |
| Query explain | `query-explain.mjs`（桌面） | `db/query-explain.ts` + `useQueryExplain` | **雙引擎解釋**；parity 契約 | CONTEXT §即時說明；`contracts/query-explain-ir.schema.json`；`client/src/hooks/useQueryExplain.tsx` |
| 結果列表／無限捲 | DOM 渲染於 workbench；`infinite-results.mjs` | React lists；import `isSentinelIntersecting` | **合併／統計共享**；渲染平行 | `frontend/entry-detail-core.mjs`；`frontend/result-stats.mjs`；`frontend/infinite-results.mjs`；`client/src/App.tsx` imports |
| 詞條詳情 | `entry-detail-portable.mjs` + core／i18n | `EntryDetailPanel` + 同 core／i18n | **核心合併邏輯共享**；面板平行 | `frontend/entry-detail-core.mjs`；`frontend/entry-detail-i18n.mjs`；`client/src/entry-detail/*` |
| 教學／關於 | `guide-i18n.mjs`／`about-i18n.mjs` + HTML | `guide-view.tsx`／`about-view.tsx` import 同 i18n | **文案 SSOT 在 frontend** | `frontend/guide-i18n.mjs`；CONTEXT §搜尋教學驗收 |
| Lang／theme | `app-context.mjs` | `App.tsx` import `getLang`／`setTheme` 等 | **共享偏好常數** | `frontend/app-context.mjs`；`client/src/App.tsx` |
| 視覺殼 CSS | `open-design.css`、`ready-gate.css`、`shell.css`、`workbench.css`、`entry-detail.css` | `main.tsx` 由 `../../frontend/*.css` import；另加 `root.css`／`pwa-app.css` | **CSS SSOT 在 frontend**（seam 閘） | `client/src/main.tsx`；`scripts/check_seams.py`（`test_shared_css_single_source_in_frontend`、`test_pwa_main_imports_frontend_css`） |
| Mode detect | `query-mode-detect.mjs`（**由 client codegen**） | `db/query/mode-detect.ts` 為源 | **單向生成**，非手抄雙份 | `scripts/codegen_query_mode_detect.py`；`frontend/query-mode-detect.mjs` 檔頭 |

---

## 3. Portable-only behaviors（只存在於 Portable／`frontend` 殼側）

下列行為在現行 `client/` 產品 UI **沒有對等暴露**（或整條啟動鏈只服務 Portable）：

| 行為 | 說明 | 來源 |
|------|------|------|
| 靜態殼由 FastAPI 掛載 | `main.py` mount `/frontend`；index 無快取；根路徑／favicon 指向 frontend | `main.py`（`serve_frontend_index`、`StaticFiles`、`/frontend`） |
| 本機啟動開 frontend URL | `local_launch.py` `HTML_SUFFIX = "/frontend/index.html"`；`bench_startup.py`／`diagnose_gate_e2e.py` 同 | `scripts/local_launch.py`；ADR-0044 §3 |
| 套件打包整棵 `frontend/` | macOS／Windows portable bundle 複製 `frontend`；exe icon 用 `frontend/favicon.ico` | `scripts/build-portable.sh`；`scripts/portable_bundle.ps1`；`scripts/build-portable.ps1` |
| 後端 HTTP 搜尋 | `searchDict` → `GET /words/search/?…` | `frontend/search-workbench.mjs` |
| 後端就緒輪詢 | `fetch("/ready")`；word_cache／tail_progress 文案 | `frontend/gate.mjs`；ADR-0044 §4；CONTEXT §詞庫快取索引／啟動完畢 |
| 關係補錄 view | `#relationView` + `relation-form.mjs` POST 本機 API | `frontend/index.html`；`frontend/relation-form.mjs`；`frontend/view-sync.mjs` |
| 詞庫勘誤 view | `#correctionsView` + `lexicon-corrections.mjs` | `frontend/view-sync.mjs`；`frontend/lexicon-corrections.mjs`；`docs/lexicon-corrections.md` |
| Chrome-tabs／拖曳 | `chrome-tabs-layout.mjs`、`tab-geometry.mjs`、vendor Draggabilly；`chrome-tabs.css` | `frontend/main.mjs`；`frontend/index.html` |
| file:// 後備說明頁 | 直接開 HTML 時導向本機 URL | `frontend/main.mjs` `showFileFallback` |
| Portable 結果列徽章契約 | 徽章跟 **已送出／tab 查詢**（`entry-detail-portable.mjs`） | `frontend/entry-detail-portable.mjs`；CONTEXT §同音異讀查詢 |
| 教學 manifest 閘讀 frontend | `guide_manifest.py`／`check_guide_examples.py` 以 `frontend/guide-i18n.mjs` 為準 | `scripts/guide_manifest.py`；CONTEXT §搜尋教學驗收 |
| 可搬移 venv／quarantine／word cache 預熱 | 與 UI 無關但屬 Portable 渠道唯一啟動／發佈面 | ADR-0044；`portable/START.*`；`scripts/portable_venv.py`；`scripts/warm_word_cache.py` |

PWA 明確過濾 maintainer views：

```41:49:client/src/query-tabs/useQueryTabs.ts
const PWA_VIEWS = new Set([VIEW.SEARCH, VIEW.GUIDE, VIEW.ABOUT]);

function sanitizePwaTabState(state: TabState): TabState {
  const tabs = state.tabs.filter((t) => PWA_VIEWS.has(t.view));
  // ...
}
```

（歷史規格亦寫「relation/corrections view（PWA 不 expose）」— `specs/001-pwa-offline-coexist/tasks.md`。）

---

## 4. PWA／client-only behaviors（只存在於 `client/`）

| 行為 | 說明 | 來源 |
|------|------|------|
| Vite 靜態束 + Pages | `npm run build` → `client/dist`；workflow 部署 | `.github/workflows/pages.yml`；CONTEXT §靜態客戶端束／PWA 交付頻道；ADR-0045 §1 |
| Service Worker | `virtual:pwa-register`；Cache First；詞庫預取 | `client/src/main.tsx`；CONTEXT §詞庫預取；ADR-0045 §1–2 |
| 瀏覽器查詢引擎 | TS port；直操 sql.js／OPFS 庫；**唔**呼叫 `/words/search/` | `client/src/db/query/*`；ADR-0045 §1 |
| 詞庫懶載／manifest／gz | `lexicon-manifest.json`、OPFS 寫入、完整性校驗、開庫降級 | `client/src/db/lexicon-manifest.ts`；`opfs-lexicon.ts`；`lexicon-restore.ts`；ADR-0045 §2–4 |
| 雙階啟動（PWA 定義） | 閘前：開庫＋探針；tail：靜態詞林／字面集／音素倒排 | `client/src/db/tail-preload.ts`；`ready-gate.tsx`；CONTEXT §離線啟動預載 |
| Debounce 即時搜尋 | `useDebouncedSearchQuery`；熱路徑跟輸入 | `client/src/hooks/useDebouncedSearchQuery.ts`；`App.tsx` `useLiveFetch` |
| 多讀音徽章跟即時輸入 | `committedQuery={inputQuery}` | `client/src/App.tsx`；CONTEXT §同音異讀（PWA vs Portable 差異） |
| PWA 安裝橫幅 | `beforeinstallprompt`／`PwaInstallBanner` | `client/src/components/PwaInstallBanner.tsx`；`hooks/usePwaInstallPrompt.ts` |
| 開庫後端標示「· OPFS」 | 頂欄依實際後端 | `client/src/mode-menu.tsx`；CONTEXT §開庫後端標示 |
| Benchmark 入口 | `?benchmark` → `BenchmarkApp` | `client/src/main.tsx` |
| PWA 專用 CSS／字體子集 | `root.css`、`pwa-app.css`；critical serif 建置 | `client/src/main.tsx`；`client/scripts/build-fonts.ts`；`check_seams.py` |
| 詞庫渠道同步腳本 | `copy-db.js` → `client/public/` | ADR-0045 §4；`client/copy-db.js`（路徑慣例） |

---

## 5. Migration risks（若以 `client/` 為唯一 UI）— 依嚴重度排序

供後續「frontend 退役準則」grilling；此處只列風險，不開方案決賽。

### R1 — Critical：Portable 發佈／啟動硬綁 `frontend/`

- Bundle 複製整棵 `frontend/`；啟動開 `/frontend/index.html`；FastAPI 靜態掛載。  
- **風險**：刪或「搬走」`frontend/` 而未改 `main.py`、`local_launch.py`、`build-portable.*`、`portable_bundle.ps1`、煙霧／seam 測試 → **免安裝渠道即死**。  
- **來源**：ADR-0044；`scripts/build-portable.sh` L48；`scripts/portable_bundle.ps1`；`scripts/local_launch.py`；`main.py`。

### R2 — Critical：共享模組與 CSS SSOT 仍住在 `frontend/`

- PWA 執行期 **依賴** `frontend/*.mjs` 與 `frontend/*.css`（Vite alias `@shared/*`、相對 import）。  
- Seam 測試強制「CSS 單源在 frontend、禁止 client 複製」。  
- **風險**：天真「刪 frontend 目錄」會同時拆掉 **PWA 建置**；退役須先 **搬共享層**（或改 SSOT 契約），不是只留 `client/`。  
- **來源**：`client/src/main.tsx`；`client/vite.config.ts`；`scripts/check_seams.py`；本票 §2 表。

### R3 — High：維護者工具（關係補錄／詞庫勘誤）無 PWA 面

- 僅 Portable DOM + 本機 API。  
- **風險**：唯一 UI = client 時，若未另開維護者路徑（CLI／保留最小本機頁／未來雲端），**關係補錄與勘誤工作流斷裂**。  
- **來源**：`frontend/relation-form.mjs`；`frontend/lexicon-corrections.mjs`；`useQueryTabs.ts` `PWA_VIEWS`；`docs/lexicon-corrections.md`。

### R4 — High：雙引擎與 parity 閘仍假設兩邊殼並存

- 查詢、explain、教學範例均要求 Portable 後端 ↔ PWA 引擎 parity。  
- **風險**：UI 合併後若仍保留 Python 引擎作 Portable runtime，殼可單一路徑，但 **parity／guide 探針／codegen** 管線要重劃「誰是殼、誰是引擎」；若誤刪 `frontend/guide-i18n.mjs` 而未遷 manifest，教學回歸整片紅。  
- **來源**：ADR-0045 §1 Consequences；CONTEXT §搜尋教學驗收／黃金查詢；`scripts/guide_manifest.py`；`scripts/codegen_query_mode_detect.py`。

### R5 — Medium：就緒閘語意與進度模型不對稱

- Portable：`/ready` + word_cache tail；PWA：下載／OPFS／探針 + 不同 tail。  
- **風險**：把 PWA `ReadyGate` 直接套上 Portable（或相反）會 **說謊進度** 或過早解鎖；須對齊 CONTEXT 契約而非只重用 CSS。  
- **來源**：`frontend/gate.mjs`；`client/src/ready-gate.tsx`；CONTEXT §閘前進度／啟動完畢；ADR-0044 §4 vs ADR-0045 §3。

### R6 — Medium：搜尋互動契約差異（debounce／徽章／標題列）

- PWA 即時 debounce；Portable 偏 committed／後端分頁。Lookup 標題列：PWA 可略過 code／jyutping 列（詞條行已內嵌）。  
- **風險**：單一 UI 時創作者會感到「邊個先係準」；遷移須明示 **以邊條契約為準**，並改 CONTEXT／煙霧。  
- **來源**：CONTEXT §同音異讀；`client/src/db/query/lookup-layout.ts` 註解；`frontend/entry-detail-portable.mjs` vs `App.tsx` `inputQuery`。

### R7 — Medium：分頁 UX 分叉（chrome-tabs vs pills）

- Portable 保留 chrome-tabs／拖曳；PWA 用 pill 列。  
- **風險**：統一 UI 時要選一款或條件編譯；鍵盤捷徑／session 還原／觸控拖曳歷史債（見 001 tasks Phase 10）。  
- **來源**：`frontend/chrome-tabs-layout.mjs`；`client/src/query-tabs/query-tabs-bar.tsx`；specs/001-pwa-offline-coexist/tasks.md。

### R8 — Lower：測試與工具面散落 frontend 路徑

- `tests/check_seams.py`、`tests/*_test.mjs`、`frontend/scripts/*-self-check.mjs`、`bench_startup.py` 均假設 `/frontend` 或 `frontend/` 檔存在。  
- **風險**：退役 PR 若只改產品入口、未改閘與自檢 → CI 紅或假綠。  
- **來源**：`scripts/check_seams.py`；`tests/search_navigation_test.mjs`；`scripts/bench_startup.py`。

---

## 6. Shared inventory（可引用：client 對 frontend 的執行期依賴）

**JS／邏輯（`client/src` 直接或經 alias）：**

- `app-context.mjs`（lang／theme／`SEARCH_RING_BLUR_MS`）
- `about-i18n.mjs`、`guide-i18n.mjs`、`mode-i18n.mjs`、`entry-detail-i18n.mjs`
- `entry-detail-core.mjs`、`result-stats.mjs`、`infinite-results.mjs`
- `query-tabs-state.mjs`、`search-navigation.mjs`（Vite `@shared/*`）、`committed-search.mjs`

**CSS（`client/src/main.tsx`）：**  
`open-design.css`、`ready-gate.css`、`shell.css`、`workbench.css`、`entry-detail.css`

**Portable 殼專用、client 產品路徑未 import 的代表性模組：**  
`main.mjs`、`gate.mjs`、`search-workbench.mjs`、`tabs-core.mjs`、`tabs-ui.mjs`、`view-sync.mjs`、`chrome-tabs-layout.mjs`、`relation-form.mjs`、`lexicon-corrections.mjs`、`entry-detail-portable.mjs`、`query-explain.mjs`（桌面份）、`mode-policy.mjs`（桌面份）

---

## 7. Sources cited（準據清單）

| 類型 | 路徑／錨點 |
|------|------------|
| ADR | `docs/adr/0044-portable-delivery-and-release.md`；`docs/adr/0045-pwa-delivery-and-lexicon-channel.md` |
| 領域 | `CONTEXT.md` §產品邊界（免安裝／Portable／靜態客戶端／PWA）、§就緒閘／啟動完畢、§同音異讀、§搜尋教學驗收 |
| Portable 殼 | `frontend/main.mjs`、`gate.mjs`、`search-workbench.mjs`、`index.html`、`query-tabs-state.mjs`、`relation-form.mjs`、`entry-detail-portable.mjs` |
| PWA 殼 | `client/src/App.tsx`、`main.tsx`、`ready-gate.tsx`、`query-tabs/useQueryTabs.ts`、`db/**` |
| 啟動／發佈 | `main.py`；`scripts/local_launch.py`；`scripts/build-portable.sh`；`scripts/portable_bundle.ps1`；`scripts/build-portable.ps1`；`portable/START.sh`／`START.bat` |
| 契約／閘 | `scripts/check_seams.py`；`scripts/codegen_query_mode_detect.py`；`scripts/guide_manifest.py`；`.github/workflows/pages.yml` |
| 歷史規格 | `specs/001-pwa-offline-coexist/tasks.md`（共享 CSS／tabs；PWA 不含 relation／corrections） |

---

## 8. Pointer for grilling（frontend 退役準準備）

後續 grilling 建議先釘死三個問題（本筆記不回答）：

1. **共享層落點**：繼續以 `frontend/` 作 portable+shared SSOT，還是抽到中立 `shared/`／`contracts/` 後再讓 client 獨佔 UI？  
2. **Portable 是否仍要本機 Python UI 殼**，抑或改嵌 WebView／改開打包後的 `client` dist？  
3. **關係補錄／勘誤** 是否仍為產品必須面，還是接受 CLI-only？

任一答案都會改寫 R1–R4 的退役準則優先序。
