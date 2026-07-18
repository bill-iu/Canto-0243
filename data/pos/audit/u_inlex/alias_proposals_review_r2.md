# alias_proposals 人手審核 r2（IWP 評分）

**Source:** `python -m ingest.project_pos_alias propose`（IWP + affinity，min_score=0.2）  
**Date:** 2026-07-19  

## 機制

- Essay 估 **IWP(c)=N(Word(c))/N(c)**（`data/pos/iwp_char.tsv`）
- **affinity** = freq(target)/N(c)：字質量否集中喺呢個雙字詞
- 高 IWP（≥0.55）自由語素預設丟棄；低 IWP 但低 affinity → 生產性語素（潔／顯）降分
- **只提案、唔自動 apply**

## 結果摘要

| | n |
|--|--:|
| 提案（min_score 0.2） | 33 |
| 低分略過 | ~264 |
| **ACCEPT 本輪** | **5** |

## ACCEPT

| source | target | 理由 |
|--------|--------|------|
| 蝶 | 蝴蝶 | 典型殘字；IWP 低 |
| 玫 | 玫瑰 | 同上 |
| 眶 | 眼眶 | 同上 |
| 咖 | 咖啡 | 曾 opaque；IWP+affinity |
| 蠱 | 整蠱 | 粵語固定；IWP+affinity |

## 明確 REJECT（高分噪音）

喪→喪屍、拒→拒絕、決→決定、棄→放棄、休→休息、顯→明顯、責→負責… — 自由／生產性語素，affinity 來自高頻複合但唔係「只係半截」。

## CLI

```text
python -m ingest.project_pos_iwp build
python -m ingest.project_pos_iwp lookup 曱蘿蝶
python -m ingest.project_pos_alias propose
python -m ingest.project_pos_alias propose --keep-free --min-score 0.1
```
