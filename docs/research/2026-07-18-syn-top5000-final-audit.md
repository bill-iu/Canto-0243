# syn_top5000 campaign 最終稽核（2026-07-18）

**結論：syn_top5000 final audit PASSED**（三終局 ok_rate 皆 ≥ 0.9）。  
**Apply 已落地**（2026-07-18，`scripts/_syn_top5000_final_audit_apply.py`；未 commit）。

## 完成度

| 終局 | 頭數 | 互斥 |
|------|------|------|
| accepted（`project_synonyms.tsv`，`syn-top5000-*`） | 781 | ✓ |
| no_natural | 350 | ✓ |
| adequate_existing | 17 | ✓ |
| **合計** | **1148／1148** | 無缺漏、無雙終局 |

分層鍵：`campaign_syn_top5000.tsv` 的 `batch_index`（accepted 按 TSV **head／batch_id** 歸層，唔用無向 min，避免兩端皆 campaign 頭時漂層）。

## 抽樣

- seed = `20260718`；層 seed = `20260718 + batch_index`
- 每層 `sample_size_for` = `min(n, max(50, ceil(n*0.05)))`
- 樣本 fixture：
  - `data/syn_ant/project/fixtures/syn_top5000_final_audit_accepted_sample.tsv`
  - `..._no_natural_sample.tsv`
  - `..._adequate_sample.tsv`
- 可重跑：`PYTHONIOENCODING=utf-8 python scripts/_syn_top5000_final_audit_sample.py`
- Meta builder：`scripts/_syn_top5000_final_audit_build_meta.py`
- Meta：`data/syn_ant/project/campaign_syn_top5000_final_audit.meta.json`

## 總表

| 終局 | sample_n | ok | fail | ok_rate | ≥0.9 |
|------|----------|-----|------|---------|------|
| accepted | 300 | 270 | 30 | 0.9000 | ✓ |
| no_natural | 265 | 240 | 25 | 0.9057 | ✓ |
| adequate_existing | 17 | 16 | 1 | 0.9412 | ✓ |

## Accepted fails（30）

剔除任一對會令該 **唯一** accepted 頭變未裁定（每頭恰 1 對）；須同時改判 `no_natural`／另覓合格尾，或接受暫時 unresolved。

| head | tail | reason |
|------|------|--------|
| 你好 | 問好 | 招呼語 vs 動詞「問好」，唔可獨立替換 |
| 呻吟 | 哼 | 程度／窄化，唔係同義層近義 |
| 師兄 | 師弟 | 輩分對立，非近義 |
| 打機 | 遊戲 | 動詞 vs 名詞，詞性／論元唔同 |
| 熊仔 | 熊 | 上下位（細稱→類名） |
| 狗仔 | 犬 | 上下位；且「狗仔」可指狗仔隊 |
| 相機 | 攝影機 | 相關器材，非可替換近義 |
| 社會 | 世上 | 相關域，非同義層 |
| 車站 | 火車站 | 上下位（泛稱→火車專稱） |
| 音樂 | 歌曲 | 上下位／相關（音樂≠一首歌） |
| 嘴角 | 口角 | 「口角」常指爭執，替換唔穩定 |
| 大小姐 | 小姐 | 程度／上下位 |
| 接住 | 接著 | 異義（接住≠接著） |
| 校車 | 公車 | 相關／上下位（校車≠公車） |
| 西瓜 | 瓜 | 上下位 |
| 貓仔 | 貓 | 上下位 |
| 鴨仔 | 鴨 | 上下位 |
| 版主 | 樓主 | 論壇角色不同，非近義 |
| 發票 | 收據 | 相關單據，非近義 |
| 身高 | 高度 | 相關量度，人高≠泛高度 |
| 銅 | 黃銅 | 金屬種類不同／上下位 |
| 世紀 | 時代 | 相關時間單位，非近義 |
| 男神 | 偶像 | 相關／窄化（男神≠泛偶像） |
| 神父 | 牧師 | 宗教職銜不同 |
| 立法 | 制定 | 相關／上下位（立法≠泛制定） |
| 客服 | 服務員 | 職銜近似，非近義 |
| 正所謂 | 所謂 | 「所謂」常貶義，唔等同「正所謂」 |
| 陰道 | 產道 | 相關解剖，填詞唔可穩定替換 |
| 輸入法 | 打字法 | 相關技術，非近義 |
| 高中 | 中學 | 上下位（高中⊂中學） |

## no_natural fails（25）

| head | 原 reason | 問題 |
|------|-----------|------|
| 下次 | no_stable_near_synonym | 應 accepted：「下回」 |
| 會話 | no_stable_near_synonym | 應 accepted：「對話」 |
| 好少 | no_stable_near_synonym | 應 accepted：「很少」 |
| 踢波 | no_stable_near_synonym | 應 accepted：「踢球」 |
| 無人 | no_stable_near_synonym | 應 accepted：「沒人」 |
| 點講 | no_stable_near_synonym | 應 accepted：「怎麼說」 |
| 夜貓 | no_stable_near_synonym | 應 accepted：「夜貓子」 |
| 握手 | function_word | reason 唔貼（實義動詞） |
| 考研 | function_word | reason 唔貼 |
| 荃灣 | function_word | 應 proper_name_or_deixis |
| 設計師 | function_word | reason 唔貼 |
| 陰毛 | function_word | reason 唔貼 |
| 冷汗 | function_word | reason 唔貼 |
| 情人節 | function_word | 節日專名，reason 唔貼 |
| 九龍 | function_word | 應 proper_name_or_deixis |
| 淘寶 | function_word | 應 proper_name_or_deixis |
| 柯南 | function_word | 應 proper_name_or_deixis |
| 話費 | function_word | reason 唔貼 |
| 車型 | function_word | reason 唔貼 |
| 麻甩佬 | function_word | reason 唔貼 |
| 做愛 | function_word | reason 唔貼 |
| 射出 | function_word | reason 唔貼 |
| 嬴 | function_word | reason 唔貼 |
| 搖搖板 | function_word | reason 唔貼 |
| 關我事 | function_word | 宜 other_documented |

## adequate fails（1）

| head | note | 問題 |
|------|------|------|
| 欄目 | prior project_syn edge covers head（節目↔欄目） | 「節目」相關非近義；不應裁 adequate |

## Apply 結果（已執行）

| 動作 | 結果 |
|------|------|
| 剔 accepted 弱對 | 30＋`節目↔欄目`＝**31**；freed 頭改判 `no_natural` |
| nn→accepted | **好少→稀少**、**無人→冇人**（詞庫成員資格 OK）；`會話` 已由 `對話↔會話` 覆蓋，自 nn 刪除 |
| nn 翻案受阻 | `下次`／`踢波`／`點講`／`夜貓` 建議尾不在詞庫 → 維持 `no_stable_near_synonym` |
| nn reason 修正 | 專名→`proper_name_or_deixis`；其餘誤標 `function_word`→`no_stable_near_synonym`／`other_documented` |
| adequate | `欄目`→`no_natural` |
| 完成度 | **1148／1148**（pairs **752**；acc 頭 760／nn 372／adq 16） |

可選：重抽最終稽核樣本鎖帳。未 commit。
