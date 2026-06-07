# 0243 歌詞搜尋工具 - 專案總覽

**專案名稱**：0243 Lyrics Search Tool  
**開發者**：Wizgo  
**開始日期**：2026 年  
**當前狀態**：核心功能已基本完成

**以下是為你的專案撰寫的完整專案文件：**

---

# 0243 歌詞搜尋工具 - 專案總覽

**版本日期**：2026-06-08  
**開發者**：Wizgo  
**目標**：建立一個支援 0243 碼 + 粵語押韻 + 多模式（m1/m2）的高效歌詞填詞搜尋工具

---

## 1. 專案結構

```
0243_lyrics_tool/
├── main.py                      # FastAPI 入口
├── import_data.py               # 統一資料匯入工具（推薦使用）
├── utils.py                     # 核心工具函式（get_0243_code, split_jyutping, get_code_variants）
├── jyutping_table.py            # 聲母韻母對照表
├── add_jyutping_to_0243.py     # 0243 字典 + 韻母字典合併工具
├── convert_wordslist.py         # wordslist.json 格式轉換
├── start.sh                     # 啟動腳本
│
├── app/
│   ├── __init__.py
│   ├── database.py              # SQLite 連接 + Session
│   ├── models/
│   │   └── word.py              # Word 資料模型
│   ├── schemas/
│   │   └── word_schema.py       # Pydantic 模型
│   └── routers/
│       └── word.py              # 所有搜尋 API
│
├── data/raw/                    # 原始與中繼 JSON
│   ├── kaifangcidian_clean.json
│   ├── cccanto_clean.json
│   ├── wordslist_clean.json
│   ├── merged_0243_with_jyutping.json   ← 目前主力資料
│   └── 0243_dict_1to5digits.json
│
├── lyrics.db                    # SQLite 資料庫（主資料）
└── venv/
```

---

## 2. 已經達成的功能

- [x] **FastAPI + SQLAlchemy 基礎架構**（含自動重載）
- [x] **多來源資料統一匯入**（kaifangcidian、cccanto、wordslist、merged_0243）
- [x] **Word 模型**（char, code, jyutping, initials, finals, tones）
- [x] **精準 0243 code 生成**（支援多音節）
- [x] **聲母 / 韻母 / 聲調自動拆分**
- [x] **m1 / m2 模式切換**（獨立於搜尋邏輯）
- [x] **等號韻搜尋**（`香港=` / `=香港人`）—— 整詞序列完全匹配（韻母或聲母）
- [x] **普通尾字押韻搜尋**（`23就`）
- [x] **同一詞語不同 code 並存**（例如「央行」同時有 30 和 39）
- [x] **分頁 + 排序**
- [x] **資料清理與去重機制**

---

## 3. 正在進行 / 最近優化

- [ ] **m1/m2 在所有搜尋中的穩定應用**（已基本完成）
- [ ] **等號韻的穩定性測試與微調**
- [ ] **前端簡單介面**（HTML + JavaScript 搜尋頁）

---

## 4. 有待開發的功能與任務（優先順序）

### **高優先**
1. **前端搜尋頁面**（HTML + JS）—— 支援即時搜尋、模式切換（m1/m2）、歷史記錄
2. **API 文件與錯誤處理優化**（Swagger 更友好）
3. **更多資料來源整合**（dict.db、其他粵語字典）
4. **多字押韻支援**（不僅限最後一個字，可指定第 N 個字押韻）

### **中優先**
5. **進階搜尋**：
   - 聲母 + 韻母混合匹配
   - 模糊音近搜尋
   - 長度限制（幾個字的詞）
6. **統計功能**（某 code 有多少詞、某韻母出現頻率）
7. **匯出功能**（JSON / CSV / 歌詞格式）

### **低優先 / 未來**
8. **用戶系統**（收藏、歷史、自訂詞庫）
9. **AI 填詞建議**（結合 Suno 或其他工具）
10. **PostgreSQL 生產環境部署**
11. **效能優化**（索引、快取、大資料量分頁）

---

## 5. 使用說明（快速參考）

```bash
# 啟動
./start.sh
# 或
python main.py

# 主要 API
GET /words/search/?q=23就&mode=m2
GET /words/search/?q=39香港=&mode=m1
GET /words/search/?code=3340&limit=50
```

---
