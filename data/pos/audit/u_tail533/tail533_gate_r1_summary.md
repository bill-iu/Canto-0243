# 長尾 533 `u` 修復／審核

## 盤點

| 桶 | n | 處理 |
|----|--:|------|
| plain_u（零 Essay 頻、真詞／成語／粵語） | 508 | agent formal 標註 |
| fragment（既定政策） | 25 | **保留 `u`** |

## G1

**Sample:** n=50 · **ok_rate = 1.0** · **PASS**  
SOFT: 不分皂白 · 實存 · 一桿入洞

## 結果

| metric | value |
|--------|------:|
| formal applied | 508 |
| SSOT `u` | 533 → **25** |
| formal/all | **0.999** |
| formal/(all−fragment) | **1.0** |
| D4 | 仍 PASS（且非 fragment 全 formal） |

## 剩餘 25 = 僅 fragment

- **clause-slice (18):** 我見／你估／將我／個月／講乜／國內生產／直角三角…  
- **opaque (5):** 然／企響度／咇／拉西／關斗  
- **residual (2):** 踊（踊躍未入庫）、魍（魍魎未入庫）  

唔再批量 formal 毒閘；殘字完整詞若日後 curated 再 alias。
