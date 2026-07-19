# nf_batches_full_gate — audit_part2 (u-inlex-nf2b)

**File:** `data/pos/audit/nf_batches_full_gate/audit_part2.tsv`  
**Batch:** `u-inlex-nf2b`  
**n:** 100  
**Rules:** n/v/a/r/x；multi only if both common；wrong primary / toxic multi → BAD+`fix_pos`；borderline → SOFT  
**Threshold:** ok_rate = (OK+SOFT)/n ≥ 0.90  

## Counts

| verdict | n | % |
|---------|--:|---:|
| OK | 95 | 95% |
| SOFT | 2 | 2% |
| BAD | 3 | 3% |
| **total** | **100** | 100% |

**ok_rate = 97/100 = 0.9700**

**PASS**

## BAD detail

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 乜料 | n,x | n | x 假陽；主用名詞（搞乜料／乜料嚟）；疑問口語非助詞 |
| 援手 | n,v | n | v 假陽；主用名詞（伸出援手／予以援手）；動作用援助 |
| 由來已久 | a,r | a | r 假陽；成語偏 predicative stative a（問題由來已久）；非情狀副 |

## SOFT

| literal | was | reason |
|---------|-----|--------|
| 心有靈犀 | a,n | a 主；n 弱（心有靈犀一點通偏 stative） |
| 恐襲 | n,v | n 主；v 新聞略語薄（恐襲巴黎） |

## Error patterns (BAD)

1. **假陽 x on 粵語名詞**（1/3）— `乜料`：內容名詞／疑問賓語，非助詞桶  
2. **假陽 v on 純名**（1/3）— `援手`：固定搭配名物，動詞義由「援助」承擔  
3. **假陽 r on stative 成語**（1/3）— `由來已久`：謂語形容，非副詞修飾

## OK patterns worth keeping

- Clear n / 專名／政經 NP：中心地帶、保時捷、信用等級、兒子、內需、勞斯萊斯、十二生肖、哈根達斯、國家公園、恐怖襲擊、資料庫、響應時間、鼓樓…
- Clear a / stative 成語：乖巧、傷心欲絕、天真無邪、孤陋寡聞、年邁、意味深長、朝氣蓬勃、欲哭無淚、觸目驚心、火熱
- Clear v / 謂語成語：一無所獲、出氣、分道揚鑣、包庇、想方設法、發揚光大、舞文弄墨、搶走、復牌、鋪設
- True multi（兩標皆常見）：全日制 a,n；公投 n,v；凡事 n,r；半夜三更 n,r；合規 a,n；好事 a,n；明確 a,v；登入 n,v；獨資 a,n；過分 a,r；診療／集訓／雜交 n,v；缺一不可／身臨其境／兩敗俱傷 a,v
- r 時間／程度：將要、從小到大、逢年過節、過於

## Apply note

```text
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/nf_batches_full_gate/audit_part2.tsv --dry-run
```

3 列 BAD（`fix_pos` 如上；family 保持 idiom 於 `由來已久`）後本抽樣 ok_rate 可升至 **0.97→1.00**（SOFT 仍計可接受）。
