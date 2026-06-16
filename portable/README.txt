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
1. 下載 canto-0243-portable-macos.tar.gz 並解壓
   Download canto-0243-portable-macos.tar.gz and extract.

2. 將 Canto-0243.app 拖到「應用程式」資料夾
   Drag Canto-0243.app to Applications.

3. 雙擊 Canto-0243.app 啟動（無需安裝 Python、無需 chmod）
   Double-click Canto-0243.app (no Python, no Terminal chmod).

   若 macOS 阻擋來自網路的檔案：
   If macOS quarantines the download:

     xattr -dr com.apple.quarantine ~/Applications/Canto-0243.app

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

- macOS「無法打開，因為來自身份不明的開發者」：
  xattr -dr com.apple.quarantine /path/to/Canto-0243.app

- 關閉服務：關閉命令視窗，或從 Dock 結束 Canto-0243.app
  Stop: close the console window, or quit the .app from the Dock.


重新打包（開發者）/ Rebuild (developers)
----------------------------------------
  Windows:  powershell -ExecutionPolicy Bypass -File scripts\build-portable.ps1
  macOS:    bash scripts/build-portable.sh
