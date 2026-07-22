# ADR-0070: macOS Desktop 主入口改薄 `.app`（退役 `.command`；單次 Gatekeeper）

修訂 [ADR-0068](./0068-desktop-pyapp-delivery.md) §9：創作者主路徑由 **`.command`** 改為 **`Canto-0243.app`**；正式套件不再附 `.command`。領域詞彙：[CONTEXT.md](../../CONTEXT.md) § **Desktop macOS 啟動**、**Desktop 套件**、**Desktop 安裝進度殼**。

## 決策

1. **主入口** — macOS Desktop tar 根目錄正式雙擊單位 = **`Canto-0243.app`**（內嵌既有 **Desktop 安裝進度殼** Mach-O）。**退役**正式渠道 `Canto-0243.command`。
2. **佈局（側車在旁）** — 解壓後 payload root = **`.app` 所在目錄**。同層：`lyrics.db`、`client/dist-portable`、wheel、指紋／README。**PyApp runtime** 放 **`Canto-0243.app/Contents/Resources/runtime/Canto-0243-runtime`**（唔再喺 payload 根 `runtime/` 作創作者可見獨立入口）。
3. **圖標** — `AppIcon.icns` SSOT = 產品 PWA **`icon-512.png`**（`client/public` → 建置生成 icns）。Bundle 顯示名／檔名維持 **`Canto-0243`**；「ONE搵韻」僅 splash／UI。
4. **搬移契約** — 創作者單位 = **成個解壓資料夾**；禁止只拖 `.app` 入 Applications 而留低側車（缺庫錯誤文案保留／加強）。
5. **單次 Gatekeeper（未 notarize）** — 建置 **ad-hoc 深簽** 成個 `.app`（`--deep`，含 runtime）。殼 **spawn runtime 前** 對 **payload root + `.app` bundle** 做 quarantine 清除（`xattr -cr` 等）。教學：**只**對 `.app` 做一次「仍要開啟」；runtime **唔**再要創作者 bypass。固定 `CFBundleIdentifier`（如 `com.canto0243.desktop`）避免每次 build 被當新 app。
6. **仍唔承諾** — 未 Developer ID + notarize 下雙擊零提示；無 Apple 開發者帳時 **唔**以 notarize 作 v1 必達。

## 理由

- 裸 Mach-O 難穩放 PWA 品牌圖標；`.app` + icns 係 Finder／Dock 正常路徑。
- 外層與 `runtime/` 各一隻下載 Mach-O 時，創作者常要 **兩次** Gatekeeper；runtime 收入 bundle + 殼先清 quarantine，先可以「只 bypass 一次」。
- 側車留 `.app` 旁保留 ADR-0068 換庫／程式-only 覆蓋心智，唔逼 B2 全塞 Resources。

## Considered

| 選項 | 結果 |
|------|------|
| 裸 `Canto-0243` 退役 `.command` | 拒作正式主路徑（圖標不穩） |
| 維持 `.command` 主路徑 | 拒（本次明確退役） |
| 全包入 `.app` Resources | 拒（更新／大 db 體感差） |
| runtime 仍在 `.app` 外 | 拒（第二閘風險） |
| 只靠 bundle、唔 xattr | 拒（Sequoia 仍常殺內層） |
| Notarize 作現行必達 | 拒（帳／流程；長遠可另 ADR） |

## Consequences

- 改 `build-desktop.sh`、shell `payload_root`／`inner_binary`、`payload_root.py` 猜測、`release`／README／macos-maintainer 教學。
- 硬閘／seams：入口名 `.app`、無 `.command`、runtime 在 Resources。
- Windows 仍根目錄 exe + `runtime\`；本 ADR 只收緊 **macOS**。
- 0068 §9 以本 ADR 為準；0068 正文應改指向此處以免分叉。
