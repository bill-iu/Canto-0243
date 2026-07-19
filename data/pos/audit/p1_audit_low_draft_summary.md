# P1 POS audit — stratum `low|draft`

**日期**：2026-07-18  
**樣本**：[`p1_sample_low_draft.tsv`](./p1_sample_low_draft.tsv)  
**母體層**：`low|draft`（COW 單標起草；唔入硬閘／創作者 chips）  
**母體／抽樣**：universe 1459 · sample 73（seed=20260718；見 `p1_sample.meta.json`）  
**標籤閉集**：`n` 名 · `v` 動 · `a` 形 · `r` 副 · `x` 虛 · `u` 未定  

## 準則

| verdict | 含義 |
|---------|------|
| **OK** | primary 正確；日後升 trust 可原樣用 |
| **SOFT** | primary 可接受，但常見多類／缺副標；升 trust 前宜補多標 |
| **BAD** | primary 錯；`fix_pos` 供升 trust／`apply` 用 |

SOFT 計入可接受率（與 `ingest.project_pos_audit.apply_verdicts_file` 一致）。本層唔強制 apply；BAD 列先落 audit，待維護者決定是否 `project_pos_audit apply`。

## 結果

| 指標 | 數值 |
|------|------|
| audited | **73** |
| OK | **59** |
| SOFT | **7** |
| BAD | **7** |
| ok+soft | **66** |
| **ok_rate**（含 SOFT） | **90.4%**（66／73） |
| 純 OK 率 | 80.8%（59／73） |
| BAD 率 | **9.6%**（7／73） |

對齊 p0 註解「cow-single ~13% primary error」：本抽樣 BAD≈10%，同量級。

## BAD（primary 錯 → fix_pos）

| literal | draft | fix_pos | 理由 |
|---------|-------|---------|------|
| 即時 | n | **a,r** | 即時＝形／副；名義用「瞬間」 |
| 喂 | n | **x,v** | 主嘆（虛）；餵食義為動；非名 |
| 基於 | v | **x** | 介／虛（based on），非動 |
| 最少 | n | **r** | at least＝副（可再加 a） |
| 無助 | n | **a** | 形（感到無助） |
| 發燒 | n | **v,n** | 主動（我發燒）；病名可附 n |
| 簡單 | n | **a** | 形，非名 |

**模式**：COW 單標把形／副／介誤收成 **n** 或把介誤收成 **v**（7 宗中 5 宗 n 假陽性）。

## SOFT（primary 可留，升 trust 宜補）

| literal | draft | 建議 | 理由 |
|---------|-------|------|------|
| 一點 | n | n,r | 副詞「一點也不」常見 |
| 串 | n | n,v | 動「串連」常見 |
| 判斷 | n | n,v | 動用法常見 |
| 報告 | n | n,v | 動用法常見 |
| 大部份 | r | n,r | 名物用法近「大多數」 |
| 沉默 | n | n,a／n,v | 形／動常見 |
| 站 | v | v,n | 站點／車站義 |

## 觀察

1. **多數 cow-single 名／動主標可用**：實體名（子彈、迷宮、鼠標…）同典型動（偷、買、看…）OK。  
2. **形被標成名**係主要噪音：簡單、無助（同 p1 提案池所見 嚴重／熟悉 等模式一致）。  
3. **虛詞漏桶**：基於、喂 應入 `x`。  
4. **本層政策**：維持 low trust；BAD 只寫 audit，**未**改 `project_pos.tsv`（避免未確認 apply 抬 trust）。  
5. 若要落地修正：  
   `python -m ingest.project_pos_audit apply --verdicts data/pos/audit/p1_sample_low_draft.tsv`  
   （會把 BAD+fix_pos 升為 review／high；先 `--dry-run`）。

## 下一步（非本檔範圍）

- 同批其他層：`high|gate`、`medium|gate`、`low|u`  
- 可選：對 BAD 七詞手動／apply 入 SSOT 後重 bake 詞性載體  
