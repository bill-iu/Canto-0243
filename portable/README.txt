Canto-0243 — Portable 版
Canto-0243 Cantonese Rhyme Workbench — Portable Edition
(Windows / macOS / Linux)
Bundle: v1.0.1-data
================================================================

需求 / Requirements
-------------------
Python 3.10 或以上
Python 3.10 or newer


Windows
-------
1. 解壓縮整個資料夾
   Extract the entire folder.

2. 雙擊 START.bat
   Double-click START.bat.

3. 首次會自動安裝依賴；瀏覽器會開啟搜尋頁
   On first launch, dependencies install automatically; your browser opens the search page.


macOS
-----
1. 解壓縮（建議放到「應用程式」或「文件」，勿從郵件附件直接執行）
   Extract the archive (prefer Applications or Documents; do not run directly from Mail attachments).

2. 首次請在「終端機」執行一次（賦予執行權限）：
   Run once in Terminal (grant execute permission):

     cd /path/to/canto-0243-portable
     chmod +x START.sh START.command
     xattr -dr com.apple.quarantine .    # 若系統阻擋來自網路的檔案
                                           # if macOS blocks downloaded files

3. 之後可雙擊 START.command，或在終端機執行 ./START.sh
   Then double-click START.command, or run ./START.sh in Terminal.

4. 若未安裝 Python：brew install python@3.12
   If Python is missing: brew install python@3.12

   建議使用 canto-0243-portable-macos.tar.gz（較 ZIP 友善）
   Prefer canto-0243-portable-macos.tar.gz over ZIP on Mac.


Linux
-----
  chmod +x START.sh && ./START.sh


內容 / Contents
---------------
- lyrics.db — 主詞庫（已內建） / main word database (included)
- data/ — 靜態同義/反義詞典 / static synonym & antonym dictionaries
- frontend/ — 網頁介面 / web UI
- app/、main.py — 後端 API / backend API


疑難排解 / Troubleshooting
--------------------------
- 8000 埠被佔用：編輯 .env.local，修改 PORT
  Port 8000 in use: edit .env.local and change PORT.

- macOS「無法打開，因為來自身份不明的開發者」：
  macOS “cannot be opened because it is from an unidentified developer”:

    xattr -dr com.apple.quarantine .

- 關閉服務：在終端機視窗按 Ctrl+C
  Stop the server: press Ctrl+C in the terminal window.


重新打包（開發者）/ Rebuild (developers)
----------------------------------------
  Windows:  powershell -File scripts\build-portable.ps1
  macOS:    bash scripts/build-portable.sh
