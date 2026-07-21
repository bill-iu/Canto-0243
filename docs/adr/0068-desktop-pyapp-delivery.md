# ADR-0068: Desktop 套件以 PyApp 交付（正名取代 Portable 運送）

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § **免安裝交付**、**Desktop 套件**、**本機服務退出**、**Desktop macOS 啟動**、**套件發佈指紋**、**套件更新提示**、**venv 運送包**。

取代創作者交付層之運送／runtime 模型：[ADR-0044](./0044-portable-delivery-and-release.md) §1／§1b 之 **venv 打包運送**、[ADR-0067](./0067-portable-venv-pack-transport.md) 全份（運送層）。**保留** 0044 §3 啟動編排精神（`local_launch` 單點）、§4 詞庫預暖、§5 分渠道發佈骨架；[ADR-0059](./0059-portable-release-fingerprint-update-notice.md) 指紋＋人手覆蓋（產品名改稱 Desktop）。技術選型 **只走 PyApp**（唔再開 Tauri／Briefcase／full-app PyInstaller onefile）。

## 決策

1. **正名** — 創作者可見與發佈資產用 **Desktop**（舊 **Portable**）。內部路徑／識別子（如 `dist-portable`、`portable/`、`PORTABLE_HOST`）可暫留至清理 PR。
2. **免安裝語意** — 創作者唔使預裝 Python／pip／uv。**首次啟動可需網路**建立 PyApp 管理之執行環境；**其後離線**查韻。正式包**唔**預設附 wheels／離線 bootstrap 物料；無網首次須失敗得清楚。
3. **運送形態** — 平台 **PyApp launcher** ＋ **可安裝應用包（wheel）** ＋ **側車**（`lyrics.db`、產品 UI、data 等跟解壓目錄／launcher 旁）。**淘汰** 套件內整棵可搬移 `venv/`／`venv.pack` 作正式渠道（legacy 建置開關可短期對照，**唔**上正式 Release）。
4. **Wheel 邊界** — wheel 含查詢服務、FastAPI app、`local_launch` 編排與 runtime 依賴宣告；**唔**把詞庫／UI 打入 wheel 當唯一來源；**唔**以側車迷你 repo 充當安裝後唯一 code。
5. **Python** — 釘 **CPython 3.11**（`PYAPP_PYTHON_VERSION=3.11`）。PyApp 使用自管發行版，**唔**偵測或改用系統已裝之 3.12／其他版本。
6. **入口** — 產品主路徑＝`local_launch` **GUI 語意**（silent、可重用已跑 backend、detach 後端）。**A1**：launcher 可結束，服務常駐直至明確退出。
7. **本機服務退出** — **預設**關閉最後一個本機產品瀏覽器分頁時 `POST /shutdown`（產品內查詢分頁＝多工作區；**reload 唔停服**）。進階可改「關分頁唔停」並顯示選單「停止本機服務」。**唔**把 F5 當退出。
8. **更新** — **現行**維持 ADR-0059：指紋提示 ＋ 人手解壓覆蓋成個 Desktop 套件；**關閉** PyApp self-update 作產品預設。整包自動同步僅長遠目標。
9. **macOS** — 創作者主路徑 **`.command`**（Gatekeeper 教學針對它）。`.app` **不放棄**，作日後修復／研究；**唔**以未 notarize 之 `.app` 雙擊作現行必達承諾。
10. **分渠道** — Windows zip 在 Windows 建；macOS tar 在對應架構 macOS 建；Linux 仍不承諾雙擊免安裝。Release 資產名／文件用 desktop 語意。**Windows Desktop 套件只交付 `.exe`（外層殼 + runtime）**，**唔**附 `START.bat`；repo 內 `portable/START.bat` 僅供 legacy／開發，唔入正式 Desktop zip。
11. **Runtime 依賴（瘦）** — Desktop wheel／`requirements.txt` **必裝**：FastAPI 棧、SQLAlchemy、dotenv、**OpenCC**（`to_traditional`／近反義字面正規化）。**唔**必裝 `pycantonese`／`pyjyutping`／`pyyaml`（建庫標音與維護腳本；見 `requirements-dev.txt` 或 `pip install -e ".[ingest]"`）。查詢路徑新詞注入走 rime／靜態索引／DB，唔即時 call pycantonese。
12. **Desktop 安裝進度殼**（grill）— 首次雙擊用**薄外層殼**（Rust + **wry/tao**，共用靜態 HTML splash；Win+Mac 同 milestone 兩 target），分階標籤＋不定 bar 顯示 PyApp bootstrap（下 CPython／建 env／裝 wheel）；**唔**假 %；**唔**等同產品 **就緒閘**。Env 已就緒則跳過殼。內層仍係 PyApp；**拒**用產品 React 閘包住無 Python 階段；**拒**只靠 fork PyApp 當唯一品牌 UI。

## 理由

- 舊痛點：建置拷貝整棵 venv、zip 數千小檔、運送／刪除慢；macOS 無開發者帳下 `.app` 亦難當可靠入口。
- PyApp：細 launcher、首次自管 Python＋裝 wheel、其後快啟；原生擴展走真 Python。
- 側車保留 **套件發佈指紋**（tag＋digest＋db sha）與「套件內建庫」心智；人手覆蓋避免 code／db 半更新撕裂。
- detach＋顯式退出對齊而家 Windows GUI 行為，避免誤以為「關瀏覽器＝關後端」。

## Considered（摘要）

| 選項 | 結果 |
|------|------|
| 首次零網（附 wheels／每包 embed 發行版） | 拒作主渠道（抵消瘦身）；可後加離線大包 |
| 詞庫／UI 全入 wheel | 拒（程式-only 刷新笨、指紋模型彆扭） |
| PyApp self-update／全自動換包 | 拒作現行；長遠可再 ADR |
| 關分頁即停服 | 拒（刷新／多 tab／誤關） |
| 雙軌長期 venv＋Desktop | 拒；正式只 Desktop/PyApp |
| 釘 3.12 或跟系統 Python | 拒；釘 3.11 自管發行版 |
| Tauri／Briefcase／full-app onefile | 拒（handoff 鎖定 PyApp only） |
| macOS 只靠修 `.app` 當 KPI | 拒作今次必達；主路徑 `.command` |
| Desktop 必裝 pycantonese／pyjyutping | 拒（code 僅 ingest／維護腳本；誤標 runtime） |
| Desktop 去掉 OpenCC | 拒（簡→港繁／近反義正規化產品契約） |
| 產品 ReadyGate 直接包 PyApp 下載 | 拒（閘要 app 已起；bootstrap 在 Python 前） |
| Bootstrap 假精確 % | 拒（PyApp 無穩定公開比例 API） |
| 只 Win 殼、Mac 永久無殼 | 拒作目標；本決策 Win+Mac 同 milestone（wry） |

## Consequences

- 新增 `pyproject.toml`（或等價）可安裝包與 entry point；建置改 PyApp（維護者要 Rust／cargo 工具鏈）。
- 廢止正式渠道對 `portable_venv`／`venv.pack`／PyInstaller GUI launcher 的依賴；0044 §1／0067 作歷史。
- 首次啟動 UX：bootstrap 進度／無網錯誤文案；文件改 Desktop 名與「首次可需網」。
- 0059／release 手冊用語 Portable→Desktop；指紋仍三人套、換庫仍須重打套件。
- 實作里程碑後 dev `start.sh` 可繼續本機 venv；與創作者 Desktop 渠道分開。
