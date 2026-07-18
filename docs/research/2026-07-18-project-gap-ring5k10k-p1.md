# P1：Essay 5k–10k post-syn「有近無反」ring

**日期**：2026-07-18  
**承接**：Top-5k content 已由 post-syn b01–b05 清零（見 `2026-07-18-project-gap-post-syn-ant.md`）

## 母體定義

- Essay 詞頻排名 **5001–10000**  
- 字面長度 **≥2**  
- 有直連近義（DB ∪ cilin ∪ guotong ∪ project_syn）  
- 無直連反義（同上 + project_ant）  
- 未入 `no_natural`  

**Freeze 量度（b01 開批前）**：open content **1600**／5000  
全表：`data/syn_ant/fixtures/post_syn_ant_ring5k10k_open.tsv`

字長：len2 ≈ 1368，len3 ≈ 213，len4 ≈ 19。  
注意：部分 syn 鄰來自詞林雜訊（地名／軍種 cluster），入帳時優先粵語填詞可用對。

## b01（已落地）

| 項目 | 內容 |
|------|------|
| batch_id | `post-syn-ant-ring5k10k-b01-20260718` |
| 種子 | Top-150 of open freeze |
| 入帳 ant | **39** 對 |
| no_natural | **128** 頭（名詞／專名／功能詞） |
| sample | 39／39 ok，threshold 0.9 |

代表：`體內–體外`、`唔經唔覺–故意`、`做主–聽話`、`這次–上次`、`陌生人–熟人`、`入場–離場`、`原先–而家`、`女主角–男主角`

## 下一步

1. **rebuild** 關係／`lyrics.db`  
2. **ring b02**：open 餘下高頻段（~1600−150 處置）  
3. 唔開 UD  
