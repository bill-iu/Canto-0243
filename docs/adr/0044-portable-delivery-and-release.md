# ADR-0044: 免安裝交付與分渠道發佈（歷史 Portable；運送層見 0068）

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 免安裝交付、**Desktop 套件**（舊 Portable）、全量發佈、發佈詞庫快照、分渠道發佈、本機啟動、詞庫快取索引。

整合並取代下列 stub 之**活決策**（歷史全文見 git）：[0006](./0006-portable-zero-install-delivery.md)、[0008](./0008-release-publishing-tiers.md)、[0011](./0011-local-launch-unified-startup.md)、[0016](./0016-macos-dual-arch-quarantine.md)、[0017](./0017-portable-word-cache-prewarm.md)、[0018](./0018-split-channel-release.md)。

**創作者套件運送／runtime 形態**（舊 §1／§1b venv 包）已由 [ADR-0068](./0068-desktop-pyapp-delivery.md)（Desktop + PyApp + 側車）取代。下列 §1／§1b 保留作**歷史**；新實作唔跟。

## 1. Portable 套件形態（歷史 — superseded by ADR-0068）

1. **建置時打包 venv** — `scripts/portable_venv.py`（`venv --copies` + `pip install -r requirements.txt`）；runtime 腳本一併複製。
2. **運送形態（Win 預設）** — 建置可將整棵 `venv/` 收成套件根目錄單一 **`venv.pack`**（zip），首次啟動 extract-once 再當正常 venv 跑；見歷史 [ADR-0067](./0067-portable-venv-pack-transport.md)。
3. **Windows** — `build-portable.ps1` → `canto-0243-portable.zip`；`START.bat` 只用 bundle venv，不探測系統 Python、不 pip。
4. **macOS** — `build-portable.sh` → `Canto-0243.app`；架構專用 tar `canto-0243-portable-macos-{arm64,x86_64}.tar.gz`。
5. **Linux** — 免安裝不承諾；本機 Python + `START.sh`。
6. **Docker** — 僅維護者開發，非創作者交付。
7. **跨 OS 建置** — Windows zip 在 Windows 建；macOS 產物在對應架構 macOS 建（**仍有效**，資產名見 0068）。

## 1b. 可搬移 runtime（歷史 — superseded by ADR-0068）

舊：物化 python-home／改 `pyvenv.cfg` home、建置硬閘 relocatable。Desktop／PyApp 改為自管發行版 + wheel，唔再以「整包 venv 跟資料夾搬」為產品承諾。

## 2. macOS 下載隔離與簽章

創作者主路徑見 [ADR-0068](./0068-desktop-pyapp-delivery.md)（**`.command`**；`.app` 非現行必達）。

1. **清除 quarantine** — 啟動腳本經既有邏輯清 `com.apple.quarantine`（能做則做）；教學仍覆蓋右鍵打開／仍要開啟。
2. **ad-hoc codesign** — 若仍產出 `.app`／binary，可 ad-hoc sign；**未 notarize**。
3. **可搬移 dylib** — 歷史 venv 路徑；PyApp 自管發行版後唔再係主線。
4. **Gatekeeper** — 教學以 **`.command`** 為準（Sequoia：右鍵→打開／仍要開啟）。

## 3. 本機啟動編排

1. **`scripts/local_launch.py` 單點** — 終端即時回饋 → free_port → 背景 `main.py` → HTML 200 → 開瀏覽器 → 背景 gate 輪詢。`HTML_SUFFIX = "/app/index.html"`（產品 UI＝`client/dist-portable`）。
2. **入口委派** — `start.sh`、`portable/START.bat`、`portable/START.sh`、`portable/macos/launcher`。
3. **bootstrap** — lifespan 單次 schema／bootstrap；**Desktop／PyApp** 首次由 launcher 裝 env／wheel（見 0068），其後產品路徑唔再 pip；dev `start.sh` 僅 requirements hash 變時 pip。
4. **體感** — 維護者在開發路徑用 `bench_startup.py` 驗 Desktop 級 HTML／終端回饋（不進 CI）。
5. **產品 UI 束** — 發佈／本機啟動前須 `cd client && npm run build:portable`（內部名可暫留）；FastAPI 掛 `/app/` → `client/dist-portable`。共享 mjs／CSS SSOT 在 **`shared/`**（唔掛產品入口）。

## 4. 詞庫快取預暖（Portable）

1. 建置時 `warm_word_cache.py` 寫 `.cache/word_meta.bin`（綁 `lyrics.db` size+SHA-256，**唔綁路徑**）。
2. 指紋不符則 runtime 冷建；就緒閘契約不變。

## 5. 發佈分層與渠道

1. **單層全量** — 換庫或可感知產品變更 → **新 semver 全量發佈**（**Desktop** zip／tar + 首次上傳 `lyrics.db`／`words-lexicon.json`）。**取消**獨立「只換庫唔換程式」嘅 **詞庫發佈** 層（舊 `release-lexicon.yml` 已停用）。
2. **程式刷新同一 tag** — 行為／介面不變嘅打包或 bugfix：`git tag -f` 後重打 zip／tar；**本機優先**有 `lyrics.db`，缺則從該 tag Release **下載**（**唔**跑 `build-db`）；**唔**覆寫／重傳獨立庫資產（Pages 繼續用 Release 上既有 `lyrics.db`）。逃生：Windows `-WithLexicon`。
3. **分渠道本機上傳**  
   - **Windows 渠道**：本機腳本主理建 Release、Desktop zip；新 tag 先傳庫。  
   - **macOS 渠道**：本機腳本建架構專用 tar，上傳同一 tag；**補 tar 必從 Release 下載 `lyrics.db`**（唔用 stale 本機 copy）。  
4. **停用** tag 觸發全量 CI matrix；保留 `ci.yml`；**唔**再維護詞庫-only workflow。
5. **操作手冊** — [docs/release.md](../release.md) 為唯一 checklist（實作 PyApp 後同步改名／步驟）。

**Considered Options（摘要）**

- 創作者自行 pip／full-app PyInstaller — 拒（免安裝／體積除錯）。**運送引擎**其後改 [ADR-0068](./0068-desktop-pyapp-delivery.md) PyApp，唔轉嫁打包負擔。
- 維持 tag CI 全量 matrix — 拒（macOS 失敗、與本機驗收脫節）。
- 五件套齊才 Publish — 拒（阻塞 Windows）；改 Windows 先發。
- 單一 arm64 + Rosetta — 拒（Intel 風險）。
- 只冷建不打包 word cache — 拒（首次過慢）。
- 將 `lyrics.db` 納入 git／LFS 以加快發佈 — 拒（主目標係程式-only 重用庫；庫仍本機＋Release 資產）。
- 保留獨立詞庫發佈層 — 拒（維護者換庫幾乎都開新 semver；程式修正多用 refresh tag）。
- 歷史：venv.pack／物化 python-home — 見 0067／本 ADR 舊 §1；正式渠道已由 0068 取代。

**Consequences**

- 分渠道上傳與「換庫必重打包」仍有效；創作者套件形態見 **0068**（PyApp + wheel + 側車）。
- 維護者須維護 Windows + macOS 兩條上傳腳本（資產名 desktop 化隨實作）。
- 刷新 tag **唔好刪** Release 上既有 `lyrics.db`（Pages 依賴）。
- 換庫必須新 tag 全量或 refresh＋重打套件；唔再靠 `release-lexicon.yml`。
- 發佈前建議解壓 smoke；CI 靠 L1 硬閘 + L2 接縫。
