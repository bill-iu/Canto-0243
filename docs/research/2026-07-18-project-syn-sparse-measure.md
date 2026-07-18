# 專案自建近義：直連近義過稀基線量度

**日期**：2026-07-18  
**契約**：`CONTEXT.md` — **直連近義過稀**＝尾數 ＜2；常用＝Essay Top-5000 ∩ 過稀；成語＝len=4 proxy ∩ 過稀後再 Essay Top-5000；兩母體去重（高頻優先）  
**可重跑**：`python scripts/research/project_syn_sparse_measure.py`  
**產物**：[`2026-07-18-project-syn-sparse-measure.json`](./2026-07-18-project-syn-sparse-measure.json)、稀疏頭 TSV

## 結論摘要

| 母體 | 宇宙／候選 | 過稀或 freeze 規模 | 尾＝0 | 尾＝1 |
|------|------------|-------------------|-------|-------|
| Essay Top-5000 | 5000 | **1148** 過稀（22.96%） | 943 | 205 |
| len=4 全詞庫過稀 | 28728 字面 | **23381** 過稀（去重後 23368） | 22918 | 463 |
| **四字 campaign 擬 freeze** | 去重後過稀按 Essay 截斷 | **5000** | 4668 | 332 |

**裁決**：高頻 campaign 母體 ≈ **1148** 頭（可開戰）。全庫 len4 過稀 ≈ **23368** ≫ 5000 → **四字缺直連近義 campaign** 只 freeze Essay Top-5000（已寫入 `CONTEXT.md`），唔一次清算。

## 直連近義定義（本量度）

無向鄰接＝`word_relations` syn（兩端 ∈ 詞庫字面）∪ cilin syn ∪ guotong syn（兩端 ∈ 詞庫；字面經 `normalize_literal`）。  
尾數＝該頭唯一鄰居數。

## Top-5000 直連尾數分布

`{"0": 943, "1": 205, "11+": 2156, "2": 245, "3-5": 642, "6-10": 809}`

## 推進建議（對齊 grill）

1. 本報告＝量度閘；**尚未**正式 `campaign-freeze`。
2. 下一步：統一 CLI／資料夾骨架＋ **高頻近義 campaign**（終局含 `adequate_existing`）。
3. 高頻收官後再 freeze 四字 Top-5000。
