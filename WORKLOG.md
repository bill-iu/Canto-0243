### **📋 0243 離線押韻字典 - Worklog**

**專案名稱**：0243 離線押韻字典（Cantonese Rhyme Dictionary）  
**開發時間**：2026 年 5 月下旬 ~ 6 月  
**技術棧**：FastAPI + SQLAlchemy + SQLite/PostgreSQL + 純 HTML/JS（離線優先）  
**主要目標**：提供快速、精準的粵語押韻搜尋，支援傳統 0243 編碼、等號韻（`香港=`）、wildcard 與近義/反義詞模式。**核心原則**：runtime 輕量（無 ML）、ingest 時預先計算關係供純 SQL 查詢。

---

### **1. 專案結構與 Schema**

- `app/routers/word.py`：`search_words`（多模式分派） + `handle_syn_ant_search`
- `app/models/word.py`：`Word` + `WordRelation`（word_id / related_id / relation_type='syn'|'ant'|'semantic_related' / score / source）
- `utils.py`：static thesaurus loader（cilin + guotong）、length cache、ensure helpers
- `data/thesaurus/`、`data/cilin/`、`data/antonym/`：主要 static 來源
- `generate_relationships.py` / `ingest_syn_ant.py`：ingest 工具
- 前端：單頁 `frontend/index.html`（模式切換 + 結果渲染）

**關鍵設計**：
- `length` 欄位 + 索引（大幅加速 length-based 過濾）
- `word_relations` 表（BigInt FK + 複合索引），取代 runtime vector
- embedding 欄位保留（ingest-only / optional）

---

### **2. 已達成的主要功能**

- **基礎與等號韻**：純數字、純漢字、混合（`39香港`）、`香港=` 等號韻（相同 finals）
- **Wildcard 與混合**：`_識_`、`好_`、`2好_` 等位置指定押韻（Python 解析 + length 過濾，無 DB regex）
- **Syn / Ant 模式**（mode='syn'）：獨立近義/反義詞查找
  - 主要路徑：預先計算的 `word_relations`（純 SQL）
  - Fallback / 補充：static thesaurus（cilin + guotong）
  - Runtime **完全不載入** sentence-transformers / torch
- **效能**：length 索引 + in-memory cache + tiered sorting + 去重（以 `char` 為主）
- **資料準備**：`_ensure_word_in_db`（首次查詢自動注入 jyutping + code）
- **離線優先**：start.sh + 雙擊 index.html 保護（file:// 時顯示提示）

---

### **3. 開發時間線與重要主題（精簡）**

**初期 ~ 中期**：基礎押韻 + 等號韻 + 效能基礎  
- 實作 `=` 語法、finals 比對、char 去重
- 加入 `length` 過濾 + 快速 JSON 路徑
- 前端即時搜尋 + Load More + URL 同步

**2026-06：Syn/Ant 模式 + Ingest 重構（朋友 feedback 主導）**  
- **動機**：避免一般使用者安裝 ML 套件。Ingest 時預先生成關係，runtime 只用純 SQL + static thesaurus。
- **成果**：
  - `requirements.txt` 移除 sentence-transformers；新增 `requirements-dev.txt`
  - 新增 `WordRelation` 表 + `generate_relationships.py`（static 優先 + 可選 embedding 輔助 semantic_related）
  - `handle_syn_ant_search` 重構為 SQL 主路徑 + static fallback
  - `main.py` / `utils.py` 啟動只 preload static thesaurus + word cache
- **對 vector 的結論**：不需要在 runtime 使用；explicit relations 更可控、可審計。

**資料來源擴充**：
- **Cilin**：從 liao961120/cilin 取得，OpenCC s2t 轉繁體 → `data/cilin/new_cilin.txt`，透過 ingest 產生大量 syn 關係。
- **Guotong**（本次重點）：
  - 來源：https://github.com/guotong1988/chinese_dictionary（原本簡體）
  - 建立 `convert_guodict.py`：下載 raw → opencc s2t 轉繁體 → 覆蓋 `data/thesaurus/dict_synonym.txt` 與 `dict_antonym.txt`
  - **關鍵修復**：`load_thesaurus_dicts()` 與 `load_antonym_dict()` 原本只單向 populate（`w = parts[0]`），導致「熱」查無「冷」。
    - 改為雙向展開：任何 "A——B" / "A B" pair 都會讓雙方互相知道對方。
    - 同時處理 synonym 檔案的 "CODE= word..." 前綴。
  - 結果：syn mode 輸入「熱」現在正確顯示「冷」等反義詞；「前/後」、「高/矮」、「進/退」等 pair 雙向可用。get_synonyms / get_antonyms 更完整。
  - 完全整合 ingest 流程，source=static_thesaurus。

**持續優化**：
- Wildcard / hybrid / code-aware 排序（literal priority + tier）
- length 欄位 + 索引 + 背景 backfill（大幅加速）
- 命名規範：全面改用 `canto` / `chars`（禁止 "hanzi"）
- PostgreSQL 強化（portable contains_substring、自動 ALTER、Alembic）
- 防禦性 fallback（length 為 NULL 時退回 func.length）

---

### **4. 主要 Bug 與解決（精選）**

- 結果數量不穩 / 重複 → char 去重 + 事件監聽清理
- 同字不同 code 污染結果 → 統一 char 去重 + code-aware tier 排序
- Syn mode 只出自己 / 無反義 → 修復 guotong pair 雙向解析
- 長度未回填導致很多模式 0 結果 → 加入 `_length_filter` 防禦 + 自動 backfill
- Reload / spawn 時 DB 操作崩潰 → 移除頂層 side-effect，全部包成 `ensure_*` + daemon thread

---

### **5. 目前狀態（2026-06 最新）**

- **Syn/Ant 模式** 穩定且正確：優先走 `word_relations` + static thesaurus（cilin + 完整 guotong 繁體）。輸入「熱」可得到「冷」等反義詞。
- **資料**：`data/thesaurus/dict_*.txt` 已為完整繁體 guotong；cilin 亦為繁體。
- **效能**：多數查詢（含 wildcard、純漢字、syn）在本地 SQLite 達實用速度；length 索引 + cache 貢獻最大。
- **Runtime 特性**：完全不依賴 ML 套件（只有 ingest 階段才需要 requirements-dev）。
- **測試**：單元測試涵蓋 syn mode、ingest、正規化、雙向 pair；手動驗證 guotong 轉換與解析。

**已知限制**：
- 極大資料集時仍依賴 length 過濾後的 Python 處理（可接受）。
- 完整 guotong / cilin 關係需執行 ingest script 才進入 DB（static thesaurus 仍可即時使用）。

**後續建議**：
1. 把 guotong 正式註冊到 `data/syn_ant/sources.yaml`。
2. 考慮為高頻 pair 預先計算更多 `word_relations`。
3. PostgreSQL 環境建議用 GIN 索引優化 JSONB finals（若需要）。
4. 持續維持「ingest 重型、runtime 輕量」與「regex 只在 Python input parsing」的原則。

---

### **6. 命名與流程規範（硬性）**

- 禁止使用 "hanzi"：一律用 `canto` 或 `chars`。
- Regex 只允許在 Python 端做使用者輸入解析（q mask 偵測），絕不推到 DB 查詢。
- 任何新欄位或 backfill 必須包成 `ensure_*` 函式，在 `__main__` 或 lifespan 明確呼叫，避免 reload 時副作用。

**本文件已 review 並壓縮整合**（移除大量重複的「最近變更」細節，合併為主題式時間線與技術故事，最新 guotong 轉換 + 雙向 parser 修復已完整納入）。所有歷史決策與朋友 feedback 精神保留。

**最後更新**：本次對話實作（guotong 完整轉繁體 + parser 雙向修復 + WORKLOG 壓縮）。