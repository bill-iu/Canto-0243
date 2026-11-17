# 手機 PWA／電腦瀏覽器啟動修復實作計劃

- 日期：2026-11-17
- 狀態：待實作；本次只建立計劃，未修改產品程式、未完成實機驗收。
- 專案：D:\Canto-0243；工作分支：dev。
- 核對基準：d83e9c69c892a480853cd7f184f45b8fb6ee3412（本機 HEAD）。
- 需求來源：[啟動失敗分析對話](https://chatgpt.com/share/6afc09a1-b840-83e8-bcaa-63272ca63ed8)。

## 1. 要修復的行為與完成標準

手機在詞庫基本查詢已成功後，仍可能被「詞庫尚未寫入本機儲存」擋在就緒閘；電腦瀏覽器亦可能出現相同錯誤，但重新進入網址後恢復。本次要令舊 Safari 有可用的持久化寫入路徑，並修復開庫失敗、Worker 資源未釋放、初始化重疊與重試誤刪造成的問題。

完成須同時滿足：

1. iOS／iPadOS 16.4–18 的 Safari 與主畫面 PWA，首次準備成功後，關閉再於飛航模式冷啟，能查到「事業」及完成正常搜尋。
2. 桌面 Chrome／Edge／Firefox／Safari 注入暫時讀取或開庫失敗後，可在同頁重試恢復；失敗 Worker 不再持有資源，其他分頁的有效詞庫不被誤刪。
3. 就緒閘只在真查詢與本機復原條件均通過後解鎖；錯誤有具體原因及可行的下一步；窄屏重試按鈕尺寸正常。

此處將「iOS 18 以下」的本次支援目標具體定為 **iOS 16.4 起**，涵蓋 16.4、17、18；這是計劃的驗收範圍，並非已驗收承諾。iOS 15.x／16.0–16.3 不納入本輪支援保證；若要再下探，另驗證舊版 SyncAccessHandle 方法、編譯產物、WASM 與記憶體限制。缺少某版本實機時，其驗收項必須保留為待驗，不能以桌面裝置模擬替代。

範圍是手機及電腦的網站／PWA。Desktop／Portable 的 /app/ 與 Python 後端只作共用介面回歸，不修改其就緒語意。沿用 TypeScript 查詢引擎、sql.js 與 wa-sqlite；不引入 Pyodide、新資料庫或新的儲存框架。

## 2. 現有程式證據

以下是本機原始碼可確認的缺口；它們尚不能證明回報者當時命中了哪一項。分享對話所述故障注入是該次調查的結果，本次未重新執行，也未取得回報者的原始例外。

| 優先度 | 現況與定位 | 影響與修復方向 |
|---|---|---|
| P0 | [opfs-storage.ts](../../client/src/db/opfs-storage.ts) 的 opfsAvailable 只驗證 getDirectory；writeOpfsFile 直接呼叫 createWritable（約第 71 行） | 可讀 OPFS 不代表支援該寫入 API；補 Worker 同步寫入備援，按實際能力選路 |
| P0 | [init.ts](../../client/src/db/init.ts) 的 persistLexiconForOffline 捕捉例外後只 console.warn；[query.ts](../../client/src/db/query.ts) 的 validateOfflineReadiness 在探針後因缺 OPFS 副本拋通用錯誤 | 寫入根因丟失；保留持久化結果與原始錯誤，再讓就緒驗證決定是否放行 |
| P0 | init.ts 的 openLexiconDatabase 降級至 sql.js 前未處置失敗 Worker（約第 205 行） | 有殘留 Worker／資源的可能；先完成清理才降級 |
| P0 | [opfs-vfs-worker.ts](../../client/src/db/opfs-vfs-worker.ts) 的 ensureSqlite 只快取已完成實例（約第 57 行）；prewarm 與 init 可重疊 | 多次 WASM／VFS 初始化；共用進行中的 Promise，失敗後允許重試 |
| P0 | opfs-storage.ts 與 opfs-vfs-worker.ts 的 opfsFileSize 把所有例外轉成 0；readOpfsFile、removeOpfsFile 亦吞掉全部例外 | 鎖定／權限問題被當成不存在，可能觸發不必要重建；只將 NotFoundError 視為缺檔 |
| P0 | [opfs-lexicon.ts](../../client/src/db/opfs-lexicon.ts) 的 acceptExisting 可在 Web Lock 外刪檔；native VFS 匯入未使用同一個應用層匯入鎖 | 兩條寫入路徑與其他分頁未一致互斥；重建及刪檔納入同一把按檔名區分的鎖 |
| P0 | [useDB.ts](../../client/src/hooks/useDB.ts) 的 retryOfflineReady 約第 256 行先 reset，再無條件以 target.version 刪檔 | 真實 identity 已是 version + SHA；既可能刪錯，也可能刪除唯一可離線副本；先重開，只在證實損壞時精準重建 |
| P1 | [opfs-vfs-backend.ts](../../client/src/db/opfs-vfs-backend.ts) 的 prewarm 未接住 ask 的非同步拒絕；messageerror 只記錄；reset 終止 Worker 卻未 reject pending | 可出現未處理拒絕或永遠 pending 的請求；將 Worker 結束與請求結束收斂到同一清理路徑 |
| P1 | opfs-storage.ts 的首次 getDirectory 失敗會令 opfsUnavailable 黏住整個頁面生命週期；resetDatabase 未清此狀態 | 暫時故障不能靠同頁重試恢復；區分能力缺失與暫時存取失敗 |
| P1 | [shared/shell.css](../../shared/shell.css) 約第 1059 行窄屏全域 .primary-button 設 flex: 1；[ready-gate.css](../../shared/ready-gate.css) 僅調整該按鈕 margin | column flex 容器把重試按鈕拉長；限制搜尋列的規則或明確覆蓋閘內 flex |
| P2／待驗 | [vite.config.ts](../../client/vite.config.ts) 使用 autoUpdate、skipWaiting、clientsClaim；manifest 與詞庫／排序資產亦分別快取 | 更新期間的資產混用需驗證，現時未證實是本次事故根因；先做 A→B 更新測試，再按證據改策略 |

補充：現行 resolveDbBackendMode 在未指定環境變數時預設 opfs-vfs；[ADR-0045](../adr/0045-pwa-delivery-and-lexicon-channel.md) §1 仍描述 sql.js 預設，屬文件落差。實作時以現行行為作基線，本次不順手切換全站預設後端；同步修正文檔。

## 3. 平台與就緒契約

### 3.1 能力判斷

不能用 UA／iOS 版本字串決定寫入 API。逐層確認 secure context、getDirectory、取得目錄的結果，以及實際 FileHandle 上的 createWritable 或 Worker 內 createSyncAccessHandle。

WebKit 官方資料確認：Safari 26 才加入 File System WritableStream API；較早的 OPFS 與 Worker 同步控制代碼已存在，兩者不是同一項能力。Apple 的 Safari 16.4 說明亦記錄 SyncAccessHandle 方法統一為同步方法。因此選定 16.4 作本輪最低驗收版本，但仍須測試完整產物。

本機安裝的 Vite 預設 target 已包含 safari16.4／ios16.4。實作時核對並固定 PWA 產物的最低目標，亦檢查 Worker、Workbox 及第三方 WASM；不假設設定 build.target 就能補齊缺少的 Web API。

| 能力／結果 | 本輪處理 |
|---|---|
| OPFS VFS 能成功開庫 | 保持 native Worker 路徑，完成探針 |
| native VFS 失敗，但 createWritable 可用 | 完整清理 VFS Worker，再以 sql.js + async OPFS 寫入恢復 |
| createWritable 缺失，但 Worker 同步控制代碼可用 | sql.js + 小型專用儲存 Worker 寫入；不要求該 Worker 初始化 SQLite |
| OPFS API 缺失 | 沿用現有 sql.js／SW 復原路徑，驗證實際本機副本；未有副本不宣稱離線就緒 |
| 有 API 但發生鎖定、配額或存取錯誤 | 回報具體故障；不偽裝成 API 不支援或檔案不存在 |

### 3.2 保持就緒閘誠實

- 保留「事業」真查詢、詞庫完整性與本機復原條件；不以逾時、network bytes 已在 RAM 或略過驗證解鎖。
- 本輪先修好 OPFS 寫入，保留現行「OPFS 可用時必須有可用 OPFS 副本」的保守規則。不能為消除錯誤而直接改成 cache.any。
- [offline-readiness 契約](../../specs/001-pwa-offline-coexist/contracts/offline-readiness.md) 現寫雙路任一存在可作前置條件，而 query.ts 實際更嚴格。實作時將文件對齊此輪保留的規則；如果日後要讓有 OPFS 的裝置亦僅靠 SW 放行，另以實機冷啟證據修訂契約。
- tail 仍在閘後背景進行；不將詞庫字面集或音素倒排移到閘前。
- 關閉 Worker 的有限等待是資源回收措施；不是 ADR-0045 所禁止的「啟動逾時即放行」。

## 4. 按依賴順序實作

### P0-A：保留錯誤與釋放失敗資源

涉及 opfs-storage.ts、opfs-vfs-worker.ts、opfs-vfs-backend.ts、init.ts、lexicon-restore.ts，以及必要的就緒錯誤呈現。

1. 維持小型錯誤資料，至少保留 stage、name、message、backend、storage identity、是否可重試與 cause；Worker 回傳 name／stage，不能只剩 Error(message)。優先擴充現有錯誤，避免另建錯誤框架。
2. 兩處 opfsFileSize、讀檔與刪檔只對 NotFoundError 回傳缺檔；其他錯誤向上傳遞。大小探測優先使用不額外取得獨佔同步控制代碼的讀法；若仍被瀏覽器鎖住，回報 busy，不重建有效檔。
3. 把 Worker disposal 集中：拒絕所有 pending、清除監聽及 singleton、嘗試 close，最多等待 1500ms 後 terminate。清理可重入；error、messageerror、postMessage 同步失敗與主動 reset 都必須令對應 Promise 結束。
4. openLexiconDatabase 的 catch 必須 await disposal 後才降級；initializeDatabase 的失敗與 reset 同樣使用此路徑。把相關呼叫者改為可等待，避免先 terminate 再向死亡 Worker 發 close。
5. prewarm 的非同步拒絕要接住並保留診斷；直接選 sql.js／本 session 已跳過 VFS 時不啟動多餘的 VFS 預熱。
6. persistLexiconForOffline 回傳明確成功／失敗結果。就緒驗證使用本次持久化結果及可用副本資訊，保留具體原因，不再只反覆探測後拋「尚未寫入」。每次新初始化清掉舊結果，避免舊錯誤污染成功重試。

驗收：注入 native init 失敗後，降級前 Worker 已清理、pending 數為 0；鎖定與配額錯誤不會觸發缺檔重建；畫面／診斷能分辨缺 API、busy、quota、損壞及網路錯誤。

### P0-B：補齊舊 Safari 持久化寫入

涉及 opfs-storage.ts、opfs-lexicon.ts；新增一個只做 OPFS 檔案操作的小型 Worker 及最薄的呼叫封裝（檔名由實作者按現有結構選擇）。

1. writeOpfsFile 先檢查 handle.createWritable；缺失才走專用 Worker 的 createSyncAccessHandle。不能使用已失敗的 SQLite Worker 作唯一備援，否則 native 開庫與持久化會一起失效。
2. Worker 寫入用明確 offset，處理 write 回傳的部分寫入，最後 truncate 到正確大小、flush，並在 finally 關閉控制代碼。async writable 失敗時亦要 abort／關閉，保留原始錯誤。
3. sql.js 還要使用原 bytes 開庫，不能 transfer 原始 ArrayBuffer 令它 detached。沿用約 4 MiB 分塊、一次只送一塊並等確認；transfer 當次切片，避免複製整份詞庫或再次下載。結束後終止臨時 Worker。
4. 成功必須等寫入、flush／close 與重新讀取檔案大小完成；不能把傳送訊息完成當作落地完成。沿用 manifest 的大小／SHA 完整性檢查，不以相同大小等同相同內容。
5. 中斷寫入不能在下次被當成完整詞庫。採最小的寫入中標記或等效機制，涵蓋兩條 OPFS 匯入路徑；標記僅在成功驗證完成後移除。後續恢復先取得匯入鎖，避免把另一分頁正在下載的檔當作殘檔。
6. 不依賴舊 Safari 未保證的 move／rename API；不預設 OPFS 寫入具原子性。只清本次已證實未完成的目標，不動既有其他 identity。

驗收：模擬 getDirectory 可用、createWritable 缺失、同步控制代碼可用，寫入及 read-back 成功；中途拋錯仍釋放 handle；原 bytes 可供 sql.js 使用；低記憶體 iPhone 不因整庫重複複製而被系統終止。

### P0-C：初始化與跨分頁匯入互斥

1. ensureSqlite 快取進行中的 Promise；prewarm 與 init 共用同一結果，失敗時清 Promise 讓下一次可重試。保留已完成實例的快徑。
2. 將同一 Worker 的開庫／關庫生命週期按順序處理，查詢只對完成初始化的有效 DB 執行；不用為本次修復重寫整個查詢排程器。
3. OPFS VFS 匯入與 sql.js 持久化都使用同一把按完整 fileName 區分的 Web Lock。檢查後需刪檔、建立殼、下載、寫入及完成標記均在鎖內再次確認；不要在取得鎖前刪檔。
4. 不在應用層匯入鎖內重複取得同一把鎖；一般查詢沿用 VFS 的協作機制。測試兩路徑交叉進入，避免引入巢狀鎖死。
5. 能力缺失可快取；getDirectory 的一次暫時拒絕不能永久設成 unavailable。明確重試時重設暫時探測狀態。
6. 缺 Web Locks 的裝置，保留單頁互斥及檔案鎖衝突提示，禁止不安全的併發覆寫。它們不因此取得尚未驗證的多分頁支援承諾。

驗收：prewarm + init 同時觸發只建立一次 WASM／VFS；首次失敗後第二次可成功；兩分頁同 identity 匯入只寫入一次；busy 不會被轉成「檔案不存在」。

### P0-D：令「重試」成為安全的同頁復原

涉及 useDB.ts、init.ts、opfs-lexicon.ts、lexicon-restore.ts、ready-gate.tsx。

1. 在 retry 開始前保留本次 LexiconTarget、完整 storage identity 與失敗原因；處置舊初始化及 tail，再清理 DB／Worker，最後開新初始化。舊工作完成後不能回寫新一輪狀態；用最小 attempt token／既有取消機制處理。
2. retry 本身共用一個進行中的 Promise；連按按鈕只執行一次，按鈕在 preparing 時停用。同步更新必要的 refs，避免 React 舊 statusRef／isValidatedRef 令 initialize 誤判為已 ready。
3. 一般 retry 只重新開庫、探測與驗證，不先刪檔。配額／權限／busy 有對應指引；busy 可短暫重開一次，仍失敗則提示關閉其他 Canto 分頁後重試，不無限重試。
4. 只有大小／SHA／schema 不符或確認寫入未完成時才重建。使用 lexiconStorageVersion(target) → lexiconOpfsFileName，涵蓋該 identity 的 journal／wal 與完成標記；不再傳 target.version 當作完整 key。
5. 需要清除損壞的 HTTP 快取時，鎖定該次 fetchUrl／dbUrl 的精確 identity。避免 ignoreSearch 誤刪其他 SHA 的有效快取；不要順手清空全站 Cache、OPFS、localStorage 或 Service Worker。
6. 重新確認實際快取狀態，重新執行真查詢及離線驗證後解鎖。保留句稿、使用者偏好與與本次故障無關的資料。

驗收：同一版本不同 SHA 清對目標；有效離線副本在暫時失敗後仍存在；快速連按不產生雙初始化；reset 前的延遲結果無法覆蓋成功的新嘗試；不用重新輸入網址即可恢復。

### P1：可讀錯誤與窄屏按鈕

1. 創作者文案只講可執行的下一步：空間不足→釋放儲存空間；暫時被使用→關閉其他分頁再試；離線且無副本→連網準備一次；儲存受限→改用一般瀏覽模式／檢查網站儲存設定。
2. 原始 name、stage、backend、identity、restore source 與 Worker pending 數放入現有 resume-debug／Console 診斷，不將技術堆疊塞進主要畫面；不新增遠端遙測。ReadyGate 的 sessionStorage 標記若被拒絕，亦不能阻止 shell 解鎖。
3. 將窄屏 flex: 1 限縮至原本需要伸展的搜尋容器；閘內按鈕明確 flex: 0 0 auto，保留觸控高度、焦點樣式與換行空間。
4. 測試 320／375／390／768px、橫向及 200% 字體；確認錯誤訊息可讀、按鈕無長條伸展、鍵盤可操作，reduced-motion 下亦能進出就緒閘。

### P2：更新與快取交替驗證

先用 production build 重現舊頁 A → 新 SW／詞庫 B 的更新，不直接改 skipWaiting 或全站快取策略。

- 驗證頁面、Worker JS、WASM、ranking-index、manifest 與詞庫 identity 的相容組合；同 tag 換 SHA 亦要測。
- 單頁、雙頁、切後台再回來、第一次 SW 尚未控制頁面、飛航重開都要覆蓋。
- 若發現自動 activation 造成混版，再選最小修正，例如延後到下一次完整導覽才啟用更新；保持編輯中的句稿可恢復，禁止 controllerchange 自動 reload 造成資料遺失。
- 網路失敗與 ranking-index 暫時不可取要保留對應錯誤，不能全部改判成 OPFS 問題；重用已存在的 ranking-index-browser self-check。
- 清理舊快取不得刪除其他仍開啟分頁必要的資產；新版本完成就緒前保留可恢復的舊副本。

若驗證未發現此類缺陷，記錄結果即可，不為假設問題加入版本協調框架。

## 5. 最小自動化檢查

以現有 node:assert、tsx／esbuild 與 self-check harness 實作一個 startup-storage-recovery-self-check，必要時把瀏覽器情境獨立成同組檢查。登記 self-check-manifest.json 的 ci／pwa 標籤；不要新增測試框架或跑與本次無關的全量語料檢查。

| 組別 | 必須注入的故障／時序 | 必須觀察的結果 |
|---|---|---|
| 舊 Safari | 有 getDirectory、無 createWritable、有 Worker sync handle | 持久化成功，真查詢與 read-back 通過，原 bytes 未 detached |
| 寫入完整性 | 部分 write、quota、中途終止、已有較長檔 | 正確補寫／truncate；控制代碼關閉；未完成副本不被接受 |
| 讀檔分類 | NotFoundError、NotAllowedError、鎖定類錯誤 | 只有 NotFound 算缺檔；其他保留原因，不刪有效副本 |
| Worker 清理 | init 拒絕、error、messageerror、postMessage 拋錯、close 不回應 | 所有請求有結局、pending=0、舊 Worker 已終止，降級先後次序正確 |
| 初始化 | prewarm 與 init 重疊；第一次 Factory 失敗 | 同時只一個初始化；失敗後可再試，無 unhandled rejection |
| 重試 | 連按、舊 init 延遲完成、舊 tail 回寫、sessionStorage 拒絕 | 只有新 attempt 可更新狀態；不重複開庫；shell 正常解鎖 |
| identity | 同版不同 SHA、相同大小損壞、gz／plain 兩個 URL | 只處理目標壞副本；有效其他 identity 仍可恢復 |
| 跨分頁 | VFS 匯入與 sql.js 備援同時進入；另一頁正在查詢 | 同 identity 只匯入一次；鎖衝突不觸發覆寫；兩頁最終可查 |
| 就緒誠實 | 查詢成功但無持久副本；僅有錯版本快取 | 不標 Ready；有效本機副本＋探針成功才解鎖 |

建議執行順序（在 client 目錄）：

```powershell
node scripts/self-check-harness.mjs --id startup-storage-recovery
node scripts/self-check-harness.mjs --id ranking-index-browser --id startup-progress
npm run build
npm run build:portable
```

第一行是本計劃要求新增的檢查；檔案及 ID 建立後才可執行。startup-progress 由 harness 自動發現。若改到共用錯誤型別／hooks，再執行相應 ci 標籤檢查；不以建置成功替代 Worker 與離線實測。

## 6. 實機及真瀏覽器驗收表

| 環境 | 在線首次／升級 | 強制 sql.js 備援 | 完全關閉後飛航冷啟 | 同頁重試／多頁 |
|---|---|---|---|---|
| iOS／iPadOS 16.4 Safari + 主畫面 PWA | 必測 | 必測 | 必測 | 必測 |
| iOS／iPadOS 17.x Safari + 主畫面 PWA | 必測 | 必測 | 必測 | 必測 |
| iOS／iPadOS 18.x Safari + 主畫面 PWA | 必測 | 必測 | 必測 | 必測 |
| Safari 26 或更新版本，含 iOS PWA | 回歸 | 必測 async writer | 必測 | 必測 |
| Windows Chrome／Edge 目前穩定版 | 必測 | 必測 | 必測 | 必測雙頁 |
| Windows Firefox 目前穩定版 | 必測 | 必測 | 必測 | 必測雙頁 |
| macOS Safari 18.x／26+ | 必測 | 必測 | 必測 | 必測雙頁 |

每次記錄裝置／OS／瀏覽器精確版本、build commit、lexicon version／SHA、實際 backend、寫入路徑與結果。主畫面 PWA 與 Safari 頁面分別驗證，不假設它們共用同一個儲存環境。

必要旅程：

1. 使用獨立測試 origin／測試 profile，首次準備 → Ready → 查「事業」及一個正常 0243 查詢 → 確認非空結果。
2. 完全關閉 PWA／頁面後斷網，再冷啟；確認不是原來 RAM 仍存活的熱啟動，且標誌／指定字體可用。
3. 用測試開關令 native VFS 開庫失敗，確認失敗 Worker 被清理，再以 sql.js 路徑重複以上旅程。
4. 兩頁同時首次初始化；一頁持有檔案資源時另一頁注入讀取故障，重試後兩頁均可查，檔案與句稿仍在。
5. 分別測 OPFS 單路存在、SW 單路存在、兩路皆缺、低配額、儲存權限受限；結果必須符合 §3.2，失敗時不誤報 Ready。
6. A→B 更新、同版換 SHA、背景返回與關閉後重開；不要求回報者手動清網站資料或重裝 PWA 才恢復。

所有清除／損壞注入只在測試環境，不拿使用者現有句稿或唯一離線副本做測試。

## 7. 文件、提交與發佈

- 實作時更新 ADR-0045、docs/pwa.md 與 offline-readiness 契約，明訂最低驗收版本、能力選路、真實預設 backend、重試及離線限制；不再修改已被 ADR-0045 取代的 stub 當作權威。
- 建議分三個可驗收提交：① 錯誤保留＋Worker 清理／初始化互斥；② 舊 Safari 寫入＋安全重試／互斥；③ UI、回歸檢查與文件。P2 只有重現才另開修正提交。
- 依 repo 規則先 checkout dev、pull origin dev；全程 dev，文字 LF，不修改 skills-lock.json。提交／push dev 後提供 diff 與驗證結果；合入 main 需用戶確認，再建立 dev→main PR。
- 本次建立計劃時 dev 工作目錄原本乾淨；checkout／pull 的第一步因 .git/index.lock 寫入權限被拒而未完成，故上述 SHA 僅代表本機基準，未宣稱已同步遠端。實作者須先在可寫 Git metadata 的工作環境完成同步並重核 diff。
- 部署前遵守 docs/pwa.md 與 git-workflow：確認 dev 已合入 main，從最新 main 建 production artifact；此次不因程式修復重建詞庫或覆寫 Release 的 lyrics.db。
- 發佈前保存上一份已驗收 Pages 產物及 build／詞庫 identity；出現回歸用已驗收版本恢復。不要把清空使用者網站儲存當作回滾方案。

## 8. 交給實作 agent 的工作指令

> 先讀本計劃及 AGENTS.md，核對 dev 最新狀態。按 P0-A → P0-B → P0-C → P0-D → P1 完成；先處理共享函式與所有呼叫者，保持最小改動。保留「事業」真查詢及持久副本的就緒條件，禁止靠逾時放行、全面刪快取或重載迴圈掩蓋故障。以 iOS 16.4／17／18 的 Safari 和主畫面 PWA 為向下相容驗收目標。P2 先驗證再決定是否修改。完成最小故障注入、production build、Portable 回歸後 commit＋push dev；回報已通過與待實機項目，未獲確認不合 main、不發佈。

## 9. 外部技術依據

- [WebKit：Safari 26.0 新功能](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/#web-api)：File System WritableStream API 的支援時間。
- [WebKit：OPFS 與 Worker 同步控制代碼](https://webkit.org/blog/12257/the-file-system-access-api-with-origin-private-file-system/)：OPFS、getFile 與 Worker-only 同步存取的區別。這是歷史介紹，不以其當年的私密瀏覽限制代替現行能力探測。
- [Apple：Safari 16.4 Release Notes](https://developer.apple.com/documentation/safari-release-notes/safari-16_4-release-notes)：FileSystemSyncAccessHandle 方法同步化與寫入配額修正。

外部文件支撐 API 判斷；回報者事故根因仍需實際錯誤與上述驗收結果確認。
