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

## b02（已落地）

| 項目 | 內容 |
|------|------|
| batch_id | `post-syn-ant-ring5k10k-b02-20260718` |
| b01 後 open | **~1450** |
| 入帳 ant | **34** 對 |
| no_natural | **125** 頭 |
| sample | 34／34 ok |

代表：`不在乎–在乎`、`停下–繼續`、`出走–回來`、`登出–登入`、`草草–仔細`、`萬能–無能`、`親愛–憎恨`、`上調–下調`、`麻醉–清醒`

## b03（已落地）

| 項目 | 內容 |
|------|------|
| batch_id | `post-syn-ant-ring5k10k-b03-20260718` |
| b02 後 open | **~1300** |
| 入帳 ant | **29** 對 |
| no_natural | **130** 頭 |
| sample | 29／29 ok |

代表：`迷茫–清晰`、`過癮–掃興`、`男孩子–女孩子`、`看重–輕視`、`思念–忘記`、`塞車–暢通`、`弱智–聰明`、`關愛–冷漠`

## b04（已落地 · batch=500 頭）

| 項目 | 內容 |
|------|------|
| batch_id | `post-syn-ant-ring5k10k-b04-20260718` |
| 本批處置頭數 | **500**（open Top-500） |
| 入帳 ant | **163** 對（覆蓋 ~94 頭） |
| no_natural | **406** 頭 |
| 本批合計處置 | **500／500** |
| sample | 50／50 ok |

策略：batch 擴大至 **500 詞／批**；可對則 ant，其餘 bulk `no_natural`。

## b05（已落地 · batch=500 頭）

| 項目 | 內容 |
|------|------|
| batch_id | `post-syn-ant-ring5k10k-b05-20260718` |
| 本批處置頭數 | **500／500** |
| 入帳 ant | **~154–163** 對 |
| no_natural | **410** 頭 |
| sample | 50／50 ok |

## b06（已落地 · P1 收官）

| 項目 | 內容 |
|------|------|
| batch_id | `post-syn-ant-ring5k10k-b06-20260718` |
| 本批處置頭數 | **147／147**（全部剩餘 open） |
| 入帳 ant | **121** 對 |
| no_natural | **94** 頭 |
| sample | 50／50 ok |
| **P1 open 後** | **0** |

## 累計 P1（Essay 5k–10k）

| | open |
|--|------|
| freeze | 1600 |
| 後 b01–b03（小批） | 1150 |
| 後 b04（500） | 648 |
| 後 b05（500） | 147 |
| **後 b06 收官** | **0** |

## 下一步

1. **rebuild** 關係／`lyrics.db` 令 runtime 見新邊  
2. 可選更低頻 ring（Essay 10k+）— YAGNI 除非有需求  
3. 唔開 UD  





