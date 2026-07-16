# Portable Client Host（第 1 段）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 讓 Portable 改餵 `client` 的 `PORTABLE_HOST` 建置產物（掛在 `/app/`），以本機 `/words/search`＋`/ready` 運行；並依序完成 chrome-tabs、維護者工具與發佈切斷，達 #86 第 (1) 段綠燈。

**Architecture:** 建置期分支（`import.meta.env.VITE_PORTABLE_HOST`）產出 `client/dist-portable/`（`base: '/app/'`，無 PWA／SW）。FastAPI 掛該目錄於 `/app/`；React 在 portable 模式用 HTTP 搜尋與 `/ready` 閘，不初始化瀏覽器查詢引擎。PWA `client/dist` 路徑不變。`frontend/` 暫留共享 SSOT。

**Tech Stack:** Vite 8、React 19、FastAPI、既有 `/words/search`／`/ready` API、portable bundle 腳本

**Spec:** [`docs/superpowers/specs/2026-07-16-portable-client-host-design.md`](../specs/2026-07-16-portable-client-host-design.md)

**GitHub:** Epic [#88](https://github.com/bill-iu/Canto-0243/issues/88) · PR1 [#89](https://github.com/bill-iu/Canto-0243/issues/89) · PR2 [#90](https://github.com/bill-iu/Canto-0243/issues/90) · PR3 [#91](https://github.com/bill-iu/Canto-0243/issues/91) · PR4 [#92](https://github.com/bill-iu/Canto-0243/issues/92)

---

## File map（PR1）

| 路徑 | 職責 |
|------|------|
| `client/vite.config.ts` | `portableHost` 時：`base:'/app/'`、`outDir:'dist-portable'`、省略 `VitePWA` |
| `client/package.json` | 新增 `build:portable` script |
| `client/src/host-mode.ts` | `isPortableHost()` 讀 `import.meta.env.VITE_PORTABLE_HOST` |
| `client/src/main.tsx` | portable：不 `registerSW`、不 `scheduleLexiconPrecache` |
| `client/src/hooks/db-provider.tsx`（或 `useDB.ts`／新 `portable-ready.ts`） | portable：跳過 OPFS 開庫；`isReady` 跟 `/ready` |
| `client/src/hooks/use-portable-search.ts`（新） | `fetch('/words/search/?…')`；對齊 workbench 的 mode／limit／offset |
| `client/src/hooks/useDB.ts` | `useSearch`：portable 時委派 `use-portable-search` |
| `client/src/App.tsx`／就緒閘元件 | portable 閘文案／進度跟 `/ready` snapshot（可重用／薄包 `frontend/gate` 語意） |
| `main.py` | 掛 `/app` → `client/dist-portable`；缺目錄則啟動失敗；no-cache 跟 `/app/`；meta 注入改伺 portable index |
| `scripts/local_launch.py` | `HTML_SUFFIX = "/app/index.html"` |
| `scripts/portable_bundle.ps1`、`scripts/build-portable.sh` | 複製 `client/dist-portable` → 套件內 `app/`（或約定路徑與 `main.py` 一致）；停複製整棵 `frontend/` 作 UI |
| `tests/smoke/…` 或小 self-check | 斷言 portable build 無 `virtual:pwa-register`；掛載路徑存在檢查 |

**PR2–PR4 觸及（後續 task 再細拆）：** chrome-tabs 元件、`relation-form`／`lexicon-corrections` React 面、release README／CI。

---

## PR1 — 基建最小切片

### Task 1: `isPortableHost` + Vite portable build

**Files:**
- Create: `client/src/host-mode.ts`
- Modify: `client/vite.config.ts`
- Modify: `client/package.json`
- Create: `client/scripts/portable-host-build-self-check.mjs`

- [ ] **Step 1: Add host-mode helper**

```ts
/** Build-time portable host (FastAPI + /words/search). PWA builds leave this false. */
export function isPortableHost(): boolean {
  return import.meta.env.VITE_PORTABLE_HOST === '1';
}
```

- [ ] **Step 2: Branch `vite.config.ts`**

在 `defineConfig` 改為讀 `process.env.VITE_PORTABLE_HOST === '1'`（或 `PORTABLE_HOST`）：

- `portableHost === true` 時：
  - `base: '/app/'`
  - `build.outDir: 'dist-portable'`
  - `build.emptyOutDir: true`
  - `plugins`：**不要**加入 `VitePWA(...)`；保留 `react()`、`readyGateCssPlugin()`（可保留 lexicon dev mount 僅 `command==='serve'`）
- `portableHost === false`：維持現況（`base` Pages／`VitePWA`／預設 `dist`）

定義 env 型別（若專案有 `vite-env.d.ts`）：

```ts
interface ImportMetaEnv {
  readonly VITE_PORTABLE_HOST?: string
}
```

- [ ] **Step 3: package.json script**

```json
"build:portable": "cross-env VITE_PORTABLE_HOST=1 vite build"
```

若 repo 無 `cross-env`：Windows／Unix 分別用：

```json
"build:portable": "vite build --mode portable"
```

並新增 `client/.env.portable`：

```
VITE_PORTABLE_HOST=1
```

（`--mode portable` 會載入 `.env.portable`。）**優先用 mode 檔，避免新依賴。**

- [ ] **Step 4: Self-check script**

`client/scripts/portable-host-build-self-check.mjs`：讀 `dist-portable/index.html`＋主 JS bundle，assert：

- 檔案存在
- bundle **不含** 字串 `virtual:pwa-register`（或 `workbox`）
- `index.html` 內 asset 路徑以 `/app/` 開頭（或相對 `./` 且 base 正確）

- [ ] **Step 5: Run build + check**

```bash
cd client && npm run build:portable && node scripts/portable-host-build-self-check.mjs
```

Expected: exit 0；`client/dist-portable/` 非空。

- [ ] **Step 6: Commit**

```bash
git add client/src/host-mode.ts client/vite.config.ts client/package.json client/.env.portable client/scripts/portable-host-build-self-check.mjs client/src/vite-env.d.ts
git commit -m "feat(client): add PORTABLE_HOST vite build to dist-portable"
```

---

### Task 2: Portable main entry — no SW / no lexicon precache

**Files:**
- Modify: `client/src/main.tsx`

- [ ] **Step 1: Gate SW registration**

```tsx
import { isPortableHost } from './host-mode.ts';

// ... existing CSS imports stay (shared frontend CSS SSOT)

if (!isPortableHost()) {
  const { registerSW } = await import('virtual:pwa-register'); // or keep static import behind if
  // Prefer: static import only in PWA — use conditional dynamic import so portable build can tree-shake
}
```

**更好（避免 portable build 解析 `virtual:pwa-register`）：** 拆檔：

- Create: `client/src/pwa-register.ts` — 內含 `registerSW`＋`scheduleLexiconPrecache`
- `main.tsx`：

```tsx
import { isPortableHost } from './host-mode.ts';

if (!isPortableHost()) {
  void import('./pwa-register.ts');
}
```

`pwa-register.ts` 放現有 `registerSW`／precache 邏輯。

- [ ] **Step 2: Build both modes**

```bash
cd client && npm run build:portable && npm run build
```

Expected: 兩者皆成功；portable self-check 仍綠；PWA `dist/` 仍有 SW 產物。

- [ ] **Step 3: Commit**

```bash
git add client/src/main.tsx client/src/pwa-register.ts
git commit -m "feat(client): skip SW and precache in portable host build"
```

---

### Task 3: Portable readiness + API search hooks

**Files:**
- Create: `client/src/hooks/use-portable-ready.ts`
- Create: `client/src/hooks/use-portable-search.ts`
- Modify: `client/src/hooks/db-provider.tsx`（或 `useDB.ts` 的 provider 路徑）
- Modify: `client/src/hooks/useDB.ts`（`useSearch`）
- Test: `client/scripts/portable-api-search-self-check.mjs`（可 mock／純 URL 組裝單測）

參考現行 `frontend/search-workbench.mjs` 組 URL：

```js
let url = `/words/search/?q=${encodeURIComponent(input)}&mode=${encodeURIComponent(mode)}&limit=${pageSize}&offset=${offset}`;
```

及 `frontend/gate.mjs` 輪詢 `GET /ready`。

- [ ] **Step 1: `use-portable-ready.ts`**

輪詢 `/ready`（間隔 ~500ms，與現 gate 類似），解析 JSON：`ready`／契約欄位（以 `get_readiness_snapshot` 實際鍵為準——實作前讀 `app/startup/offline_preload.py`）。暴露：`{ isReady, snapshot, error }`。

- [ ] **Step 2: Provider 分支**

當 `isPortableHost()`：

- **不要**呼叫 `initializeDatabase`／OPFS
- `isReady`／gate overlay 狀態改接 `use-portable-ready`
- `status` 可映射為 `ready`／`loading` 以減少 `App.tsx` 大改

當非 portable：維持現況。

- [ ] **Step 3: `use-portable-search.ts`**

實作與 `useSearch` 相同的對外 shape（`results`、`total`、`hint`、`loading`、`hasMore`、`loadMore`…），內部 `fetch` API。Mode 字串對齊後端（`0243`／`02493`／`394052`／`synonym` 等——對照 `app/routers/word.py` 與 workbench）。

- [ ] **Step 4: `useSearch` 委派**

```ts
export function useSearch(...) {
  if (isPortableHost()) {
    return usePortableSearch(...);
  }
  // existing engine path
}
```

注意 hooks 規則：不可條件呼叫不同 hook。改為：

```ts
export function useSearch(...) {
  const portable = isPortableHost();
  const portableResult = usePortableSearch(portable ? query : '', ...);
  const engineResult = useEngineSearch(!portable ? query : '', ...);
  return portable ? portableResult : engineResult;
}
```

或抽 `useEngineSearch`＝現有本體。空 query 時兩側皆 no-op。

- [ ] **Step 5: Manual／smoke**

有本機 `lyrics.db` 時：先完成 Task 4 掛載後再測。此步至少跑 TypeScript／既有 client self-check 不破。

- [ ] **Step 6: Commit**

```bash
git add client/src/hooks/use-portable-ready.ts client/src/hooks/use-portable-search.ts client/src/hooks/useDB.ts client/src/hooks/db-provider.tsx
git commit -m "feat(client): portable host ready gate and /words/search adapter"
```

---

### Task 4: FastAPI `/app/` mount + local_launch

**Files:**
- Modify: `main.py`
- Modify: `scripts/local_launch.py`
- Create: `tests/smoke/test_portable_app_mount.py`（或擴充現有 startup smoke）

- [ ] **Step 1: Resolve UI dir**

```python
APP_UI_DIR = Path(os.getenv("CANTO_APP_UI", "client/dist-portable"))
```

若 `not APP_UI_DIR.is_dir()` 或缺 `index.html`：在 lifespan 或 mount 前 `raise RuntimeError("… run: cd client && npm run build:portable")`——**禁止**回退 `frontend/`。

- [ ] **Step 2: Replace frontend product mount**

- 將產品靜態掛載改為：`app.mount("/app", StaticFiles(directory=APP_UI_DIR, html=True), name="app_ui")`
- 提供 `GET /app/index.html`（或依賴 StaticFiles html）並注入 `canto-portable`／`canto-lexicon-version` meta（移植現有 `serve_frontend_index` 邏輯到新路徑）
- `FrontendNoCacheMiddleware`：路徑改 `startswith("/app")`
- `home()` JSON 的 `frontend` 鍵改為 `app` URL（或並行兩鍵一個版本後刪）
- favicon：可改從 `APP_UI_DIR` 或暫留 `frontend/favicon.ico`（共享資產；計畫允許暫留）

**過渡：** 可暫時保留 `/frontend` mount **只給**尚未遷移的測試，但 `local_launch` 不得再開它。Spec 要求產品入口為 `/app/`——PR1 起 launch 只開 `/app/`。

- [ ] **Step 3: `local_launch.py`**

```python
HTML_SUFFIX = "/app/index.html"
```

同步改 `bench_startup.py`／`diagnose_gate_e2e.py` 若硬編碼 `/frontend/index.html`。

- [ ] **Step 4: Smoke test**

```python
def test_app_ui_dir_required(tmp_path, monkeypatch):
    monkeypatch.setenv("CANTO_APP_UI", str(tmp_path / "missing"))
    # importing/mount helper raises clear error
```

- [ ] **Step 5: Manual path**

```bash
cd client && npm run build:portable
# from repo root, with venv:
PORTABLE=1 python -c "import main; print('ok')"  # or start via local_launch
```

Expected: 瀏覽器 `/app/` 可載入；`/ready` 200；搜尋有結果。

- [ ] **Step 6: Commit**

```bash
git add main.py scripts/local_launch.py scripts/bench_startup.py tests/smoke/test_portable_app_mount.py
git commit -m "feat: serve portable UI from /app (client dist-portable)"
```

---

### Task 5: Bundle scripts copy `dist-portable`

**Files:**
- Modify: `scripts/portable_bundle.ps1`
- Modify: `scripts/build-portable.sh`
- Modify: `scripts/build-portable.ps1`（若有複製 frontend）

- [ ] **Step 1: Copy UI**

將 `Copy-PortableTree frontend → frontend` 改為複製 `client/dist-portable` → 套件內 **`client/dist-portable`**（與 `main.py` 預設相對路徑一致；工作目錄為套件根）。

或複製到套件根 `app-ui/` 並設 `CANTO_APP_UI=app-ui`——**選前者少 env**。

- [ ] **Step 2: Build order note**

在 `portable/README.txt` 或 build 腳本開頭：`npm run build:portable` 必須先成功。

- [ ] **Step 3: Commit**

```bash
git add scripts/portable_bundle.ps1 scripts/build-portable.sh scripts/build-portable.ps1 portable/README.txt
git commit -m "build(portable): ship client dist-portable instead of frontend tree"
```

---

### Task 6: PR1 驗收清單（人工＋自動）

- [ ] `npm run build:portable` + self-check 綠
- [ ] `npm run build`（PWA）綠；Pages artifact check 綠
- [ ] `PORTABLE=1` + `local_launch` 開 `/app/index.html` → 閘解鎖 → 查 `23`／`就=` 有列
- [ ] `python -m unittest discover -s tests/smoke -q`（或專案慣用子集）綠
- [ ] 在 PR 描述貼上上述結果；**不宣告**第 (1) 段完成

---

## PR2 — chrome-tabs（僅 portable）

### Task 7: Portable tabs chrome

**Files（預期）：**
- Create: `client/src/query-tabs/chrome-tabs-bar.tsx`（或包裝現有 `frontend/chrome-tabs-layout.mjs`）
- Modify: `client/src/query-tabs/query-tabs-bar.tsx` 或 `App.tsx`：`isPortableHost() ? <ChromeTabsBar/> : <PillBar/>`
- 保留 `@shared/query-tabs` 狀態

- [ ] **Step 1:** 移植／包裝 chrome-tabs＋必要 CSS／Draggabilly 依賴（若 vendor 在 `frontend/`，portable 建置需能解析或改 copy 進 client public）
- [ ] **Step 2:** 僅 `isPortableHost()` 啟用
- [ ] **Step 3:** 手動：多 tab 開合、重整還原、與搜尋聯動
- [ ] **Step 4:** Commit `feat(client): chrome-tabs for portable host only`

---

## PR3 — 維護者工具

### Task 8: Relation + corrections in portable App

**Files（預期）：**
- Create: `client/src/views/relation-view.tsx`、`corrections-view.tsx`（邏輯對照 `frontend/relation-form.mjs`、`lexicon-corrections.mjs`）
- Modify: `client/src/query-tabs/useQueryTabs.ts`：portable 時允許維護者 views；PWA 仍 `PWA_VIEWS`
- Modify: 導航／選單入口僅 portable 顯示

- [ ] **Step 1:** API 對照現有 POST／GET（`app/routers/relation.py`、lexicon corrections）
- [ ] **Step 2:** UI 最小可用（不重設計）
- [ ] **Step 3:** 手動走完補錄＋勘誤主路徑
- [ ] **Step 4:** Commit `feat(client): maintainer views in portable host`

---

## PR4 — 切斷與第 (1) 段收口

### Task 9: Docs、CI、舊入口切斷

**Files:**
- `README.md`、`portable/README.txt`、`docs/CONTRIBUTING.md`（若寫死 `/frontend`）
- CI／smoke 內硬編碼 `/frontend/index.html` 者改 `/app/`
- `main.py`：若仍 mount 舊 `/frontend` 作產品入口 → **移除產品入口**（共享檔仍留 repo）
- 地圖 #83 或實作 epic 留言「第 (1) 段完成」

- [x] **Step 1:** ripgrep `frontend/index.html`／`HTML_SUFFIX`／bundle `frontend` UI 複製，清掉產品路徑（文件／CI／seam／舊殼提示 → `/app/`；`frontend/` 仍留共享 SSOT）
- [ ] **Step 2:** 跑 #86 第 (1) 段綠燈：parity／guide／就緒＋核心搜尋；chrome-tabs＋維護者可用 — **待維護者手動綠燈**（見 #83／#92）
- [x] **Step 3:** Commit `chore: cut over portable docs and paths to /app client host`
- [x] **Step 4:** 在 [地圖 #83](https://github.com/bill-iu/Canto-0243/issues/83) 留言：第 (1) 段實作已上 `dev`，待維護者手動綠燈（parity／guide＋chrome-tabs＋維護者工具手動 QA）；第 (2) 段／#87 另開

---

## Spec coverage check

| Spec 項 | Task |
|---------|------|
| `PORTABLE_HOST`／`dist-portable`／無 SW | 1–2 |
| API 搜尋＋`/ready` | 3 |
| `/app/` 掛載、launch、缺 dist 失敗 | 4 |
| bundle 不帶 frontend UI 樹 | 5 |
| PR1 驗收 | 6 |
| chrome-tabs | 7 |
| 維護者工具 | 8 |
| 發佈切斷＋第 (1) 段綠燈 | 9 |
| 不做第 (2)(3)／#87 | 刻意省略 |

## Placeholder scan

無 TBD／TODO；PR2–PR4 為較粗任務塊，開工前可再拆子 plan，但驗收條件已寫死。
