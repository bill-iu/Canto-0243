# alias_proposals 人手審核 r4（最後 6 條 · 收尾）

**Source:** `propose --min-score 0.2` 剩餘 6 條  
**準則：** residual alias 只收「半截→唯一完整詞」；自由語素改 **formal POS**，唔 alias  
**Date:** 2026-07-19  

## 結論

| 判決 | n |
|------|--:|
| ACCEPT alias | **0** |
| REJECT alias | **6** |
| 改 formal POS（離開 u） | **6** |

## 逐條

| source | 曾提案 target | alias | formal | 理由 |
|--------|---------------|-------|--------|------|
| 喃 | 喃喃 | REJECT | **x** | 疊字 AA，非半截；擬聲／狀態小品 |
| 騷 | 騷擾 | REJECT | **a,v** | 口語可自由用（風騷／好騷）；alias 會毒自由義 |
| 薦 | 推薦 | REJECT | **v** | 舉薦等自由語素 |
| 醋 | 呷醋 | REJECT | **n** | 自由名詞「醋」；呷醋＝動賓 |
| 敞 | 敞開 | REJECT | **a** | 另有寬敞；形語素 |
| 嫂 | 嫂子 | REJECT | **n** | 面稱「X嫂」自由；唔鎖 嫂子 |

## 收尾狀態

- `alias.tsv` 維持 **15** 行（r3 後無新增）  
- 6 源字 **pos≠u** → `propose` 唔再出（ exhaust residual 佇列）  
- 提案檔可空或僅低分噪音  

## 之後要唔要再開 Essay top-N？

見同 commit 回應／下節決策建議。
