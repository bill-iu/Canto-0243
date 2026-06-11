# 0243 離線押韻字典 - 專案總覽

**版本日期**：2026-06-11  
**開發者**：Wizgo  
**目標**：提供一個可離線使用的粵語押韻搜尋工具，支援 0243 / 02493 編碼、粵拼、等號韻與相關詞查詢。

---

## 1. 專案簡介

這個專案是一個以 FastAPI 為後端、SQLite 為資料庫、純 HTML + JavaScript 為前端的離線式粵語字詞查詢工具。它的核心用途是協助使用者在填詞與創作時，快速找出同韻、同碼或相近發音的詞語。

### 目前已完成的重點功能

- [x] 支援 0243 與 02493 兩種模式（m1 / m2）
- [x] 支援漢字、數字編碼、粵拼與混合查詢
- [x] 支援等號韻查詢，例如 `香港=`
- [x] 支援位置指定的聲母 / 韻母比對
- [x] 對罕見字、混合字串與特殊查詢提供精確匹配處理
- [x] 點擊查詢結果後會直接回到同一套搜尋結果流程
- [x] 顯示同碼 / 同韻相關結果，並改善排序與可讀性
- [x] 將目前查詢狀態同步到瀏覽器 URL，支援返回／前進與分享
- [x] 提供回歸測試，提升搜尋行為穩定性
- [x] 新增獨立「近義/反義詞查找」模式（mode=syn）：前端按鈕 + 兩欄無分數 UI；後端靜態詞林/反義表 + 重用 embedding matrix 混合；可選 near-synonym LLM 生成；preload 即時響應；與 m1/m2 完全正交（不影響原有嚴格 code 過濾與排序）

---

## 2. 專案結構

```text
0243_lyrics_tool/
├── app/
│   ├── database.py
│   ├── models/
│   │   └── word.py
│   ├── routers/
│   │   └── word.py
│   └── schemas/
│       └── word_schema.py
├── frontend/
│   └── index.html
├── data/
│   └── raw/
├── import_data.py
├── init_db.py
├── main.py
├── reset_db.py
├── start.sh
├── utils.py
├── requirements.txt
└── README.md
```

---

## 3. 快速開始

### 啟動服務

```bash
./start.sh
```

若要直接查看前端頁面，可開啟：

```text
frontend/index.html
```

後端 API 可透過以下網址使用：

```text
http://127.0.0.1:8000/docs
```

### 主要搜尋範例

```text
GET /words/search/?q=23就&mode=m2
GET /words/search/?q=2=我3&mode=m1
GET /words/search/?q=23=我&mode=m1
GET /words/search/?q=香港=
```

---

## 4. 開發與資料庫操作

### 初始化資料庫

```bash
python init_db.py
```

### 重置資料庫

```bash
python reset_db.py
```

### 執行回歸測試

```bash
python -m unittest -v tests.test_word_detail
```

---

## 5. 環境設定

1. 安裝依賴：
   ```bash
   pip install -r requirements.txt
   ```
2. 如需使用自訂資料庫位址，可建立 `.env` 並設定 `DATABASE_URL`。
3. 依賴安裝完成後即可啟動服務。

---

## 6. 目前狀態

目前專案已具備可用的搜尋流程與前端互動體驗，包含統一結果頁、相關詞排序、URL 狀態同步與精確字查詢修復。後續可繼續擴充為更完整的押韻詞庫與使用者體驗工具。

## 7. Performance Rule (Non-negotiable) — 瞬間搜尋速度基本規則

**瞬間搜尋速度是本專案的不可協商基本規則之一**（non-negotiable）。所有搜尋（含 m1/m2 純漢字、混合「門0」「好23」、wildcard、syn 近義/反義等）在 preload 完成後**必須感覺 instant**（目標端到端 <0.2s，常見 case 否則 <0.5s）。

### 命名慣例（Naming Conventions）— 硬性規定

**禁止在任何函數、變數、識別項或新程式碼中使用 "hanzi"。**  
這是粵語專案（Cantonese lyrics tool），"hanzi" 為國語用語。日後新增與中文字符（漢字）相關的邏輯時，**必須**使用以下名稱之一：
- **"canto"**（推薦用於與粵語發音/字符相關的脈絡）
- **"chars"**（推薦用於字面字符資料、遮罩位置、literal positions 等；專案內已部分採用）

違反本規定不得合併。所有新貢獻（含註解與文件）都必須遵守。

### 必須涵蓋的關鍵測試案例（每次變更都需驗證）
- 純漢字：「事業」（m1/m2 模式下**嚴格只輸出 query 自己擁有的 0243 codes**，正確 tier 排序，無無關 code 污染如 "0尊"）。
- 混合 literal+digit：「門0」「好23」（literal 優先，預期詞如「門前」「門童」「門鈴」「門庭」等出現在頂部；正確性 + 速度同等重要）。
- Wildcard：「_識_」「好_」。
- Syn 模式：「快樂」（兩欄近義/反義，無分數，preload 後 instant，可點擊連鎖）。
- 其他常見：純數字、= 韻、粵拼片段、load more 邊界。

### Enforcement 流程（每次修改 / 新增功能都必須遵守）
任何 code/frontend/資料/模式變更（含未來擴充），開發者**必須**在提交前執行以下步驟並記錄：
1. 對上述關鍵 case 進行 before/after 計時（瀏覽器 DevTools Network 面板、console.time 包 fetch、或 `python -c 'import time, requests; ...'`）。
2. 比對結果集與排序（dump 前 20-30 筆，確保內容、jyut header 順序、strict per-code 行為、literal priority、syn two-col 完全一致；不得因加速而改變結果）。
3. 執行 `python -m pytest tests/` 確認全綠。
4. 更新 WORKLOG.md：記錄變更摘要、關鍵 case timing 數據、結果無退化證明。
5. 若新功能「必然」會影響速度（極少見），必須先在 plan 討論、調整目標、同步更新本節說明。

違反本規則的變更不得合併。**「在不影響搜尋結果的情況下保持最快速度」是每次迭代的硬性 gate**。

歷史優化基礎（length 索引、strict codes、preload matrix、no DB regex、mem cache、caps + selective query、warmup 等）必須被保留或強化；新 cache 層（server in-mem word meta + server result + frontend JS）是達成「永遠 instant」的核心手段。

（本規則直接回應 2026 年需求：「將瞬間搜尋速度寫入README.md作為基本規則之一，每次修改/新增功能都必須確保在不影響搜尋結果的情況下保持最快速度」。）
