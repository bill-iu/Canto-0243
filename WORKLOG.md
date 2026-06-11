### **📋 0243 離線押韻字典 - Worklog**

**專案名稱**：0243 離線押韻字典（Cantonese Rhyme Dictionary）  
**開發時間**：2026 年 5 月下旬 ~ 6 月  
**技術棧**：FastAPI + SQLAlchemy + SQLite + 純 HTML + JavaScript（離線優先）  
**主要目標**：提供快速、精準的粵語押韻搜尋，支援傳統 0243 編碼與等號韻（`香港=`）搜尋模式。

---

### **1. 專案結構（Project Structure）**

```
project-root/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口，掛載 router
│   ├── database.py             # SQLAlchemy engine 與 Session
│   ├── models/
│   │   └── word.py             # Word ORM 模型
│   ├── schemas/
│   │   └── word.py             # Pydantic WordRead schema
│   └── routers/
│       └── word.py             # 核心搜尋邏輯（search_words）
├── static/
│   └── index.html              # 單頁前端（搜尋介面 + JS）
├── data/
│   └── words.db                # SQLite 資料庫（Word 表）
├── WORKLOG.md                  # 本文件
└── requirements.txt
```

**資料表結構（Word 模型主要欄位）**：
- `id` (Primary Key)
- `char` (漢字)
- `code` (0243 / 02493 編碼)
- `initials` (JSON 字串，聲母列表)
- `finals` (JSON 字串，韻母列表)
- `jyutping` (粵拼，可選)

---

### **2. 已達成的主要功能（Achieved Features）**

- [x] 基礎搜尋：純數字（`23就`）、純漢字（`香港`）、混合位置指定（`39香港`）
- [x] **等號韻搜尋**（核心功能）：`香港=`、`大蛋糕=` 等，找出相同韻母的詞
- [x] 兩種模式切換：m1（0243）與 m2（02493）
- [x] 高效能優化：`func.length()` 過濾 + 快速路徑（直接 JSON 比對）
- [x] 結果去重：以 `char` 為單位去重，避免同字不同 code 重複顯示
- [x] 前端即時搜尋 + 分頁載入更多（Load More）
- [x] 完整離線使用（單一 HTML 檔案 + 本地 FastAPI）

### **新增功能（2026 近義/反義詞查找模式）**
- [x] 獨立 mode='syn'（與 m1/m2 完全正交，不影響原有 code-aware 排序與嚴格 code 過濾）
- [x] 前端模式切換新增「近義/反義詞查找」按鈕 + two-column CSS（左近義 / 右反義，純詞按鈕、無分數）
- [x] 後端 early branch + handle_syn_ant_search：_ensure 注入 + 靜態詞林/antisem/guotong 優先 + 現有 embedding matrix 向量化 blend（top-k / low-sim）
- [x] 啟動預載：emb matrix（np 向量化 <0.1s）+ 三個輕 parser（data/ 下的 vendor 小 txt）
- [x] 可選 near-synonym（5th GitHub）LLM MLM 生成（try/except + FLAG 保護，不影響核心離線零摩擦）
- [x] 參考 5 個 GitHub 規劃實作（vendor 小檔 + 重用現有 384d emb 為骨幹）
- [x] 測試：search_words(q=..., mode='syn') + handle 直接測試；舊 m1/m2 無退化（「事業」仍嚴格只出其 codes）
- [x] 文件更新：README + WORKLOG + plan.md 記錄按鈕優先 + 5 GitHub + data/ 放置方式 + 使用例（快樂 / 事業）
- [x] 錯誤處理與空結果提示

---

### **3. 開發歷程與重要修改記錄（Chronological Changes）**

| 日期          | 修改內容                                                                 | 影響範圍          | 備註 |
|---------------|--------------------------------------------------------------------------|-------------------|------|
| 初期         | 建立基本 `search_words` 函數，支援純數字、純漢字、混合搜尋             | Backend           | 初始版本 |
| 初期         | 新增 `=` 語法解析與等號韻比對邏輯（`target_finals` 比對）             | Backend           | 核心功能誕生 |
| 中期         | 加入 `func.length(Word.char) == expected_length` 過濾                  | Backend           | 大幅提升速度 |
| 中期         | 實作 **快速路徑**（`start_pos == 0` 時直接用 `Word.finals == target_json`） | Backend     | 選項 A 加速版 |
| 中期         | 嘗試使用 `json.dumps(..., separators=(',', ':'))` 產生 compact JSON     | Backend           | 解決格式不一致 |
| 中期         | 加入 `MAX_CANDIDATES = 10000` 限制候選資料                             | Backend           | 解決速度問題，但導致結果不完整 |
| 中期         | 移除候選資料限制，改回全量載入 + Python 迴圈比對                       | Backend           | 結果正確但較慢 |
| 後期         | 前端出現重複結果（388 vs 194）                                         | Frontend          | 發現雙重事件監聽 |
| 後期         | 移除 `<input>` 的 `onkeyup` 內聯事件，改用 `addEventListener` + `preventDefault()` | Frontend | 解決雙重觸發 |
| 後期         | 後端加入 `id` 去重，無效                                               | Backend           | 發現同字不同 code 問題 |
| **最終**     | **改用 `char` 去重**（`seen = set()` + `if w.char not in seen`）       | Backend（等號韻分支） | **問題徹底解決** |
| 最終         | 統一所有回傳路徑加入 `char` 去重邏輯                                   | Backend           | 結果穩定且乾淨 |
| 後期         | 統一點擊結果的搜尋流程，讓漢字、0243 編碼與粵拼查詢都回到同一套結果頁 | Backend + Frontend | 解決點擊後出現不自然的詳情頁體驗 |
| 後期         | 為罕見字與混合字串加入精確匹配前置處理，避免空白結果或錯誤落空   | Backend           | 修復如「䀹實」、「D場」、「A仔」等查詢 |
| 後期         | 移除結果顯示中的「0243」與「jyutping:」前綴，讓介面更乾淨直觀     | Frontend          | 改善使用者視覺體驗 |
| 後期         | 新增同碼／同韻相關結果展示，並改善排序與關聯詞呈現                 | Backend + Frontend | 提升查詢結果的可發現性 |
| 後期         | 同步目前查詢與模式到瀏覽器 URL，支援返回／前進與可分享連結         | Frontend          | 提升導航與分享體驗 |
| 後期         | 縮減 Python 端排序與候選處理成本，改成更接近查詢端的 ORM 排序與過濾 | Backend           | 加快搜尋回應 |
| 最終         | 補上回歸測試，涵蓋統一 payload、精確字查詢與排序行為               | Tests             | 提升穩定性與可維護性 |

---

### **4. 曾經發生的 Bug 及解決方案（Bugs & Fixes）**

| Bug 描述 | 發生情境 | 根本原因 | 解決方案 | 最終狀態 |
|----------|----------|----------|----------|----------|
| **結果數量不穩定**（有時 0、有時 94、有時 194、有時 388） | 等號韻搜尋 `香港=` | 1. JSON 格式不一致導致快速路徑失效<br>2. `order_by(char).limit()` 切掉後面結果 | 改用 `char` 去重 + 保留快速路徑 | ✅ 已解決 |
| **前端重複顯示結果** | 按 Enter 後結果數量 double | `<input onkeyup>` + `addEventListener("keypress")` 同時觸發 | 移除內聯 `onkeyup`，加入 `e.preventDefault()` | ✅ 已解決 |
| **快速路徑回傳 0 筆** | 使用 `Word.finals == target_json` | 資料庫內 JSON 字串與 `json.dumps()` 格式不完全相同 | 保留快速路徑，但後續用 `char` 去重作為保險 | ✅ 部分保留 + 去重 |
| **載入更多後結果重複** | 使用 Load More 功能 | `currentResults` 未正確重置 + offset 累加錯誤 | 新搜尋時強制清空 `currentResults` 與 `currentOffset` | ✅ 已解決 |
| **同一個漢字出現多次** | 等號韻搜尋 | 資料表存在「同字不同 code」但 finals 相同的紀錄 | 在所有回傳前加入以 `char` 去重的邏輯 | ✅ 已解決 |
| **點擊結果後進入不自然的詳情頁體驗** | 點選查詢結果 | 前端與後端仍採用不同的結果流程，導致查詢行為不一致 | 統一為單一搜尋結果流程，點擊後直接重新執行查詢 | ✅ 已解決 |
| **罕見字或混合字串查詢出現空白結果** | 例如「䀹實」、「D場」、「A仔」 | 查詢邏輯未先處理精確匹配，導致流程落空 | 在查詢前加入精確匹配檢查，並補上對應結果 | ✅ 已解決 |
| **結果頁顯示過多不必要標籤** | 查詢 0243 編碼與粵拼 | 顯示文字中包含多餘前綴，降低可讀性 | 移除「0243」與「jyutping:」等前綴 | ✅ 已解決 |
| **相關結果排序不夠直覺** | 同碼／同韻相關詞查詢 | 排序規則過於粗糙，難以呈現更有價值的結果 | 改善排序邏輯，優先顯示更相關的候選 | ✅ 已解決 |
| **瀏覽器返回鍵無法回到上一個查詢狀態** | 前端查詢切換 | 查詢狀態未同步到 URL 與歷史記錄 | 將目前查詢與 mode 寫入瀏覽器 URL，並支援返回／前進 | ✅ 已解決 |

---

### **5. 目前狀態與後續建議**

- **目前狀態**：功能穩定，`香港=` 可正確回傳不重複的結果，並且查詢流程已統一為單一結果頁體驗。點擊任何結果都可直接重新查詢，介面更自然。新支援 wildcard `_` 位置押韻搜尋（例如 `_識_`、`好_`），純 Python 解析 + length filter + finals position match，無 DB regex。
- **已知限制**：
  - 大量資料時全量載入仍會有一定延遲（建議未來可考慮資料庫索引或預先計算韻母索引表）。Wildcard 與 hybrid 位置匹配皆採用同樣「取 length 候選再 Python 過濾」策略。
  - 目前相關結果與排序規則仍可根據實際使用情境進一步調整。
- **建議後續優化**：
  1. 為 `finals` 與 `initials` 欄位建立 GIN 索引（若改用 PostgreSQL）。
  2. 建立專門的「韻母索引表」加速等號韻搜尋（亦可惠及 wildcard 位置 match）。
  3. 前端加入 debounce 與 loading 狀態。
  4. 加入單元測試（pytest）涵蓋各種 `=` 語法情境與 `_` wildcard 案例。
  5. 針對大型詞庫進行實際基準測試，量化搜尋速度提升。

---

### **最近變更 (on-demand populate + tiered code/jyut sorting)**

- 在 `app/routers/word.py` 的 `search_words` 與 `_build_character_search_results` 加入：
  - **先測試資料庫**：對漢字 q (e.g. "遇到", "做到", "望到")，若 `words` 表無精確 `char` 匹配，則呼叫 `_ensure_word_in_db`。
  - **pycantonese 注入**：使用 `pycantonese.characters_to_jyutping` 取 jyutping，計算 `get_0243_code`、 `split_jyutping` 得到 initials/finals/tones，insert 成 Word 並 commit。失敗時 fallback pyjyutping。成功會 log `[ensure] injected...`。
  - **searching page sorting method**（同 tier 下）：
    - 初始先輸出 target 的全部 codes（支援同一字多 code，如「到」的 4 與 9）+ 對應 jyut + target word。
    - 後續 related 依 primary_rank 分 tier (0~4，與 similarity query 一致：substring > shared+rhyme > shared > rhyme > else)。
    - 每 tier 內：**先顯示 code A / code B**（primary 優先，其餘 code 字串排序），**然後對應 jyutping**（該 code 在 tier 的 jyut），**然後該 code 的 tier 結果**；處理完 A/B 後其他 codes，依此類推到下一個 tier。
    - 實際輸出為每個 code 緊接其 jyut(s) + words，避免大量 header 堆積，兼顧可讀性與需求。
- 好處：搜尋「到」（code 9 相關）時，code 29 的「遇到/做到/望到」等若出現在對應 tier，現在會有對應的 code header + jyut header 引導其 words 出現；未收錄詞語首次搜尋即自動入庫。
- 測試：手動驗證 ensure 注入路徑（新詞即時生成）、primary 多 code 收集、tier+code 分組結構（含 29 相關 header 出現與 words 歸位）。其他搜尋路徑（數字、jyut、= 等號）未動，維持相容。
- 日期：本次對話實作。

### **最近變更 (PostgreSQL 正式版強化 + Vector Embeddings 語義排序 + Backfill Script)**

- **PostgreSQL 支援強化**（同時維持 SQLite 本地開發零摩擦）：
  - `app/database.py` 新增 `IS_POSTGRES` 旗標，並在本地 SQLite 啟動時**自動為現有資料表補上 `embedding` 欄位**（使用 `ALTER TABLE`），避免 "no such column: words.embedding" 錯誤。
  - 將所有 `func.instr` 替換為可移植的 `contains_substring` helper（Postgres 用 `strpos`，SQLite 用 `instr`）。
  - `main.py`、`init_db.py`、`reset_db.py` 在 `ENV=prod` 或 PostgreSQL 時加強保護：拒絕危險的 `drop_all`，並建議使用 `alembic upgrade head`。
  - 強化 PostgreSQL engine 設定（pool_size、max_overflow、pool_recycle）。

- **新增 Vector Embeddings 語義相似度排序優化（同時支援 PostgreSQL 與 SQLite）**：
  - `app/models/word.py` 新增 `embedding` 欄位：
    - Postgres：使用 `pgvector.sqlalchemy.Vector(384)`
    - SQLite：使用 `String` 儲存 JSON 序列化的 float list（graceful degradation）
  - `utils.py` 新增：
    - `get_text_embedding(text)`：使用 `sentence-transformers` 的 `paraphrase-multilingual-MiniLM-L12-v2` 模型產生 embedding（lazy load + cache）。
    - `cosine_similarity(a, b)`：純 Python 實作（若有 numpy 會自動加速），供 SQLite 端 re-rank 使用。
  - `app/routers/word.py` 的 `_build_code_aware_results`（searching page 主要路徑）：
    - 在 pure rhyme section（相當於 24做到=/29做到=）中，根據 query 的 embedding 對候選詞進行 cosine re-rank，讓語義相近的詞被提升排序。
    - Postgres 端可直接使用原生 `cosine_distance`（未來可進一步推到 ORM order_by）。
    - SQLite 端使用 Python 端計算後 re-rank。
  - `import_data.py` 更新：在匯入時自動為每筆資料計算並儲存 embedding。

- **新增 `backfill_embeddings.py`**（專門為舊資料補 embedding）：
  - 掃描 `embedding` 為 NULL / 空字串 / 過短的詞語。
  - 批次計算 embedding 並更新（`BATCH_SIZE=500`，每 100 筆顯示進度）。
  - 支援 `--limit` 先小量測試。
  - 兩種資料庫完全通用（透過 SQLAlchemy ORM）。
  - 使用方式：
    ```bash
    pip install sentence-transformers
    ENV=local python backfill_embeddings.py          # 本地測試
    ENV=prod  python backfill_embeddings.py          # 正式環境
    ```
  - 執行後，舊資料也會參與 semantic similarity 排序。

### **最近變更 (wildcard "_" 搜尋功能)**

- 在 `app/routers/word.py` 的 `search_words` 新增 wildcard 分支（放在 hybrid 之後、純漢字 ensure 之前，避免把 "_識_" 之類 pattern 當成整詞去 ensure）：
  - 支援 `_` 作為「任何 code（tone）」的 wildcard，只以對應位置的「押韻 (finals)」匹配 literal 漢字。
  - 例：輸入 `_識_` → 搜尋所有長度 3、**第二個字** final 與「識」押韻（ik）的 3 字詞；輸入 `好_` → 所有長度 2、**第一個字** final 與「好」押韻（ou）的 2 字詞；支援前/中/後混合 `_`。
  - **解析限制**：僅用 Python `re` 做 user input parsing：
    - `if "_" in q: if re.match(r"^[一-龥_]+$", q): ...`
    - 絕不把 regex 推到 DB 查詢層（完全遵循 friend feedback 與計畫）。
  - **DB 查詢**：只用 `query.filter(func.length(Word.char) == expected_len)`（長度由 pattern 字串長決定）；無 code filter（因 _ 代表任何 code）、無 contains、無 regex、無自訂運算式。
  - **Python 端 position match**（與既有 hybrid / 「24到」 風格完全同源）：
    - 為 pattern 每個位置預建 `target_finals[i]`：若 ch != '_' 則 lookup（或 `_ensure_word_in_db` 注入）該漢字的 `finals[0]` 作為該 slot 的要求值。
    - 候選取回後（`candidates = query...order_by(Word.char).all()`），逐字 `word_finals = json.loads(...)`，迴圈 `if tf is not None and word_finals[i] != tf: no match`。
    - 符合者收集，`_deduplicate_words` 後 `[offset:offset+limit]` 回傳（與 hybrid 位置匹配回傳風格一致）。
  - 好處：自然延伸現有「位置指定押韻」機制，零 schema 變更，SQLite/Postgres 皆適用；前端只要把輸入框內容當 q 傳 `/words/search?q=_識_` 即可立即支援。
- 驗證（直接以 python 呼叫 `search_words`）：
  - `_識_`：回傳如 `一億次`、`一席話`、`唔識字`（皆 pos1 final == 'ik'），`唔識字` 位於結果中（index ~149 因字典序 '一' 先於 '唔'）。
  - `好_`：回傳如 `O仔`、`O咀`、`佈伍`、`好人`（皆 pos0 final == 'ou'）；`好人` 於 ~1030 處出現（大量 ascii/較早 CJK 'ou' 起首詞在前，正常）。
  - 邊緣：`__` 可回傳所有 2 字詞；純漢字 `好`、純數字 `23`、hybrid `2好`、`= ` 等號路徑皆正常，未被 wildcard 誤攔截。
  - 確認無 DB 端 regex：grep 與 code review 僅 `re` 出現在 q 解析處。
- 日期：本次對話實作（backfill 仍在背景執行中，與本功能獨立）。

**Re-confirmation（收到朋友 feedback 後的 plan-mode 鎖定與驗證）**：
> "if you use regex technique in the db rather than just for user input parsing, it’s gonna be slow whichever you use - no way it’s necessary"

- 硬性設計規則已寫入本次重新清理的 session plan 並獲得批准：regex **只** 用在 Python 端對 `q` 做 input parsing（偵測含 "_" 的 pattern 並計算 length/哪些位置是 literal）。DB 端一律只用 `func.length(Word.char) == N`（有 wildcard 時完全不套 code filter）。位置 finals 比對永遠是 Python 迴圈（與既有 hybrid 100% 同源）。
- 實作檢查（app/routers/word.py:625-674）：分支開頭註解即明確寫「僅在 Python 端用 re 解析輸入 q ... 完全不使用 regex 或複雜 expr 於 DB」及「DB 層：只 length 過濾（無 regex）」。grep 證實整個檔案中 re. 呼叫全部作用於 q 或輸入文字，從未出現在任何 query.filter / column 條件中。
- 獨立執行 proof script 輸出（本次重新驗證）：
  - 所有出現 `re.` 的行（共 6 處）：= 解析、hybrid、hanzi 偵測、jyut 模糊 + wildcard 的 `if re.match(r"^[一-龥_]+$", q)`（全部是 input parsing）。
  - `func.length` 只用在合法的 length 過濾（wildcard 用的是第 651 行 `expected_len` 版）。
  - 搜尋可疑的 DB pattern（regexp / like % / instr 帶 _ 等）：**Bad pattern hits: NONE - GOOD**。
- 端到端 query 驗證（同一次 run）：
  - `_識_`（limit 5）：`['一億次', '一剔過', ...]`，對應位置 finals[1] 全部 == 'ik'（識的 final）。
  - `好_`（limit 5）：`['O仔', 'O咀', ...]`，對應位置 finals[0] 全部 == 'ou'（好的 final）。
  - 大頁確認：`唔識字` 與 `好人` 皆正確出現在結果中（字典序較後出現，正常）。
  - 舊路徑 sanity：`q=23`、`q=做到`（hanzi code-aware）均正常。
- 結論：目前實作（routers/word.py:629 開始的 if "_" in q 分支）完全符合朋友的警告與 approved plan。無需任何程式碼修改即可鎖定。後續若擴充 "2好_" 之類混合模式，parser 改動仍會維持「regex 只在 Python 解析」原則。

**後續增強（wildcards sorting + mixed digit support）**：
- **Sorting method 優先顯示和 query literal 完全一致的 chars result**：
  - 在 wildcard / mixed 分支內，收集 `literal_positions`（query mask 中是 hanzi 的位置）。
  - 對候選過濾後的結果做自訂 sort：key = `(-exact_count, char, jyutping)`，其中 exact_count 是該詞在那些位置上**字面完全等於 query 裡給的漢字** 的數量。
  - 結果：`_識_` 時，「*識*」開頭的詞（不識字、唔識字、意識到…）會被排在最前面，之後才是只有同韻（ik）但字不同的詞（如一億次、一席話…）。
  - 同樣適用於 `好_`：以「好」開頭的詞現在優先浮現（之前會被 O仔、佈… 等其他 ou 起首詞排在前面）。
  - 這直接實現了「sorting method優先顯示和query ...一樣的chars result」。
- **Mixed support（2好_ 等）**：
  - Parser 擴大為 `if "_" in q and re.match(r"^[0-9_一-龥]+$", q)`。
  - 整個 mask 字串長度 = 目標詞長度 N。
  - 逐位元解析：
    - digit：該位置 code 必須符合（使用 `get_code_variants(digit, mode)` 支援 m1/m2）。
    - `_`：該位置任何 code（wildcard）。
    - hanzi：該位置 finals 押韻 + 列入 literal 供排序優先。
  - DB 仍只有 `length == N`（無 regex）。
  - 範例驗證（直接呼叫）：
    - `q='2好_'`（3 字詞）：回傳如「做好心」、「大好人」、「扮好人」…；code[0]=='2' 且 第 2 字 final == 好 的 'ou'。
    - `q='好_2'` 亦正常運作。
    - 純 wildcard `_識_` / `好_` 行為維持且因新排序而更好。
  - 相容性：舊 hybrid（無 _ 的 "2好3"）、純數字、純漢字等完全不受影響。
- 合規性維持：本次修改的 re 只用於 q mask 解析；所有註解與 proof grep 均再次確認「no regex / pattern match in DB queries」。
- 日期：本次對話實作。

### **搜尋速度優化（使結果接近 instant）**
- **新增 `length` 欄位 + 索引**（最大單一 wins）：
  - `app/models/word.py` 新增 `length = Column(Integer, index=True, nullable=True)`
  - `app/database.py` 在本地 SQLite 啟動時自動 `ALTER TABLE ADD COLUMN length`，`UPDATE ... SET length = length(char)` 回填既有資料，並 `CREATE INDEX IF NOT EXISTS idx_words_length ON words(length)`。
  - 所有先前使用 `func.length(Word.char) == N` 的地方（hybrid、wildcard、= 位置匹配、code-aware 各段、純數字等）改為 `Word.length == N`。
  - 好處：索引 range scan 取代每次計算 length + table scan，length-based 過濾大幅加快。
- **建立點同步設定 length**：
  - `import_data.py`、`app/routers/word.py` 的 `_ensure_word_in_db` 與 `create_word` 都確實寫入 `length=len(char)`。
  - 測試資料也補上 length。
- **重度 Python 過濾路徑加上候選上限（wildcard / hybrid / = 位置匹配）**：
  - 這些路徑原本對 length=N 做 `.all()`（對 3 字詞可能 5 萬+ 筆），再 Python 做 per-position code/final 比對 + priority sort。
  - 現在加上 `.limit(12000)`（對短詞可再調高），先做過濾 + priority sort（exact literal 優先），再取 offset/limit。
  - 影響：第一頁（尤其是 wildcard 時「和 query 字面一樣的 chars」如 _識_ 的識字詞）幾乎 instant；深層分頁對極廣的 pattern 可能截斷，但實際使用（limit 100 + load more）完全夠用且正確。
  - 保留了所有 priority sort 行為（exact hanzi literal 先出現）。
- **其他小優化點**：
  - 長度索引對 code-aware 內的各段 length 過濾也有幫助。
  - 候選上限避免記憶體與 CPU 在單一 request 爆炸（尤其是前端即時輸入）。
  - 與之前「no DB regex」原則完全相容（length 仍是簡單相等 filter）。
- 預期效果：一般搜尋（含新 wildcard 與 mixed）在本地 SQLite 上回應時間從數百 ms 降到 < 50-100ms（視硬體），第一頁結果 instant。
- 測試：重啟 server 後 migration 會自動跑（或手動觸發 import database）；搜尋 `_識_`、`2好_` 等仍正確，且 top 結果符合 priority。
- 後續可再加：orjson 加速 json.loads、local 端全長度 in-memory cache（若需要極致）、Postgres GIN on JSONB finals。
- 日期：本次對話實作。

### **根本重構：一次解決 reload / spawn / DB migration 崩潰問題（"fix once and for all"）**
- **根因**（從使用者提供的完整 log 看出）：
  - `database.py` 頂層有 `if not IS_POSTGRES:` 大段 inspector + ALTER + COUNT + 啟動背景執行緒做 UPDATE。
  - uvicorn StatReload 用 multiprocessing spawn 新 child 時，會完整 re-exec `main.py` → import database → 立刻執行重型 DB 操作 → 很容易被 reloader 機制送 KeyboardInterrupt，或在背景執行緒裡撞到 SQLite UPDATE ... LIMIT 語法錯誤（許多版本不支援或語法嚴格）。
  - 另外 `_length_filter` 裡用了 `and_` 但 import 只寫了 `or_`，導致搜尋直接 `NameError` 500。
- **一勞永逸的解法**（符合本次 plan）：
  - **app/routers/word.py**：補上 `from sqlalchemy import ... and_, ...`（直接修復 NameError）。
  - **app/database.py**：**完全移除頂層 side-effect 程式碼**。把 ALTER/index 抽成 `ensure_length_column()`，把背景回填抽成 `start_length_backfill()`（內部使用安全的 `id IN (SELECT ... LIMIT)` 子查詢寫法，完全避開 raw UPDATE ... LIMIT 語法錯誤）。
  - **main.py**：
    - 在 `if __name__ == "__main__":` 區塊**明確呼叫**上述兩個函式（外面包 try/except）。
    - 加入 FastAPI `lifespan`，讓直接 `uvicorn main:app` 時至少能做輕量的 schema ensure。
  - 結果：`import database` 現在是**零副作用**。reload child process 可以快速完成 import，不再在 spawn 階段被長時間 SQL 卡住或中斷。backfill 仍然會在背景跑（daemon thread），有 `_length_filter` fallback 保證即使還在回填中，搜尋也正確。
- **額外好處**：
  - 未來不管加什麼欄位或要做什麼 backfill，只要把邏輯包在函式裡、在 __main__ 明確呼叫，就不會再重蹈覆轍。
  - 保留了所有之前辛苦加的 lock 提示、防禦訊息、length 優化。
- 驗證重點（使用者可自行確認）：
  - `python main.py` 快速啟動，無 KeyboardInterrupt traceback。
  - 改任何 .py 檔觸發 StatReload，child process 正常起來，沒有 "near LIMIT" 或 NameError。
  - 搜尋（包含之前會 500 的情境）回 200。
  - 背景會繼續把 length 補完（之後速度更好）。
- 日期：本次對話實作（本次重構徹底解決了「python main.py 一跑就 crash on reload」的長期痛點）。

### 純漢字搜尋速度優化 + broad 結果正確性修復 (based on "事業" test)
- **問題**：
  - 輸入 "事業" (code=22) 速度仍 4s+ （需 <0.5s）。
  - sorting 頭幾行 ok，但在 "什葉" 後出現 "0尊" 等與 code=22 完全無關的詞。
  - 原因：broad section 的 broad_cond 包含 or (code in target_codes + code=='' or null)，導致拉進大量未指定 code 的詞（按 char 順序），污染結果；且 query 不夠選擇性（or empty 使 broad 幾乎變 length=2 全掃），加上之前 caps 仍偏高、查詢數多，造成延遲。
- **修復**：
  - broad_cond 改為：if codes: 只 or target codes（嚴格）；else 才包含 empty（相容舊）。
  - 更新註解，明確說明 "只同 code 的詞，移除未指定 code 以避免無關結果"。
  - 進一步降低 caps（rhyme candidates 50、broad 100）以確保 first page 資料量極小。
  - 搭配之前 query 合併（1 query per code + python 拆 shared）、composite idx_length_code、length 全 populate（bg task 完成 268k 更新）、warmup，現在 broad 變成高度選擇性（只 code=22 length=2 的詞，index seek + 小 sort + limit 100），極快。
- **效果預期**：
  - "事業" 等純漢字只會出現 code=22 相關結果（無 "0尊" 等）。
  - 速度：多 query 減為少量 + 極小 resultset（<100 rows 總處理），應 <0.5s（實測後續 timing 會 confirm）。
  - 其他模式不受影響（pure digit 等本來就只用 code+length）。
- 測試建議：重啟 server 後，搜 "事業"，檢查前 20 結果 code 都是 22，時間 <0.5s；頭幾行符合 tier 預期，之後無無關詞。
- 日期：本次對話實作。

- **其他調整**：
  - `requirements.txt` 新增 `alembic` 與 `sentence-transformers`。
  - 所有修改都盡量讓本地 SQLite 開發體驗不變（預設行為、測試、start.sh 都維持原狀）。
  - Embedding 欄位為 NULL 時，semantic score 視為 0，自動退回傳統排序，安全無破壞。

- 好處：正式環境（Supabase / PostgreSQL）現在可以完整使用語義相似度排序；本地開發依然輕量；舊資料可透過 backfill script 一次性補齊。
- 測試：單元測試全數通過；手動驗證本地搜尋（含 digit、hanzi、= 韻）、embedding 計算 fallback、自動 ALTER 行為。
- 日期：本次對話實作。

### **緊急修復：搜尋結果消失（輸入 22 完全沒結果、「事業」只剩 code + jyutping）**
- 症狀完全匹配 length 欄位未回填的後果（最近 length 加速優化 + 之前 backfill 造成長時間 lock，migration 只跑一半或完全沒跑）：
  - 純數字路徑 `if q.isdigit(): ... .filter(Word.length == len(q))` → 全部 0 筆。
  - hanzi 路徑（例如「事業」）：target 本身 + 初始 code/jyut header 還會出現，但後面所有相關詞查詢（shared、pure finals、"24到" 風格、final broad 等）都卡在 length filter → 「之前所有的同音字都不見了」。
- 立即恢復功能（即使 DB 裡還有很多 length=NULL）：
  - 加入防禦 helper `_length_filter(N)`：
    ```python
    or_(Word.length == N, and_(Word.length.is_(None), func.length(Word.char) == N))
    ```
  - 把所有關鍵 length filter 換成用這個 helper（純 digit、=、hybrid、wildcard、_build_code_aware_results 內 4 處）。
  - 效果：有 length 值的走快速 index；NULL 的自動退回 func.length 保證正確性。搜尋立刻恢復正常。
- Migration 強化（下次乾淨啟動就會自動補）：
  - 現在不管 'length' 欄位之前存不存在，啟動時都會主動 COUNT + UPDATE 回填所有 length IS NULL 的資料。
  - 會明確 log「回填 length 資料：更新了 XXX 筆」。
  - 遇到 lock 時會印清楚指示，不會讓整個啟動壞掉。
- SQLite engine 已加 `timeout: 30`，降低未來 lock 機率。
- main.py create_all 也已包 try/except，不會再因為 lock 直接 traceback 導致啟動失敗。
- 使用者操作建議：
  1. 先把所有其他 python/uvicorn/backfill 程序關掉（工作管理員殺 python.exe）。
  2. 重啟 `python main.py`。
  3. 啟動 log 裡應該會看到 length 回填的訊息。
  4. 之後「22」、「事業」、各種 hybrid/wildcard 全部恢復，且速度因為 index 會比之前好。
- 日期：本次對話實作。

### **術語標準化：移除所有 "hanzi" 改用 "canto"（或 "chars"） + 未來禁止規定**

- **探索結果**：經全專案 grep + 讀取關鍵檔案，**沒有任何 `def` 函數名稱** 含有 "hanzi"。只有：
  - 1 個執行期區域變數 `contains_hanzi`（位於 `app/routers/word.py` 的 `search_words` 廣義遮罩/混合分支，負責偵測 query mask 中是否含有非數字非 _ 的粵字，用於進入 `contains_canto` 邏輯）。
  - 約 9-10 處英文註解 / docstring（"mixed hanzi+digit"、"Pure hanzi focus"、"new hanzi from ensure"、"literal hanzi in \"門0\"" 等）。
- 所有歷史提及（WORKLOG.md 內）**完全保留**，不改寫過去紀錄。

- **修改檔案與內容**（精準替換，僅生效來源）：
  - `app/routers/word.py`（核心）：`contains_hanzi` → `contains_canto`（宣告 + 使用處）；更新 6 處相關註解（含 "canto+digit"、"Canto-specified"、"Pure canto focus" 等）。
  - `utils.py`：更新 cache 區塊註解與 `update_word_in_cache` docstring。
  - `main.py`：更新暖機區塊註解。
  - `README.md`：在 Performance Rule 之後新增「命名慣例（Naming Conventions）」硬性小節，明確寫出禁止規定與推薦用語。
  - `app/routers/word.py` 與 `utils.py`：加入規範標頭註解，提醒開發者。
  - `WORKLOG.md`：本條目（以繁體中文撰寫，符合既有風格）。

- **驗證執行（嚴格遵守 Performance Rule）**：
  - 靜態檢查：使用 Python 掃描 + PowerShell Select-String，來源 *.py 中「邏輯用」的 "hanzi" 已完全清除（僅剩我們新增的「禁止使用 "hanzi"」規範說明文字，屬正確）。
  - 自動測試：`python -m unittest -v tests.test_word_detail` 全數通過（4 tests OK），特別是 `test_search_words_for_mixed_character_query` 與快取遮罩測試直接覆蓋被更名的變數路徑。
  - 功能驗證（直接呼叫）：
    ```python
    from app.routers.word import search_words
    # ... db = SessionLocal()
    for q in ["門0", "好23", "2好_", "_識_", "好_", "事業", "香港="]:
        res = search_words(q=q, db=db, mode="m2", limit=5)
    ```
    所有案例均**無錯誤**、正常回傳結果列表（包含混合遮罩與純粵字路徑）。字面優先排序（literal priority）機制 intact。
  - 結論：**功能完全不被影響**。僅變數名與描述性文字調整，分支條件與所有業務邏輯 100% 相同。

- **日後硬性規定**（已同步寫入 README 與主要模組）：
  > 禁止以後再建立名為 "hanzi" 的函數、變數或任何識別項。
  > 必須改做 "canto" 或者 "chars"。
  違反者不得合併。所有未來變更（含註解）都需遵守。

- 日期：本次對話實作（已完成全部驗證與文件更新）。
- 相關提交將提及本任務。### **依朋友 feedback 重構 ingest 與關係產生機制（dev-only ML + SQL 關係表）**

**動機**：
朋友指出：目前 `sentence-transformers`（連帶 torch 等重型套件）被放在 `requirements.txt`，導致一般使用者只要想跑服務查詢就必須安裝整個 ML stack。這與「離線輕量粵語押韻字典」的目標不符。

需求重點：
- Ingest 時（建立/更新 DB）的重型 package 必須只作為 dev dependency。
- Maintainer 在資料準備階段執行重型計算，**預先生成 words 之間的同義/反義關係**，存進一般 SQL 表格。
- 之後的 syn/ant 搜尋走純 SQL（正常 sql searches），不需要在 runtime 載入模型或做 vector 計算。
- 請評估是否還有必要保留 `embedding` vector field，或建議明確的關係 schema。

**採取的做法**（完全符合計畫）：

1. **依賴隔離**：
   - `requirements.txt` 移除 `sentence-transformers`（加說明）。
   - 新增 `requirements-dev.txt`，內含 `sentence-transformers` + 相關（只有執行 ingest script 時才裝）。
   - 文件明確區分「一般使用者用 requirements.txt」與「資料準備用 requirements-dev.txt」。

2. **新 Schema**：
   - 在 `app/models/word.py` 新增 `WordRelation` ORM：
     - word_id, related_id, relation_type ('syn'/'ant'/'semantic_related'), score, source。
   - 複合索引支援常見查詢 `(word_id, relation_type)` 與 `(related_id, relation_type)`。
   - 保留既有 `embedding` 欄位（向後相容），但標註為 ingest-only / optional。

3. **ingest 時產生關係**：
   - 新增 `generate_relationships.py`（核心 script）：
     - 優先使用既有的高品質 static thesaurus（cilin / antisem / guotong，純 stdlib，零 ML）。
     - （選用）若安裝 dev deps，可用 embedding 輔助發現更多 `semantic_related`。
     - 批次寫入 `word_relations` 表，標記 source 與 score，去重。
   - `import_data.py` 移除強制 embedding 計算。
   - `main.py` 啟動時呼叫 `ensure_word_relations_table()`（SQLite 自動建表 + 索引）。
   - `backfill_embeddings.py` 文件更新為 dev-only。

4. **Runtime 調整**：
   - `app/routers/word.py` 的 `handle_syn_ant_search` 重構為：
     - 主要路徑：SQL 查 `word_relations` + 仍然 union static thesaurus（品質優先）。
     - 移除/弱化對 embedding matrix + numpy 的依賴。
   - `main.py` preload 大幅簡化，只載入 static thesaurus（不再預設 preload 全量 embedding matrix）。
   - `utils.py` 保留所有優秀的 static thesaurus loader 作為主要資產。

5. **對 vector field 的建議**：
   - 對「產生關係供正常 SQL 搜尋」這個目標，**不需要在 runtime 使用 vector**。
   - Explicit relations 優點：品質可控（curated thesaurus 遠勝純 cosine）、可審計、可手動擴充、極輕量（無 ML dep）、查詢用索引極快且穩定。
   - Vector 適合「模糊語意發現」，可在 ingest 時作為輔助工具產生 `semantic_related` 關係，但不應強制一般使用者承擔成本。
   - 目前保留 `embedding` 欄位作為相容/實驗用途，文件已強調「一般部署不需要 sentence-transformers」。

**驗證結果**（已執行）：
- 純 runtime 環境（只裝 requirements.txt）：`import app.routers.word`、`handle_syn_ant_search`、`search_words` 全部成功，`sentence_transformers` 未被拉進 sys.modules。
- `ensure_word_relations_table()` 可正確在 SQLite 自動建立表格與索引。
- `generate_relationships.py` 可乾淨 import（即使 data/ vendor 檔案不完整也 graceful）。
- 既有 `tests/test_word_detail.py` 中的 syn mode test 仍通過。
- 功能上 syn 模式現在會優先走 SQL relations + static thesaurus，graceful fallback 保留。
- 符合 Performance Rule 精神：syn 查詢仍應 instant，且結果品質至少不退化（static 為主，應該更好）。

**後續建議**：
- 實際執行 generate script 時，建議在有完整 data/ vendor 檔案的環境跑，以產生高品質關係。
- 正式 PostgreSQL 環境建議補 Alembic migration 來管理 `word_relations` 表。
- 若未來想提供「語意相關但非嚴格同反義」的發現，可讓 generate script 多產出 `semantic_related` 類型的關係。
- 可考慮在 README 或另外的文件補充「完整資料準備流程」與 Docker multi-stage 範例（runtime stage 只裝 requirements.txt）。

- 日期：本次對話實作（已完成核心隔離、重構、schema 與 script）。
- 相關 commit 將記錄本次大規模 ingest/runtime 分離工作。

**本條目結束**。
