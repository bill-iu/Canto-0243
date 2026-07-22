# 實作計劃：四字缺直連反義 campaign（campaign_len4）

**日期**：2026-07-15  
**狀態**：已 grill 收斂；待實作  
**領域**：`CONTEXT.md` → **四字缺直連反義 campaign**、**四字尾軟偏好**  
**分支**：`dev`（改動 commit+push 至 dev；入 main 另開 PR）

---

## 0. 目標與非目標

### 目標

凍結母體 **有近無直連反 ∩ 字面長度 = 4**，分批裁定至全數 **已裁定**（`accepted` ∨ `no_natural_antonym`），品質閘 ≥90%，產物入既有 **專案自建反義清單**（`project_antonyms.tsv`）。

完成宣稱（release／文案）：

> 四字缺直連母體已裁定  

**唔**宣稱：全部成語／全部四字都有反義。

### 非目標

| 不做 | 原因 |
|------|------|
| MOE 相反詞 | 已否決 |
| Wikidata P461 作主線 | 數量／概念對立不對口 |
| Lexeme P5974 ingest | 另 PR；中文 ~百級 |
| 改 `sort_ant_pool`／runtime 排序 | grill Q8：只動資料 |
| 關近義橋／runtime 衍生 | grill Q9：完成後仍保底 |
| 成語 SSOT／「真成語」過濾 | 母體係長度條件，唔係成語表 |
| 硬性四字尾 | 只做 **四字尾軟偏好** |

### 規模（本機 `lyrics.db` 觀測，freeze 當刻會重算）

| 集合 | 約略 |
|------|------|
| 詞庫四字 | ~29k |
| 四字 ∩ 有近 ∩ 無直連（WR+靜態，邏輯排除 project_ant） | **~3.2k** |
| 既有 project_ant 端點為四字 | ~36 |
| Top-5000 已 `no_natural` 且 len=4（可繼承） | **~18** |
| 清單任一端為四字嘅 accepted 對 | ~33 |

工程量主體 ≈ 3.2k − 已有 project 覆蓋 − 繼承 no_natural ≈ **~3.1k 未裁定**。

---

## 1. 已鎖定決策（grill 摘要）

| # | 決策 | 選擇 |
|---|------|------|
| 1 | 完成定義 | 凍結母體全數已裁定 |
| 2 | 母體 | 有近無直連反 ∩ len=4 |
| 3 | 推進 | 一次凍結全量，分批 |
| 4 | 尾形態 | 軟偏好四字尾（短尾可入帳） |
| 5 | Top-5000 | 同字面 `no_natural` **繼承**為已裁定 |
| 6 | Prompt | 四字專用盲生成稿 |
| 7 | 品質閘 | ≥0.90（pair + no-natural + 最終稽核） |
| 8 | Runtime | 唔改 ant 排序 |
| 9 | 橋／衍生 | 完成後仍開 |
| 10 | 次序／批 | Essay `freq DESC, literal ASC`；batch≈500 |
| 11 | 工程 | 平行 campaign 資產 + 重用 CLI／庫 |

---

## 2. 現況工具與必須改動的契約缺口

重用：

- `ingest/project_antonyms.py` — TSV／meta／filter／sample
- `ingest/project_antonyms_campaign.py` — freeze／progress／no-natural／final audit
- `scripts/project_antonyms.py` — CLI
- 共用 accepted：`data/syn_ant/project_antonyms.tsv` + `project_antonyms.meta.json`
- 測試樣式：`tests/smoke/test_project_antonyms_campaign.py`

**硬編碼（Top-5000 專用，len4 唔能原樣套）：**

| 契約 | 現值 | len4 需要 |
|------|------|-----------|
| `CAMPAIGN_K` | 5000 固定 | **freeze 當刻全母體大小**（~3.2k，唔截 Top-K） |
| `CAMPAIGN_BATCH_SIZE` | 500 | 500（末批可 **&lt;500**） |
| `batch_count` | 10 固定 | `ceil(k / 500)` |
| `batch_counts[*]` | 每批恰 500 | 末批允許 residual |
| `rank_campaign_heads` | 無長度過濾 | `len(literal)==4` |
| Default paths | `campaign_top5000.*` | 平行 `campaign_len4.*` |
| `no_natural` 檔 | 單檔綁 Top-5000 | **平行檔**（見 §3.2） |
| final audit meta | `campaign_final_audit.meta.json` | 平行 `campaign_len4_final_audit.meta.json` |

**繼承陷阱：**  
`compute_campaign_progress` 對 `no_natural_heads - campaign` **fail-closed**。  
若 len4 validate 直接指向現有 `project_no_natural_antonyms.tsv`（含 ~3k 非四字頭），會報 `no-natural outside campaign`。  
→ **唔好共用同一 no-natural TSV 做 validate**；用平行檔 + freeze 時 seed 繼承列。

---

## 3. 資產與命名

| 角色 | 路徑（建議） |
|------|----------------|
| Manifest TSV | `data/syn_ant/campaign_len4.tsv` |
| Manifest meta | `data/syn_ant/campaign_len4.meta.json` |
| No-natural TSV | `data/syn_ant/campaign_len4_no_natural.tsv` |
| No-natural meta | `data/syn_ant/campaign_len4_no_natural.meta.json` |
| Final audit | `data/syn_ant/campaign_len4_final_audit.meta.json` |
| 四字 prompt | `data/syn_ant/project-antonyms-prompt-len4.txt` |
| Accepted（共用） | `data/syn_ant/project_antonyms.tsv` |
| Batch meta（共用 batches map） | `data/syn_ant/project_antonyms.meta.json` 內 `batches["len4-bNN-…"]` |

**campaign id slug**：`len4`（文件全名：四字缺直連反義 campaign）。  
**batch_id 前綴**：`len4-b01-YYYYMMDD` …（同現有 `campaign-b01-…` 風格，避免同 top5000 撞名）。

Manifest 欄位：沿用 `rank / head / essay_frequency / batch_index`（同 `campaign_top5000.tsv`）。

Meta 最少欄位（對齊 top5000，另加）：

```json
{
  "campaign_id": "len4",
  "baseline_commit": "<freeze 當刻或固定基準 sha>",
  "freeze_git_commit": "<sha>",
  "k": 0,
  "batch_size": 500,
  "batch_count": 0,
  "length_filter": 4,
  "seed_predicate": "has_syn_no_direct_ant_excluding_project_ant",
  "exclude_sources": ["…derived…", "project_ant"],
  "db_sha256": "…",
  "essay_sha256": "…",
  "thesaurus_ant_sha256": "…",
  "batch_counts": { "1": 500, "2": 500, "…": "…", "N": 123 },
  "manifest_sha256": "…",
  "inherited_no_natural_count": 0,
  "inherited_no_natural_source": "data/syn_ant/project_no_natural_antonyms.tsv"
}
```

---

## 4. 實作工作包（WP）

### WP-01 — CampaignSpec 泛化（庫）

**檔案**：`ingest/project_antonyms_campaign.py`（必要時拆小模組；注意既有 300-line 豁免註解）

1. 引入不可變 **CampaignSpec**（或等效參數物件）：
   - `campaign_id`, `batch_size=500`
   - `length_filter: int | None`（len4=4；top5000=`None`）
   - 路徑 defaults（manifest / no_natural / final audit）
   - `k_mode`: `"top_k"`（5000）| `"full_set"`（len4 全取）
   - `fixed_k` 僅 top_k 使用
2. 重構（行為不變為準）：
   - `rank_campaign_heads(..., *, length_filter=None, k=…)`  
     - 候選：`syns - directs` ∩ membership ∩ `is_valid_term`  
     - 若 `length_filter`：`len(c)==length_filter`  
     - `full_set`：`k = len(ranked)`（唔截斷）；`top_k`：保持 `[:k]`
   - `build_campaign_meta` / `validate_campaign_meta` / `parse_campaign_manifest`：  
     - **唔再**假設全局 `CAMPAIGN_K==5000`  
     - 允許末批 `1..batch_size`；前 N−1 批恰 `batch_size`（若 k 整除則全批恰 500）
   - Top-5000：spec 常數保持現有 fail-closed（k=5000、10×500），**回歸測試必須綠**
3. 導出 `LEN4_SPEC` 與 `TOP5000_SPEC`（或 CLI 用 id 查找）。

**完成定義**：`tests/smoke/test_project_antonyms_campaign.py` 全過；新增 len4 形狀測試（見 WP-06）。

---

### WP-02 — CLI：campaign 選擇子

**檔案**：`scripts/project_antonyms.py`

1. 為下列子命令加 `--campaign {top5000,len4}`（default=`top5000`，保兼容）：
   - `campaign-freeze`
   - `campaign-validate`
   - `campaign-unresolved`
   - `no-natural-sample` / `no-natural-validate`（manifest／no-natural 路徑跟 campaign）
   - `campaign-final-sample` / `campaign-final-validate`
2. 路徑解析：未顯式 `--tsv/--meta/…` 時用 spec 預設。
3. `campaign-freeze` 對 len4：
   - 調 `rank_campaign_heads`（length=4, full_set）
   - 寫 `campaign_len4.tsv` + `.meta.json`
   - **繼承 seed**（WP-03）寫入 `campaign_len4_no_natural.tsv`（若檔已存在：預設 fail 或要求 `--force-reseed-no-natural`，**禁止默默覆蓋已審列**）
4. 印出 JSON 摘要：`k`, `batch_count`, `inherited_no_natural`, `first/last head`。

**完成定義**：  
`python scripts/project_antonyms.py campaign-freeze --campaign len4 --db lyrics.db`  
可重現寫出 manifest；  
`campaign-validate --campaign top5000` 行為與今日一致。

---

### WP-03 — No-natural 平行檔 + 繼承

1. Freeze 時讀 `project_no_natural_antonyms.tsv`：
   - 過濾 `head in len4_manifest`
   - 寫入 `campaign_len4_no_natural.tsv`（header 同現：`head, reason, batch_id`）
   - `batch_id`：保留原 batch_id **或** 統一標 `inherited-top5000`（二選一，**freeze 時釘死一種**並寫進 meta；建議保留原 id 以利追溯，validate 只要求 non-empty + allowlist reason）
2. Len4 新判 `no_natural` **只 append** `campaign_len4_no_natural.tsv`。
3. **唔**自動改 Top-5000 的 `project_no_natural_antonyms.tsv`（避免雙向耦合）。
4. 若日後要單一全域 no-natural 表：另開重構；本期 YAGNI。

**完成定義**：validate len4 時，繼承嘅 ~18 頭計入 `no_natural`／resolved，且唔報 outside campaign。

---

### WP-04 — 四字專用 prompt

**檔案**：`data/syn_ant/project-antonyms-prompt-len4.txt`

內容要求（盲生成契約不變）：

- 種子為四字／類成語字面
- 最多 3 候選；寧可少、唔硬砌
- **優先**同詞性、同義層、**四字**反義尾
- 無穩定四字反義時可出較短尾；仍須真相反
- 禁 guotong／第三方表 few-shot
- 可附近義鄰語境

Batch meta 的 `prompt_path` / `prompt_sha256` 必須指此檔（唔用通用 `project-antonyms-prompt.txt`）。

**完成定義**：檔入 git；首批 meta 綁定其 sha256。

---

### WP-05 — 審定流程（運維，非大段新碼）

每批（~500 未裁定頭）標準流水線：

```text
campaign-unresolved --campaign len4 --batch-index N --list-heads
  → 盲生成（prompt-len4；可附 syn neighbors）
  → filter（既有硬過濾：membership、syn 衝突、每頭 ≤5…）
  → 人工／A–D：四字尾優先保留；短尾可留
  → 合格對 append project_antonyms.tsv + batches[len4-bNN-…]
  → 其餘 head → no_natural append campaign_len4_no_natural.tsv
  → sample + quality-check / no-natural-validate（≥0.90）
  → campaign-validate --campaign len4
```

**軟偏好落地（本期）**：

- Prompt + 審核 checklist  
- 可選小工具：`prefer_len4_tails(proposals) -> ordered`（穩定排序：四字尾先、再字面），**唔**改 runtime  
- **唔**因只有短尾而改判 no_natural

**batch 建議**：

| 批 | batch_index | 說明 |
|----|-------------|------|
| 繼承 | — | freeze 時一次寫入 |
| len4-b01… | 1… | Essay 最高頻未裁定 |
| … | | 末批 residual |
| final | — | 全 resolved 後 final-sample + final-validate |

約 `ceil(3200/500) ≈ 7` 資料批（視 freeze k 與繼承／中途 accepted）。

**完成定義**（單批）：meta `ok_rate>=0.9`、TSV validate 過、progress 該批 unresolved 下降。

---

### WP-06 — 測試

| 測試 | 斷言 |
|------|------|
| 回歸 | 現有 top5000 smoke 全綠 |
| `rank` len4 | 全部 head `len==4`；有 syn；無直連（排除 project 後） |
| freeze 形狀 | `sum(batch_counts)==k`；末批 ≤500；前批 =500（或 k&lt;500 單批） |
| 繼承 | 把 top5000 no-natural 的四字頭 seed 進 len4 檔後，progress 計 resolved |
| 平行路徑 | validate `--campaign len4` 唔讀錯 top5000 manifest |
| 終局衝突 | 同 head 同時 accepted∩no_natural → fail |
| CLI smoke | freeze dry 到 tmp（可用 fixture db／mock essay） |

---

### WP-07 — 文件

| 項 | 動作 |
|----|------|
| `CONTEXT.md` | ✅ 已寫 **四字缺直連反義 campaign**、**四字尾軟偏好** |
| `THIRD_PARTY_NOTICES.md` | 僅當新第三方源；本期通常 **唔改** |
| Release note（達標後） | 寫「len4 缺直連母體已裁定」+ 驗證指令 |
| 本計劃 | 實作中更新狀態勾選 |

**ADR**：不開（同構延伸，無新架構取捨）。

---

### WP-08 — 收官與發佈閘

1. `campaign-validate --campaign len4 --require-complete`
2. `campaign-final-sample --campaign len4 --require-complete --seed …`
3. 人工填 final audit meta（Acc／Nn 分層 ≥90%）
4. `campaign-final-validate --campaign len4 --require-complete`
5. 關係 rebuild／Release 詞庫後，`!` 先睇到新 `project_ant`（清單完成 ≠ runtime 可見——既有契約）
6. **唔**把 len4 complete 當成關橋／衍生閘

---

## 5. 建議實作順序（日曆感）

```text
Day 0   CONTEXT ✅；本計劃入庫
Day 1   WP-01 Spec 泛化 + 回歸綠
Day 1–2 WP-02 CLI + WP-03 繼承 + WP-06 測試
Day 2   WP-04 prompt；真正 freeze commit（釘 k／hashes）
Day 3+  WP-05 循環批（每批：生成→審→閘→push dev）
最後    WP-08 收官；release note；可選 PR → main
```

Lexeme 研究／PR **並行、不阻塞** 上述日曆。

---

## 6. 風險與緩解

| 風險 | 緩解 |
|------|------|
| 四字 opaque → 大量 no_natural | 預期內；能配則配；文案唔講「都有反義」 |
| 末批 / 非 500 整除破壞 validate | WP-01 明確 residual 契約 + 測試 |
| 共用 no_natural 檔炸 progress | 平行檔 + 繼承 seed（§3.2） |
| Top-5000 回歸 | default `--campaign top5000`；固定 k 測試 |
| 假對仗成語對 | A–D + 專用 prompt；抽樣 ≥90% |
| 缺端唔在詞庫 | 既有：先 curated 標音／重建再入清單；對級拆出 |
| 母體滑動 | freeze 後只認 manifest；唔重跑 rank 改集合 |
| Essay 噪聲四字（「回覆日期」） | 母體契約包含之；無反義則 no_natural |

---

## 7. 驗證指令（目標態）

```bash
# 工具回歸
python -m unittest tests.smoke.test_project_antonyms_campaign -q
python -m unittest tests.smoke.test_project_antonyms_batch -q

# Freeze（僅一次，釘死後入 git）
python scripts/project_antonyms.py campaign-freeze --campaign len4 --db lyrics.db

# 進度
python scripts/project_antonyms.py campaign-validate --campaign len4
python scripts/project_antonyms.py campaign-unresolved --campaign len4 --batch-index 1 --list-heads

# 批後
python scripts/project_antonyms.py validate
python scripts/project_antonyms.py campaign-validate --campaign len4

# 收官
python scripts/project_antonyms.py campaign-validate --campaign len4 --require-complete
python scripts/project_antonyms.py campaign-final-validate --campaign len4 --require-complete
```

---

## 8. 勾選清單

- [x] WP-01 CampaignSpec + residual batch（PR-A）
- [x] WP-02 CLI `--campaign`（PR-A）
- [x] WP-03 len4 no-natural 平行檔 + 繼承 helper（PR-A；freeze 產物待首次 freeze commit）
- [x] WP-04 prompt-len4（PR-A）
- [x] WP-06 測試綠（PR-A；Len4CampaignTests + top5000 回歸）
- [x] Freeze commit（manifest + meta + inherited nn）— **PR-B**（k=2898，6 批，繼承 nn=15）
- [x] WP-05 各批 accepted / no_natural + 閘 — **b01–b06 done** — campaign-validate --require-complete **passed**（2026-07-15）
- [x] WP-08 最終稽核 — Acc 285/300 (0.95)、Nn 300/300；campaign_len4_final_audit.meta.json
- [ ] Release note（可選版本）

---

## 9. 一條指令起手（WP-01 開工時）

```text
1. 讀 ingest/project_antonyms_campaign.py 內 CAMPAIGN_K / validate_campaign_meta / rank_campaign_heads
2. 引入 CampaignSpec；top5000 路徑行為 bit-identical
3. 加 length_filter=4 + full_set + residual batch
4. 補 smoke；全綠再動 CLI
```

**Out of scope for first PR（建議拆 PR）**

| PR | 內容 |
|----|------|
| **PR-A（工具）** | WP-01–04、06 + 空／繼承 freeze 可選 |
| **PR-B+（資料）** | 各 len4-bNN 批 TSV／meta（可多 PR） |
| **PR-Z（收官）** | final audit + release note |
| **另** | Lexeme P5974 研究／計量 |

---

*Grill 決策以 2026-07-15 session 為準；與本文件衝突時以 `CONTEXT.md` 領域定義為先，再改本計劃。*
