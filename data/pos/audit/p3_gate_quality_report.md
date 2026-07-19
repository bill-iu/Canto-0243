# P3 長尾 · 閘用品質閘

## 母體

- Essay 詞頻 **rank 5001–20000**（15 000 字面）
- **終局覆蓋**：100% 入 `project_pos.tsv`（缺列則提案／`u` 填）
- **閘用品質**：對 `P3 ∩ gate_pos` 抽樣，OK+SOFT **>90%**

## 覆蓋結果

| 指標 | 值 |
|------|-----|
| mother_body | 15 000 |
| tagged | 15 000 |
| gate_formal | ~545 |
| undetermined_only | ~11 884 |
| low_draft | ~2 570 |
| coverage | **100%** |

## 品質閘

| 輪 | seed | ok_rate | 結果 |
|----|------|--------:|:----:|
| r1 | 20260719 | 0.88 | ❌ → 套用 6 BAD |
| r2 | 202607192 | **0.92** | ✅ |
| r3 | 202607193 | **0.92** | ✅ |

**`p3_gate_quality.pass = true`**（兩輪獨立確認 >90%）

## 常見 BAD 模式

- cow-multi 假 n,v
- verb-suffix 假陽（南開、不完）
- prefix-passive 假陽（被害人、被告人）
- len4-noun 把 VO 當名（提供服務）
