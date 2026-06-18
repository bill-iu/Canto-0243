# Portable 免安裝交付

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 免安裝交付、Portable 套件、macOS 應用程式套件、開發容器環境。

創作者 A（零技術門檻）應在 **Windows** 解壓 zip 雙擊 **START.bat**、在 **macOS** 雙擊 **Canto-0243.app** 即可查韻，**無需**自行安裝 Python 或執行 pip。**Linux** 維持 L0（本機 Python + START.sh），不列免安裝承諾。**Docker** 僅供維護者開發，非創作者交付。

我們決定：

1. **建置時打包 venv** — `scripts/portable_venv.py` 以 `python -m venv --copies` 在發佈目錄建立可搬移 venv 並 `pip install -r requirements.txt`；`scripts/wait_for_url.py`、`free_port.py` 一併複製。
2. **Windows** — `scripts/build-portable.ps1` 產出含 venv 的 `canto-0243-portable.zip`；`START.bat` 只使用 `venv\Scripts\python.exe`，不再探測系統 Python 或首次 pip。
3. **macOS** — `scripts/build-portable.sh` 產出 `Canto-0243.app`（`Contents/Resources/app` 含完整 bundle + venv），架構專用 `canto-0243-portable-macos-{arm64,x86_64}.tar.gz` 只打包 `.app`；取代 chmod／Terminal 為預設創作者路徑。詳見 [ADR-0016](0016-macos-dual-arch-quarantine.md)。
4. **跨平台建置** — Windows zip 在 Windows 建；macOS .app 在 macOS 建；Release 四件套仍含兩者 + `lyrics.db` + `words-lexicon.json`。
5. **本機啟動契約統一** — `start.sh` 與 Portable `START.*` 共用同一啟動規則（見 CONTEXT § **本機啟動**）；維護者須在開發版路徑驗證 Portable 級體感（HTML 就緒時間、終端即時回饋），不可僅在解壓 zip 後才量測。

**Considered Options**

- 創作者自行 pip（現狀）— 違反免安裝承諾。
- PyInstaller 單檔 exe — 體積與除錯成本高；venv 搬移較貼近現有 main.py 流程。
- 同一 tar 兼 WM — venv 不可跨 OS 共用；分平台建置。

**Consequences**

- Release 套件體積顯著增大（含 Python 依賴）。
- CI／維護者需分 OS 跑 build 腳本。
- Linux 使用者 README 仍說明本機 Python 路徑。
- 啟動腳本變更須同步 `start.sh` 與 `START.*`，並以開發版 smoke 驗證 Portable 體感。
