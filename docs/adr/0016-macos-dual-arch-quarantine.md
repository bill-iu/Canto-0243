# macOS 雙原生架構與下載隔離

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § macOS 應用程式套件、全量發佈、免安裝交付。

取代 [ADR-0008](0008-release-publishing-tiers.md) 中「單一 macOS tar」與「四件套」之 macOS 部分；Windows zip 與詞庫資產政策不變。

## 我們決定

1. **雙原生 macOS tar** — 全量 Release 附 `canto-0243-portable-macos-arm64.tar.gz`（Apple Silicon）與 `canto-0243-portable-macos-x86_64.tar.gz`（Intel）；各 tar 內 `.app` 的 bundled venv 為該架構原生，唔靠 Rosetta 單檔冒充通用。
2. **五件套** — 全量 artifact：`lyrics.db`、`words-lexicon.json`、`canto-0243-portable.zip`、上述兩個 macOS tar。
3. **下載隔離** — `portable/macos/launcher` 與 `portable/START.sh` 於啟動時呼叫 `scripts/portable_macos.py` 清除 `com.apple.quarantine`；**唔得**要求創作者手動 `xattr`（見 CONTEXT）。
4. **建置時 ad-hoc 淺簽** — 只簽 `Contents/MacOS/Canto-0243` 與外層 `.app`（**唔** `--deep` 簽 `venv`，避免 Sequoia「無法開啟」）。
5. **備用入口** — tar 內附 `Open Canto-0243.command`：清隔離後 `open` `.app`；唔要求創作者手動 Terminal `xattr`。
6. **CI** — `release-full.yml` 的 `build-macos` 以 matrix 分別在 `macos-latest`（arm64）與 `macos-15-intel`（x86_64）runner 建置；兩邊皆 green 才 publish。

**Considered Options**

- 單一 arm64 tar + Rosetta — Intel 創作者可能 `bad CPU type`；唔採用。
- 只文件教學手動 `xattr` — 違反免安裝交付；唔採用。
- 僅 launcher 清隔離、唔 codesign — Sequoia 上若 Gatekeeper 於執行前阻擋，launcher 無法執行；故建置時加 ad-hoc 淺簽。
- `codesign --deep` 簽含 venv 的 bundle — 內部未簽 Mach-O 可能令 Finder「無法開啟應用程式」；改淺簽。

**Consequences**

- 詞庫發佈 workflow 須驗證兩個 macOS tar 皆存在（見 `release-lexicon.yml`）。
- 維護者手動全量 checklist 須在兩台 macOS（或 CI）各建一次，或依 CI。
- `portable/README.txt` 與 README 下載說明須標明依晶片選 tar。
