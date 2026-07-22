Canto-0243 — Desktop 免安裝離線版（ADR-0068）
Canto-0243 Cantonese Rhyme Workbench — Desktop offline edition
(Windows / macOS / Linux*)
================================================================

* Linux 仍須本機 Python 3.11+（不列免安裝承諾）。


首次啟動 / First run
--------------------
首次執行需要網路：下載 CPython 3.11 並安裝應用程式環境（只需一次）。
其後可完全離線使用。

First launch needs internet (downloads CPython 3.11 and installs the app env once).
Later launches work fully offline.

無需預先安裝 Python / pip / uv。
You do not need Python pre-installed.


Windows
-------
1. 解壓縮整個資料夾
   Extract the entire folder.

2. **只**雙擊 **Canto-0243.exe**（唯一創作者入口；首次會顯示安裝進度殼）
   Double-click **Canto-0243.exe** only (sole creator entry; first run shows setup splash).
   套件**不**附 START.bat。
   No START.bat is shipped.

   （維護者）repo 內 portable/START.bat 與 scripts/portable_venv* 為 **legacy／dev**
   （舊 venv.pack 運送，ADR-0067）；非正式 Release 渠道。正式建置見 scripts/build-desktop.*
   （PyApp，ADR-0068）。跑 legacy seams：CANTO_SEAMS_LEGACY=1。

3. 瀏覽器會自動開啟查韻介面
   Your browser opens the search UI.

4. 退出：預設關閉最後一個查韻分頁即停本機服務（刷新唔停）；選單可改設定
   Exit: by default closing the last product tab stops the local server (reload-safe).


macOS
-----
1. 依晶片下載對應 tar 並解壓（Apple Silicon → arm64；Intel → x86_64）
   Download the matching tar (Apple Silicon → arm64; Intel → x86_64):
     canto-0243-desktop-macos-arm64.tar.gz
     canto-0243-desktop-macos-x86_64.tar.gz

2. 進入解壓後的 canto-0243-desktop 資料夾
   Open the extracted canto-0243-desktop folder.

3. 雙擊 Canto-0243.command 啟動（會開啟 Terminal）
   Double-click Canto-0243.command (opens Terminal).

   若 Gatekeeper 阻擋：
   If blocked:
     • 右鍵 Canto-0243.command →「打開」→ 確認
       Right-click → Open → confirm (once).
     • Sequoia：系統設定 → 隱私與安全性 →「仍要開啟」
       System Settings → Privacy & Security → Open Anyway.

   未 notarize 的 .app 不是現行必用入口；請用 .command。
   Unsigned .app is not the supported path; use .command.


更新 / Updates
--------------
有新正式版時，介面／終端會提示。請下載新 zip／tar，關閉程式後解壓覆蓋。
不會自動覆蓋本機檔案。

When a new stable release is available you will see a notice. Download the new
package and extract over the old folder after quitting. No silent auto-update.


內容 / Contents
---------------
- Canto-0243.exe — 外層安裝進度殼（創作者入口；套件根目錄唯一 .exe）
- runtime/Canto-0243-runtime.exe — 內層 PyApp（子目錄；由殼啟動）
- *.whl — 應用程式包（首次由 runtime 安裝）/ app wheel
- lyrics.db — 主詞庫
- data/ — 靜態詞典資料
- client/dist-portable/ — 產品 UI
- （無 START.bat；根目錄唔放 runtime.exe）


疑難排解 / Troubleshooting
--------------------------
- 首次無網：請連網後再開一次（錯誤應清楚說明）
  No network on first run: connect and try again.

- 8000 埠被佔用：編輯 .env.local，修改 PORT
  Port 8000 in use: edit .env.local and change PORT.

- 關閉服務：介面「退出 Canto-0243」；或工作管理員結束相關 python 進程
  Stop: in-app Exit, or end python processes in Task Manager.


重新打包（開發者）/ Rebuild
--------------------------
  cd client && npm run build:portable
  Windows:  powershell -ExecutionPolicy Bypass -File scripts\build-desktop.ps1
  macOS:    bash scripts/build-desktop.sh
  （需要 Rust/cargo）
