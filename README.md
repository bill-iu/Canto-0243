# 0243 歌詞搜尋工具 - 專案總覽

**版本日期**：2026-06-09  
**開發者**：Wizgo  
**目標**：建立一個支援 0243 碼 + 粵語押韻 + 多模式（m1/m2）的高效歌詞填詞搜尋工具

---

## 1. 專案結構

```
0243_lyrics_tool/
├── main.py
├── init_db.py                  # 初始化資料庫
├── reset_db.py                 # 重置資料庫（開發用）
├── import_data.py              # 統一資料匯入工具
├── utils.py                    # 核心工具函式
├── jyutping_table.py
├── start.sh
│
├── app/
│   ├── database.py             # 支援 SQLite / PostgreSQL + dotenv
│   ├── models/
│   │   └── word.py
│   ├── schemas/
│   │   └── word_schema.py
│   └── routers/
│       └── word.py             # 搜尋 API（含等號韻 + 位置指定）
│
├── data/raw/                   # 原始資料（已忽略上傳）
│
├── lyrics.db                   # SQLite 資料庫
├── .env                        # 本地環境變數（已忽略）
├── .env.example
├── requirements.txt
└── README.md
```

---

## 2. 已經達成的功能

- [x] **FastAPI + SQLAlchemy 架構**（支援 SQLite 與 PostgreSQL 切換）
- [x] **多來源資料統一匯入**（kaifangcidian、cccanto、wordslist、merged_0243）
- [x] **完整 Word 模型**（包含 `initials`、`finals`、`tones` JSON 欄位）
- [x] **聲母 / 韻母 / 聲調自動拆分**
- [x] **m1 / m2 模式切換**（獨立於搜尋邏輯）
- [x] **等號韻搜尋**（支援位置指定聲母匹配，如 `2=我3`、`23=我`）
- [x] **位置指定混合搜尋**（如 `2香3`、`23我`，可指定位置押韻）
- [x] **傳統等號韻**（如 `香港=` 完整序列匹配）
- [x] **同一詞語不同 code 並存**（如「央行」同時支援 code 30 與 39）
- [x] **資料庫初始化與重置工具**（`init_db.py` / `reset_db.py`）
- [x] **環境變數管理**（`.env` + `python-dotenv`）
- [x] **分頁、排序與錯誤處理**

---

## 3. 正在進行 / 最近更新

- [x] 等號韻的位置指定聲母匹配邏輯修正
- [x] `reset_db.py` 重置資料庫腳本
- [x] `init_db.py` 初始化資料庫腳本
- [x] `app/database.py` 重構（同時支援 SQLite 與 PostgreSQL）
- [ ] 前端搜尋介面開發
- [ ] PostgreSQL 正式部署與資料匯入教學

---

## 4. 有待開發的功能與任務（優先順序）

### 高優先
1. **前端搜尋頁面**（HTML + JavaScript）
2. **PostgreSQL 部署教學**（含免費資料庫申請與資料匯入）
3. **多位置押韻支援**（可同時指定多個位置押韻）
4. **API 文件優化**（更完整的 Swagger 說明）

### 中優先
5. 進階搜尋功能（聲母 + 韻母混合、模糊音近搜尋）
6. 統計功能（某 code / 某韻母出現頻率）
7. 匯出功能（JSON / CSV）

### 低優先 / 未來
8. 使用者系統（收藏、歷史紀錄）
9. AI 填詞建議整合
10. 效能優化（索引、快取）

---

## 5. 快速使用說明

```bash
# 啟動專案
./start.sh
# 或
python main.py

# 主要搜尋 API 範例
GET /words/search/?q=23就&mode=m2
GET /words/search/?q=2=我3&mode=m1
GET /words/search/?q=23=我&mode=m1
GET /words/search/?q=香港=
```

### 初始化 / 重置資料庫

```bash
# 初始化資料表
python init_db.py

# 重置資料庫（會清空所有資料）
python reset_db.py
```

---

## 6. 環境設定

1. 複製環境變數範例：
   ```bash
   cp .env.example .env
   ```
2. 修改 `.env` 中的 `DATABASE_URL`（預設為 SQLite）
3. 安裝依賴：
   ```bash
   pip install -r requirements.txt
   ```

---

**目前狀態**：核心後端功能已完成，資料庫支援已準備就緒，正準備進行前端開發與 PostgreSQL 部署教學。

```

---