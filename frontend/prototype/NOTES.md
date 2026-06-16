# PROTOTYPE — 查詢分頁定案 A（Open Design）

**問題：** 頁內多查詢分頁（Variant A），完全貼合 Open Design；定案後 TDD 接入 `index.html`。

**狀態：** v3 — [adamschwartz/chrome-tabs](https://github.com/adamschwartz/chrome-tabs) + L1 分層 header。

## Open Design 視覺決策（不寫入 CONTEXT.md）

| 項目 | 定案 |
|------|------|
| Tab 元件 | **chrome-tabs**（MIT）SVG 幾何 + layout + bottom-bar |
| Header | **L1** 品牌列正式 header 底；僅 tabdeck strip 底 |
| 無縫 | `chrome-tabs-bottom-bar` + 作用中 fill = `--bg` |
| 關閉鈕 | **A1** 非作用中 hover 才顯示 |
| 品牌 | 視窗左上角；tab 從 `--brand-rail` 起 |

## 檔案

| 檔案 | 說明 |
|------|------|
| `chrome-tabs.css` | 上游樣式（token 化） |
| `chrome-tabs-layout.js` | 上游 layout（無 Draggabilly） |
| `query-tabs.css` | header 分層 + Open Design token |
| `query-tabs.html` | 狀態機 + chrome-tabs 整合 |

## 一鍵開啟

```bash
./start.sh
```

瀏覽器：http://127.0.0.1:8000/prototype

## 試玩清單

1. header：品牌列暖紙底、tab 列單獨 strip 底（非整條大色帶）
2. 作用中 tab 底部 bottom-bar 與 hero `--bg` 無斷層
3. tab 分隔線可見；overlap 僅 1px（上游預設）
4. 切換／F5／Alt+N/W／中鍵關閉

## Verdict（試完後填）

- [ ] 視覺／操作 OK，可 TDD 接入 index.html
- [ ] 需調整：…
