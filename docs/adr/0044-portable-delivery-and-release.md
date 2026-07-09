# ADR-0044: Portable 免安裝交付與分渠道發佈

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 免安裝交付、Portable 套件、macOS 應用程式套件、全量發佈、詞庫發佈、分渠道發佈、本機啟動、詞庫快取索引。

整合並取代下列 stub 之**活決策**（歷史全文見 git）：[0006](./0006-portable-zero-install-delivery.md)、[0008](./0008-release-publishing-tiers.md)、[0011](./0011-local-launch-unified-startup.md)、[0016](./0016-macos-dual-arch-quarantine.md)、[0017](./0017-portable-word-cache-prewarm.md)、[0018](./0018-split-channel-release.md)。

## 1. Portable 套件形態

1. **建置時打包 venv** — `scripts/portable_venv.py`（`venv --copies` + `pip install -r requirements.txt`）；runtime 腳本一併複製。
2. **Windows** — `build-portable.ps1` → `canto-0243-portable.zip`；`START.bat` 只用 bundle venv，不探測系統 Python、不 pip。
3. **macOS** — `build-portable.sh` → `Canto-0243.app`；架構專用 tar `canto-0243-portable-macos-{arm64,x86_64}.tar.gz`（各架構原生 venv，不靠 Rosetta 冒充）。
4. **Linux** — 免安裝不承諾；本機 Python + `START.sh`。
5. **Docker** — 僅維護者開發，非創作者交付。
6. **跨 OS 建置** — Windows zip 在 Windows 建；macOS `.app` 在對應架構 macOS 建。

## 2. macOS 下載隔離與簽章

1. **清除 quarantine** — `portable/macos/launcher`／`START.sh` 經 `portable_macos.py` 清 `com.apple.quarantine`；**唔**要求創作者手動 `xattr`。
2. **ad-hoc deep codesign** — 建置時 `codesign --deep --force --sign -` 整 `.app`；另簽 `Open Canto-0243.command`；強制 LF 行尾。
3. **可搬移 dylib** — venv 內 `libpython` 改 `@loader_path`（避免建置機絕對路徑）。
4. **Gatekeeper** — 未 notarize；教學以「右鍵→打開／仍要開啟」覆蓋 Sequoia。

## 3. 本機啟動編排

1. **`scripts/local_launch.py` 單點** — 終端即時回饋 → free_port → 背景 `main.py` → HTML 200 → 開瀏覽器 → 背景 gate 輪詢。
2. **入口委派** — `start.sh`、`portable/START.bat`、`portable/START.sh`、`portable/macos/launcher`。
3. **bootstrap** — lifespan 單次 schema／bootstrap；Portable 永不 pip；dev `start.sh` 僅 requirements hash 變時 pip。
4. **體感** — 維護者在開發路徑用 `bench_startup.py` 驗 Portable 級 HTML／終端回饋（不進 CI）。

## 4. 詞庫快取預暖（Portable）

1. 建置時 `warm_word_cache.py` 寫 `.cache/word_meta.bin`（綁 `lyrics.db` size+SHA-256，**唔綁路徑**）。
2. 指紋不符則 runtime 冷建；就緒閘契約不變。

## 5. 發佈分層與渠道

1. **兩層** — **全量發佈**（程式 + Portable + 詞庫資產）vs **詞庫發佈**（只換同 semver Release 上的 `lyrics.db`／`words-lexicon.json`）。
2. **分渠道本機上傳（取代 tag 全量 CI）**  
   - **Windows 渠道**：本機 `release-windows-local.ps1` 上傳 zip／db／lexicon。  
   - **macOS 渠道**：Intel MacBook `release-macos-local.sh` 建 **x86_64** tar，上傳**同一 upstream tag**（`GH_REPO` 指上游）。  
   - Windows zip 齊可先 **Publish**；macOS 後補；notes 註明 arm64 過渡期可不提供。
3. **停用** tag 觸發 `release-full.yml` 類全量 matrix；保留 `ci.yml` 與 `release-lexicon.yml`。
4. **詞庫 workflow 前置** — 該 tag 已有 **Windows zip + macOS x86_64 tar**（arm64 不強制）。
5. **操作手冊** — [docs/release.md](../release.md) 為唯一 checklist。

**Considered Options（摘要）**

- 創作者自行 pip／PyInstaller 單檔 — 拒（免安裝／體積除錯）。
- 維持 tag CI 全量 matrix — 拒（macOS 失敗、與本機驗收脫節）。
- 五件套齊才 Publish — 拒（阻塞 Windows）；改 Windows 先發。
- 單一 arm64 + Rosetta — 拒（Intel 風險）。
- 只冷建不打包 word cache — 拒（首次過慢）。

**Consequences**

- 套件體積含 venv + 可選 `.cache`。
- 維護者須維護 Windows +（過渡期）Intel Mac 兩條上傳腳本。
- 詞庫發佈不得在未有 zip+x86_64 的 semver 上單獨進行。
