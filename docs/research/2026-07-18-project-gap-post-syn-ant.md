# 最大缺口盤點（放棄 UD）＋ post-syn 自建反義首批

**日期**：2026-07-18  
**決策**：唔引入 [ckiplab/ud](https://github.com/ckiplab/ud)；改量度近反義覆蓋，用**專案自建**補洞。  
**可重跑基線**：`python scripts/research/project_syn_sparse_measure.py`  
**本批產物**：`project_antonyms.tsv` batch `post-syn-ant-b01-20260718`（62 對）＋ `project_no_natural_antonyms.tsv`（44 頭）

---

## 1. 四大 freeze campaign 狀態（正規化後）

量度鍵一律經 `normalize_literal`（避免 溫柔／因為 等異體誤報未解決）。

| Campaign | 母體 | has_ant / 非過稀 | no_natural（∩） | **未解決** |
|----------|------|------------------|-----------------|------------|
| 高頻反義 top5000 | 5000 | 2216 has_ant | 3048 | **0** |
| 四字反義 len4 | 2898 | 1775 has_ant | 1124 | **0** |
| 高頻近義 syn_top5000 | 1148 | disposition ≈ 全數 | nn 372 + adeq 15 | 會計完成（多數仍 sparse thr&lt;2，預期） |
| 四字近義 syn_len4 | 5000 | disposition 完成 | nn 3549 + adeq 111 | 會計完成 |

**結論**：既有 campaign **唔再係最大缺口**；誤報「89 未解決」來自 **未 normalize 嘅 manifest 字面**，唔係真缺邊。

`project_*` 清單套入 membership：**ant 5986／0 fail，syn 2034／0 fail**。

---

## 2. 產品殘餘（DB ∪ 靜態詞林 ∪ 自建清單）

Essay 詞頻排名、兩端 ∈ 詞庫字面：

| 母體 | syn 過稀（尾&lt;2） | has_syn_no_ant | 其中未入 nn 且 **len≥2**（可填內容詞） |
|------|-------------------|----------------|----------------------------------------|
| Essay Top-5000 | 1045 | 2690 | **558** |
| Essay 5001–10000 | 1523 | 2542 | **1601** |
| Essay 10001–20000 | 3478 | 5904 | 5195 |

單字功能詞／助詞（你、唔、呢…）多數應 `no_natural`，**唔**再硬砌反義。

### 點解 Top-5000 反義 campaign 完咗仲有 558？

時間序：

1. 反義 freeze 種子＝當時「有近無直連反」  
2. 其後 **專案自建近義** 為大量粵語口語配上近義（如 唔係→不是、鍾意→喜歡）  
3. 呢批頭 **新晋** has_syn_no_ant，**從未**入 ant freeze  

→ **最大、最高頻、可自建補** 嘅缺口＝  
**post-syn「有近無反」粵語內容詞（Essay Top-5000 ∩ len≥2）≈ 558 頭**。

完整清單：[`2026-07-18-gap-post-syn-ant-top5k-content.tsv`](./2026-07-18-gap-post-syn-ant-top5k-content.tsv)

---

## 3. 缺口優先序（之後自建）

| 順位 | 缺口 | 規模 | 做法 |
|------|------|------|------|
| **P0** | post-syn 有近無反 · Essay Top-5k · len≥2 | ~558（本批後再量） | 自建 ant／no_natural 分批 |
| P1 | 同上 · Essay 5k–10k · len≥2 | ~1601 | 新 ring campaign（可另 freeze） |
| P2 | 近義 thr&lt;2 但仍要第二尾 | 低於 P0 | 只對填詞實用頭加第二 syn；其餘 adequate／nn |
| P3 | len4 長尾 | 大 | 維持現 campaign 完成即可；唔一次清算全庫 |
| — | UD／jieba／COW POS | — | **否**（假缺口） |

---

## 4. 本批自建（b01）

| 項目 | 內容 |
|------|------|
| batch_id | `post-syn-ant-b01-20260718` |
| 種子 | `data/syn_ant/fixtures/post_syn_ant_gap_top150.tsv`（558 頭中 Top-150） |
| 入帳 ant | **62** 對（filter 後再剔 5 弱對） |
| no_natural | **44** 頭（連詞／疑問／無穩定反義） |
| 抽樣閘 | N=62 → sample 50；ok 50；threshold 0.9；**ok_rate 1.0** |
| 剔除例 | 真係–唔係、兩個–一個、頭先–跟住、掛住–忘記、細妹–家姐 |

代表入帳：`唔係–係`、`唔好–好`、`鍾意–討厭`、`女仔–男仔`、`拍拖–分手`、`得閒–忙`、`污糟–乾淨`…

---

## 5. b02（已落地）

| 項目 | 內容 |
|------|------|
| batch_id | `post-syn-ant-b02-20260718` |
| b01 後殘餘 open | **~457**（由 ~558 下降） |
| 入帳 ant | **72** 對 |
| no_natural | **~69** 頭（名詞／功能詞無穩定反義） |
| 抽樣閘 | sample 50；ok 50；threshold 0.9 |
| validate | pairs **6120** ok |

代表：`細細聲–大聲`、`搞掂–搞唔掂`、`好靚–核突`、`落車–上車`、`在線–離線`、`老細–下屬`…

---

## 6. b03（已落地）

| 項目 | 內容 |
|------|------|
| batch_id | `post-syn-ant-b03-20260718` |
| b02 後殘餘 open | **~339** |
| 入帳 ant | **81** 對 |
| no_natural | **104** 頭 |
| validate | pairs **6201** ok |

代表：`怕醜–大膽`、`唔捨得–捨得`、`衰仔–乖仔`、`搞錯–正確`、`呢邊–那邊`、`廣東話–普通話`、`盡快–慢慢`…

## 7. b04（已落地）

| 項目 | 內容 |
|------|------|
| batch_id | `post-syn-ant-b04-20260718` |
| b03 後殘餘 open | **~188** |
| 入帳 ant | **89** 對 |
| no_natural | **104** 頭 |
| validate | pairs **6290** ok |

代表：`醜怪–靚`、`離遠–靠近`、`專登–無意`、`攬實–放開`、`匿埋–現身`、`落街–返屋企`、`未夠–夠`、`呷醋–放心`…

## 8. 累計 b01–b04

| batch | ant 對 | nn 約 |
|-------|--------|-------|
| b01 | 62 | 44 |
| b02 | 72 | 69 |
| b03 | 81 | 104 |
| b04 | 89 | 104 |
| **合計** | **~304** | **~321** |

母體由 ~558 content open 大幅清減。

## 9. 下一步

1. **rebuild** `lyrics.db`／Release 關係令 runtime 見到新邊。  
2. 重跑缺口量度（預計 Top-5k content open ≪ 188）。  
3. 可選 **b05** 收尾 Top-5k，或轉向 **Essay 5k–10k** ring（P1）。  
4. 勿開 UD。

---

## 6. 工程備註

- Campaign progress／缺口量度必須 **normalize 後再比 head**。  
- 工作樹若有其他無關改動，提交本批時只 stage `data/syn_ant/project_*`、fixtures、本 research 文。
