# 啟動修復驗證紀錄

日期：2026-11-17。基準：d83e9c69c892a480853cd7f184f45b8fb6ee3412。

## 實作

- 舊 Safari 缺 createWritable 時，以約 1 KB 的專用 Worker 分塊同步寫入；處理部分寫入、flush／close、大小驗證及寫入中斷標記。
- native VFS 與 sql.js 共用完整版本＋SHA 檔名的匯入鎖；讀取、刪除只將 NotFoundError 視作缺檔。
- 失敗 Worker 在降級前清理；終止／解碼錯誤結束 pending；SQLite 初始化共用 Promise；關閉最多等待 1500ms。
- 重試保留有效副本，合併快速連按；reset 等待舊初始化與 tail 結束，過期結果不能覆蓋新就緒狀態；保留進度訂閱。
- 儲存錯誤保留 name／stage／fileName／cause 並提供具體文案；就緒閘保留「事業」真查詢與持久副本條件；修正窄屏按鈕與 sessionStorage 受限時的 shell 解鎖。
- PWA target 固定 iOS／Safari 16.4；更新 ADR、離線契約及 v1.1.2 修復說明。

## 已通過

| 檢查 | 結果 |
|---|---|
| TypeScript | tsconfig.app.json --noEmit 通過 |
| startup-storage-recovery | 實際儲存函式／Worker 的舊 API 備援、部分寫入、配額、鎖定、缺檔、損壞副本、跨後端匯入互斥通過 |
| 重試／初始化 | 實際 hook 的連按合併、過期結果隔離、實際初始化的先清理再降級、reset 排空舊連線、失敗清理完成前維持 single-flight 通過 |
| 就緒誠實 | 真查詢成功但持久化失敗時拒絕 Ready；有效副本成功；探針無結果拒絕 |
| 排序索引 | ranking-index-browser-self-check 通過，含離線新 realm、同 tag 換內容、Vite Worker 與 Workbox |
| 啟動進度 | startup-progress-self-check 的斷言通過 |
| PWA build | Vite production build、Workbox 及 check-pages-artifact.js 通過 |
| Portable build | Vite --mode portable 通過 |
| 專案接縫 | scripts/check_seams.py：89 項，通過，6 項略過 |
| Python smoke | 359 項通過，4 項略過（244 秒） |
| 真瀏覽器首次 | 本地 production artifact 在 Chromium 瀏覽器開啟；native sqlite3_open_v2 失敗後 sql.js 成功降級；查「事業」顯示 4707 項、包含「事業」 |
| 真瀏覽器離線重開 | 關閉原頁、停止本地 HTTP 伺服器，再建立全新頁面；由 SW／OPFS 復原並查得相同結果；不是沿用原頁 RAM |
| 詞庫不變 | lyrics.db SHA-256 仍為 5455bd70cf185d3d5be76c5edb514637545013de57d1dfc2e61a7aedcca461fc，與現有 Release 一致 |

## 執行環境與待完成項目

- Windows 此次 shell 的子程序無法以裸 node／npx 名稱解析執行檔，npm run build／self-check harness 因此未跑起。使用已安裝的 Node，直接執行相同 prebuild、Vite、產物檢查及 tsx 腳本完成上述檢查；prebuild 四個資料步驟皆命中既有內容 stamp。
- 既有 startup-progress 腳本輸出成功後會因 BroadcastChannel 保持開啟，該次程序已停止；排序索引與本次新增檢查均正常結束。不是新增修復造成的斷言失敗。
- iOS／iPadOS 16.4、17、18 的 Safari 與主畫面 PWA、macOS Safari／Firefox、低記憶體實機仍待驗；能力注入與 Chromium 結果不冒充這些實機驗收。
- 基本 A→B 更新已覆核：舊 SW 頁面仍可查，新頁面載入新版 index-525bfeyR.js 後仍有 4707 項結果；完整跨平台／雙分頁更新及窄屏／字體放大矩陣仍待覆核。本輪未改 SW activation 策略。

## 發佈狀態與既有版本

用戶已授權修復完成後覆蓋 v1.1.2 及 redeploy Pages。本機 dev 與遠端 dev 起始均為上述基準。

- 既有 Release：v1.1.2；release id 417216492；target d83e9c69c892a480853cd7f184f45b8fb6ee3412。
- Windows 舊資產 SHA-256：909a8dcc3fe4b2d4ef2f4e0341160835a996e6f82cc3bccfa1b79c45da3d0af8。
- macOS Intel 舊資產 SHA-256：d5afc9297a4b26113935f408aa00c3cf860cfc35d3d9cabb6640c537b96bc573。
- 本機 .git/index.lock 寫入受限，git checkout／pull 無法執行；本機 gh 對 GitHub 的 socket 連線受限。GitHub 連接已讀取遠端基準與 Release 資訊。
- 修復已透過 GitHub 連接推送 dev，建立 [PR #177](https://github.com/bill-iu/Canto-0243/pull/177)；CI 結果及合併狀態以 PR 即時頁為準。本機 Git HEAD 仍在起始基準，檔案保留修復；恢復 Git 寫入後須先核對與遠端內容一致，再同步 metadata，避免直接 reset --hard 丟棄工作樹內容。
- Chrome 的 GitHub Pages workflow 頁目前未登入，未能觸發手動部署。發佈資產及 Pages 尚未更換；不把本機 build 成功當成已上線。

後續須先確認 dev 修復提交及 CI，經 PR 合入 main，再從 main 刷新 v1.1.2 tag、重建並覆寫 Windows／macOS 程式資產（不覆寫詞庫），最後從 main dispatch pages.yml，target_tag=v1.1.2，並覆核線上搜尋及離線重開。
