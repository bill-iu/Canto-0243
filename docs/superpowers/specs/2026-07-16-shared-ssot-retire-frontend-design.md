# #86 第 (3) 段：共享 SSOT → `shared/`，刪 `frontend/`

**日期**：2026-07-16  
**狀態**：已實作（2026-07-17）· 落點 `shared/`  
**依據**：[#'86](https://github.com/bill-iu/Canto-0243/issues/86) Resolution 第 (3) 段；研究 [#85](https://github.com/bill-iu/Canto-0243/issues/85) R2

## 目標

- 共享 mjs／CSS／vendor 遷到 repo 根 **`shared/`**（扁平，保留檔名）。
- `client` alias／import、`check_seams`、guide manifest、codegen、相關 tests 全改指 `shared/`。
- **刪除整個 `frontend/`**；不准留長期 stub／re-export 相容層。
- 產品／發佈／測試路徑不再依賴 `frontend/`。

## 非目標

- 改查詢語意、雙端 explain、#87 引擎拆分。
- 重構共享模組內部 API（只搬家＋改路徑）。

## 步驟

1. `git mv frontend shared`
2. 刪 `shared/index.html`（舊 `/app` redirect stub；產品入口已是 `/app/`）
3. `main.py`：停掛 `/frontend` 靜態樹；可選保留 `GET /frontend/index.html` → **RedirectResponse `/app/`**（無檔案依賴）；favicon 後備改 `shared/favicon.ico`
4. 批量改路徑：`frontend/` → `shared/`（client、scripts、tests、CONTEXT／ADR 一句）
5. seam／esm／guide／portable＋PWA build 綠
6. 確認 `frontend/` 目錄不存在

## 綠燈

- CI 相關測試綠；`client` portable／PWA build 過。
- `rg frontend/` 在產品碼路徑無存活依賴（文件歷史敘述除外可漸清）。
- 無 `frontend/` → `shared/` re-export 層。
