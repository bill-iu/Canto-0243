# ADR-0067: Portable venv pack transport (fewer zip entries)

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § **免安裝交付**、**Portable 套件**、**venv 運送包**。  
原則層： [ADR-0044](./0044-portable-delivery-and-release.md) §1／§1b（runtime 仍係可搬移 venv；本 ADR 只鎖**運送**）。  
指紋： [ADR-0059](./0059-portable-release-fingerprint-update-notice.md)（`package_digest`／`file_count` 以**運送狀態**為準）。

## 決策

1. **運送** — Windows portable 建置預設把整棵 `venv/`（含 `python-home`）打成套件根目錄單一 **`venv.pack`**（zip）。Zip／資料夾在 **首次啟動前** 只有少數 entry，唔再運送數千小檔。
2. **Runtime** — 首次 START／`Canto-0243.exe` **extract-once** 到 `venv/`，之後行為同 ADR-0044 展開 venv（`pyvenv.cfg` home patch、self-check 語意不變）。
3. **完成判定** — `venv/.portable-venv-extracted`（JSON：至少 `pack_sha256`）。成功順序：**完整解壓 → 驗證 `Scripts/python.exe`（及 Win `python-home/python.exe`）→ 寫 marker → 刪 `venv.pack`**。
4. **半展開** — 失敗則刪 `venv/`（保留 `venv.pack`）、釋放 lock，可再試；自動重試有限次後報錯。壞 venv 且 **已無 pack** ⇒ 創作者重新下載整包（本 slice 唔留 pack 作重建源）。
5. **並發** — `venv/.portable-venv-extract.lock`；第二實例等或退出並提示。
6. **進度** — console 人話 + 簡單 `%`／檔數（`START.bat`／ensure 路徑）；唔做 MessageBox 進度窗。
7. **Build rollback** — `build-portable.ps1 -NoVenvPack` 維持舊式展開樹（對照／除錯）。
8. **Manifest** — build 在 **pack 後** stamp：`file_count`／`package_digest` = 運送樹（含 `venv.pack`、無展開 `venv/`）。可選欄：`venv_pack_sha256`、`venv_unpacked_file_count`（唔入 0059 指紋四件套）。
9. **平台** — Windows 先；macOS 保持展開 venv，直至對稱接線（接口／命名預留同一 `venv.pack` 契約）。
10. **拒** — 創作者自行 PyInstaller／自建 pack；用 full-app onefile 取代 venv runtime；自動覆蓋更新（仍 ADR-0059）。

## 理由

C11 phase 1 已 slim denylist；檔案數痛點仍在運送時嘅 venv 小檔風暴。Pack 運送 + extract-once 直接削減 unzip entry，又保留已驗證嘅 venv／`python-home` 模型。成功後刪 pack 換磁碟（接受無法本地只靠 pack 重建）。

## Considered

| Option | Result |
|--------|--------|
| Full-app PyInstaller 取代 venv | 拒 — DLL／除錯／同 0044 衝突大 |
| Zip 只改壓縮、仍展開樹 | 拒 — on-disk／unzip entry 主 KPI 無解 |
| 成功後保留 pack | 拒於本 slice（grill **B**）— 省空間優先；可後加 opt-in |
| Extract 去 `%LOCALAPPDATA%` | 拒於本 slice（grill 痛點 **A**） |
| Win+Mac 同 PR | 拒 — Mac follow-up |

## Consequences

- 首次啟動可能明顯較慢；文件／console 必須說明。
- 異路徑 smoke 要覆蓋：unpack zip → ensure extract → patch home → launch。
- `-NoVenvPack` 產物 file_count 會同預設 pack 差一個數量級；發佈應用預設 pack。
- `package_digest` 建置時間因少檔而下降（對 0059 有利）。
