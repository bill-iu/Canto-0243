# ADR-0044: Portable 免安裝交付與分渠道發佈

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 免安裝交付、Portable 套件、macOS 應用程式套件、全量發佈、發佈詞庫快照、分渠道發佈、本機啟動、詞庫快取索引。

整合並取代下列 stub 之**活決策**（歷史全文見 git）：[0006](./0006-portable-zero-install-delivery.md)、[0008](./0008-release-publishing-tiers.md)、[0011](./0011-local-launch-unified-startup.md)、[0016](./0016-macos-dual-arch-quarantine.md)、[0017](./0017-portable-word-cache-prewarm.md)、[0018](./0018-split-channel-release.md)。

## 1. Portable 套件形態

1. **建置時打包 venv** — `scripts/portable_venv.py`（`venv --copies` + `pip install -r requirements.txt`）；runtime 腳本一併複製。
2. **Windows** — `build-portable.ps1` → `canto-0243-portable.zip`；`START.bat` 只用 bundle venv，不探測系統 Python、不 pip。
3. **macOS** — `build-portable.sh` → `Canto-0243.app`；架構專用 tar `canto-0243-portable-macos-{arm64,x86_64}.tar.gz`（各架構原生 venv，不靠 Rosetta 冒充）。
4. **Linux** — 免安裝不承諾；本機 Python + `START.sh`。
5. **Docker** — 僅維護者開發，非創作者交付。
6. **跨 OS 建置** — Windows zip 在 Windows 建；macOS `.app` 在對應架構 macOS 建。

## 1b. 可搬移 runtime（Win／Mac 對稱）

1. **建置物化** — 唔依賴建置機絕對路徑上嘅系統／uv Python。  
   - **macOS**：stdlib／libpython 物化入 venv；`pyvenv.cfg` `home` 指 venv 內。  
   - **Windows**：物化完整前綴到 `venv/python-home/`（含 `python.exe`、`python*.dll`、`DLLs/`、`Lib/`）；`home` 指該目錄。Windows `Scripts/python.exe` 係 redirector，**必須**有 `{home}\python.exe`（只拷 stdlib 不足；#66）。
2. **啟動改 home** — 解壓路徑異於建置路徑時，啟動前改寫 `pyvenv.cfg`：  
   - macOS：`portable_macos.py`／launcher。  
   - Windows：`START.bat`（PowerShell，先於 venv python）與 `Canto-0243.exe`（`portable_win_launcher` inline patch）。
3. **建置硬閘** — `_assert_venv_relocatable`：`prefix`／`base_prefix`／`sys.path` 唔得指套件外（含 Windows 盤符路徑）；`pyvenv.cfg` `home` 必須在 venv 下。失敗則 build fail。
4. **拒** — 文件要求創作者裝 Python／uv；只在建置機 smoke 當「可搬移」。

## 2. macOS 下載隔離與簽章

1. **清除 quarantine** — `portable/macos/launcher`／`START.sh` 經 `portable_macos.py` 清 `com.apple.quarantine`；**唔**要求創作者手動 `xattr`。
2. **ad-hoc deep codesign** — 建置時 `codesign --deep --force --sign -` 整 `.app`；另簽 `Open Canto-0243.command`；強制 LF 行尾。
3. **可搬移 dylib** — venv 內 `libpython` 改 `@loader_path`（避免建置機絕對路徑）。
4. **Gatekeeper** — 未 notarize；教學以「右鍵→打開／仍要開啟」覆蓋 Sequoia。

## 3. 本機啟動編排

1. **`scripts/local_launch.py` 單點** — 終端即時回饋 → free_port → 背景 `main.py` → HTML 200 → 開瀏覽器 → 背景 gate 輪詢。`HTML_SUFFIX = "/app/index.html"`（產品 UI＝`client/dist-portable`）。
2. **入口委派** — `start.sh`、`portable/START.bat`、`portable/START.sh`、`portable/macos/launcher`。
3. **bootstrap** — lifespan 單次 schema／bootstrap；Portable 永不 pip；dev `start.sh` 僅 requirements hash 變時 pip。
4. **體感** — 維護者在開發路徑用 `bench_startup.py` 驗 Portable 級 HTML／終端回饋（不進 CI）。
5. **產品 UI 束** — 發佈／本機啟動前須 `cd client && npm run build:portable`；FastAPI 掛 `/app/` → `client/dist-portable`。共享 mjs／CSS SSOT 在 **`shared/`**（唔掛產品入口）。

## 4. 詞庫快取預暖（Portable）

1. 建置時 `warm_word_cache.py` 寫 `.cache/word_meta.bin`（綁 `lyrics.db` size+SHA-256，**唔綁路徑**）。
2. 指紋不符則 runtime 冷建；就緒閘契約不變。

## 5. 發佈分層與渠道

1. **單層全量** — 換庫或可感知產品變更 → **新 semver 全量發佈**（Portable zip／tar + 首次上傳 `lyrics.db`／`words-lexicon.json`）。**取消**獨立「只換庫唔換程式」嘅 **詞庫發佈** 層（舊 `release-lexicon.yml` 已停用）。
2. **程式刷新同一 tag** — 行為／介面不變嘅打包或 bugfix：`git tag -f` 後重打 zip／tar；**本機優先**有 `lyrics.db`，缺則從該 tag Release **下載**（**唔**跑 `build-db`）；**唔**覆寫／重傳獨立庫資產（Pages 繼續用 Release 上既有 `lyrics.db`）。逃生：Windows `-WithLexicon`。
3. **分渠道本機上傳**  
   - **Windows 渠道**：`release-windows-local.ps1`（主理：建 Release、zip；新 tag 先傳庫）。  
   - **macOS 渠道**：`release-macos-local.sh` 建 **x86_64** tar，上傳同一 tag；**補 tar 必從 Release 下載 `lyrics.db`**（唔用 stale 本機 copy）。  
4. **停用** tag 觸發全量 CI matrix；保留 `ci.yml`；**唔**再維護詞庫-only workflow。
5. **操作手冊** — [docs/release.md](../release.md) 為唯一 checklist。

**Considered Options（摘要）**

- 創作者自行 pip／PyInstaller 單檔 — 拒（免安裝／體積除錯）。
- 維持 tag CI 全量 matrix — 拒（macOS 失敗、與本機驗收脫節）。
- 五件套齊才 Publish — 拒（阻塞 Windows）；改 Windows 先發。
- 單一 arm64 + Rosetta — 拒（Intel 風險）。
- 只冷建不打包 word cache — 拒（首次過慢）。
- 將 `lyrics.db` 納入 git／LFS 以加快發佈 — 拒（主目標係程式-only 重用庫；庫仍本機＋Release 資產）。
- 保留獨立詞庫發佈層 — 拒（維護者換庫幾乎都開新 semver；程式修正多用 refresh tag）。
- Windows 改用官方 embeddable Python 取代 venv — 拒（與 macOS venv 管線斷裂；#66 用物化 python-home 即可）。
- 只改 `home`／`PYTHONHOME`、唔物化 runtime — 拒（另一台 PC 無建置機 uv 路徑則 redirector 找不到 `python.exe`）。

**Consequences**

- 套件體積含 venv + 可選 `.cache`；Windows 另含 `python-home` 完整前綴（體積上升，換可搬移）。
- 維護者須維護 Windows +（過渡期）Intel Mac 兩條上傳腳本。
- 刷新 tag **唔好刪** Release 上既有 `lyrics.db`（Pages 依賴）。
- 換庫必須新 tag 全量；唔再靠 `release-lexicon.yml`。
- 發佈前建議整夾搬移 smoke（L3）；CI 靠 L1 硬閘 + L2 接縫。
