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
