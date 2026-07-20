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

2. 雙擊 Canto-0243.exe（推薦；無 cmd 視窗）
   Double-click Canto-0243.exe (recommended; no console window).

   進階／疑難排解：雙擊 START.bat
   Advanced / troubleshooting: double-click START.bat.

3. 無需安裝 Python；瀏覽器會自動開啟搜尋頁
   No Python install required; your browser opens the search page.

4. 退出：查韻介面 header「退出 Canto-0243」
   Exit: use “退出 Canto-0243” in the app header (portable only).


macOS（免安裝）
---------------
1. 依晶片下載對應 tar 並解壓（Apple Silicon → arm64；Intel → x86_64）
   Download the matching tar for your Mac (Apple Silicon → arm64; Intel → x86_64):
     canto-0243-portable-macos-arm64.tar.gz
     canto-0243-portable-macos-x86_64.tar.gz

2. 進入解壓後的 canto-0243-portable 資料夾
   Open the extracted canto-0243-portable folder.

3. 雙擊 Canto-0243.command 啟動（會開啟 Terminal；無需安裝 Python）
   Double-click Canto-0243.command (opens Terminal; no Python install).

   若 macOS 顯示無法驗證／無法開啟：
   If Gatekeeper blocks the script:
     • 對 Canto-0243.command：右鍵（或 Control+點擊）→「打開」→ 確認
       Right-click (or Control-click) Canto-0243.command → Open → confirm (once).
     • Sequoia 15（只有「完成／移至垃圾桶」、無「打開」）：先按「完成」，再到
       系統設定 → 隱私與安全性 → 向下捲動 →「仍要開啟」（Canto-0243）→ 再雙擊
       Sequoia 15 (Done / Move to Trash only): tap Done, then System Settings →
       Privacy & Security → scroll down → Open Anyway (Canto-0243) → double-click again.

   進階：同資料夾內 START.sh 亦可於 Terminal 手動執行
   Advanced: you can also run ./START.sh from Terminal in the same folder.


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
- client/dist-portable/ — 網頁介面（PORTABLE_HOST 建置產物）/ web UI (PORTABLE_HOST build)
- app/、main.py — 後端 API / backend API


疑難排解 / Troubleshooting
--------------------------
- 8000 埠被佔用：編輯 .env.local，修改 PORT
  Port 8000 in use: edit .env.local and change PORT.

- 「找不到內建執行環境」：請重新下載完整 Release 套件
  "Bundled runtime missing": re-download the full release package.

- macOS Gatekeeper：確認 tar 與晶片相符（arm64 / x86_64）；被擋時右鍵→「打開」，或 Sequoia 15：系統設定→隱私與安全性→仍要開啟
  macOS Gatekeeper: match tar to chip; right-click → Open, or Sequoia 15: System Settings → Privacy & Security → Open Anyway

- 關閉服務：查韻介面 header「退出 Canto-0243」；或工作管理員結束 pythonw.exe
  Stop: use “退出 Canto-0243” in the app header, or end pythonw.exe in Task Manager.


重新打包（開發者）/ Rebuild (developers)
----------------------------------------
  先建 UI：cd client && npm run build:portable（須成功；bundle 腳本會檢查 index.html）
  Build UI first: cd client && npm run build:portable (must succeed; bundle scripts check index.html)

  Windows:  powershell -ExecutionPolicy Bypass -File scripts\build-portable.ps1
  macOS:    bash scripts/build-portable.sh
