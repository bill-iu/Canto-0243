Canto-0243 — 免安裝離線版
Canto-0243 Cantonese Rhyme Workbench — Zero-install offline edition
(Windows / macOS / Linux*)
Bundle: Canto-0243 v1.2.0
================================================================

* Linux 仍須本機 Python 3.10+（不列免安裝承諾）。


Windows（免安裝）
-----------------
1. 解壓縮整個資料夾
   Extract the entire folder.

2. 雙擊 START.bat
   Double-click START.bat.

3. 無需安裝 Python；瀏覽器會自動開啟搜尋頁
   No Python install required; your browser opens the search page.


macOS（免安裝）
---------------
1. 依晶片下載對應 tar 並解壓（Apple Silicon → arm64；Intel → x86_64）
   Download the matching tar for your Mac (Apple Silicon → arm64; Intel → x86_64):
     canto-0243-portable-macos-arm64.tar.gz
     canto-0243-portable-macos-x86_64.tar.gz

2. 將 Canto-0243.app 拖到「應用程式」資料夾（或留在解壓目錄）
   Drag Canto-0243.app to Applications (or keep it in the extract folder).

3. 雙擊 Canto-0243.app 啟動（無需安裝 Python、無需 chmod）
   Double-click Canto-0243.app (no Python, no Terminal chmod).

   若 macOS 顯示無法驗證／無法開啟：
   If Gatekeeper blocks the app or script:
     • 對 Canto-0243.app 或 Open Canto-0243.command：右鍵（或 Control+點擊）→「打開」→ 確認
       Right-click (or Control-click) → Open → confirm (once per item).
     • 仍不行再試同目錄的 Open Canto-0243.command（會清隔離並開啟 .app）
       Then try Open Canto-0243.command in the same folder (clears quarantine, opens .app).

   進階：資料夾版仍可用 START.command / START.sh（內含 venv）
   Advanced: folder bundle START.command / START.sh also work.


Linux
-----
  需本機 Python 3.10+；解壓後若無 venv/，請：
  Requires system Python 3.10+; if venv/ is missing:

    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    chmod +x START.sh && ./START.sh


內容 / Contents
---------------
- venv/ — 內建 Python 執行環境（WM 免安裝） / bundled runtime (WM)
- lyrics.db — 主詞庫 / main word database
- data/ — 靜態同義/反義詞典 / static dictionaries
- frontend/ — 網頁介面 / web UI
- app/、main.py — 後端 API / backend API


疑難排解 / Troubleshooting
--------------------------
- 8000 埠被佔用：編輯 .env.local，修改 PORT
  Port 8000 in use: edit .env.local and change PORT.

- 「找不到內建執行環境」：請重新下載完整 Release 套件
  "Bundled runtime missing": re-download the full release package.

- macOS Gatekeeper：確認 tar 與晶片相符（arm64 / x86_64）；被擋時右鍵→「打開」.app 或 Open Canto-0243.command（各一次）
  macOS Gatekeeper: match tar to chip; if blocked, right-click → Open on .app or Open Canto-0243.command (once each).

- 關閉服務：關閉命令視窗，或從 Dock 結束 Canto-0243.app
  Stop: close the console window, or quit the .app from the Dock.


重新打包（開發者）/ Rebuild (developers)
----------------------------------------
  Windows:  powershell -ExecutionPolicy Bypass -File scripts\build-portable.ps1
  macOS:    bash scripts/build-portable.sh
