# syn_len4 campaign 最終稽核（2026-07-18）

## 結論（reaudit 鎖帳）

| 輪次 | seed | Acc | Nn | Adequate | 閘 |
|------|------|-----|-----|----------|-----|
| 首輪 formal | 20260718 | 450/500 (0.9000) | 476/500 (0.9520) | 108/126 (0.8571) | **FAILED**（adeq） |
| 首輪 apply | — | 剔弱對 64；nn→acc 13；nn→adq 7；adq→nn 18 | | | `remediated_pending_reaudit` |
| **Reaudit** | **20260719** | **466/500 (0.9320)** | **495/500 (0.9900)** | **111/115 (0.9652)** | **PASSED** |
| Reaudit apply | — | 剔 37 對；nn→acc 5；adq fails 4→nn | | | `passed_cleaned` |

**現況：syn_len4 final audit PASSED**（reaudit 三終局 ok_rate 皆 ≥ 0.9；cleanup apply 已落地；未 commit）。

歷史首輪樣本／判決保留於 `campaign_syn_len4_final_audit.meta.json` → `first_audit`。

---

## 完成度（reaudit apply 後）

| 終局 | 頭數 | 互斥 |
|------|------|------|
| accepted（`project_synonyms.tsv`，`syn-len4-b0N`／final-audit／reaudit） | 1340 | ✓ |
| no_natural | 3549 | ✓ |
| adequate_existing | 111 | ✓（皆有直連覆蓋） |
| **合計** | **5000／5000** | 無缺漏、無雙終局 |

分層鍵：`campaign_syn_len4.tsv` 的 `batch_index`（accepted 按 **manifest head** 歸層；含 only-tail 覆蓋邊）。

---

## Reaudit 抽樣

- seed = `20260719`；層 seed = `20260719 + batch_index`
- 每層 `sample_size_for` = `min(n, max(50, ceil(n*0.05)))`；adeq N=115 全抽（分層）
- 樣本 fixture：
  - `data/syn_ant/project/fixtures/syn_len4_final_audit_accepted_sample.tsv`
  - `..._no_natural_sample.tsv`
  - `..._adequate_sample.tsv`
- 可重跑：`PYTHONIOENCODING=utf-8 python scripts/_syn_len4_final_audit_sample.py`
- Meta builder：`scripts/_syn_len4_final_audit_build_meta.py`
- Meta：`data/syn_ant/project/campaign_syn_len4_final_audit.meta.json`
- 抽樣腳本 post-apply 修正：nn／adq 唔再只認 `bNN` batch_id；accepted 終局用 undirected coverage；only-tail 頭補覆蓋邊

### Reaudit 總表

| 終局 | sample_n | ok | fail | ok_rate | ≥0.9 |
|------|----------|-----|------|---------|------|
| accepted | 500 | 466 | 34 | 0.9320 | ✓ |
| no_natural | 500 | 495 | 5 | 0.9900 | ✓ |
| adequate_existing | 115 | 111 | 4 | 0.9652 | ✓ |

### Accepted fails（34）

| head | tail | reason |
|------|------|--------|
| 關鍵問題 | 基礎問題 | 關鍵≠基礎，相關非近義 |
| 人仔細細 | 小心翼翼 | 仔細形貌／態度≠小心翼翼動作 |
| 健健康康 | 健康 | 重疊詞≠基形 |
| 家庭教師 | 補習老師 | 家教≠補習班老師 |
| 和平共處 | 長期共存 | 和平≠長期共存 |
| 無處可逃 | 無處可尋 | 逃≠尋 |
| 逆流而上 | 逆風而行 | 逆流≠逆風 |
| 邊遠地區 | 邊緣地區 | 邊遠≠邊緣 |
| 數字通信 | 數據通信 | 數字≠數據 |
| 立法機關 | 議會 | 體制／範圍唔同 |
| 長途旅行 | 長途跋涉 | 旅行≠跋涉 |
| 威風八面 | 威風凜凜 | 八面≠凜凜 |
| 牛肉拉麪 | 牛肉麵 | 上下位 |
| 交通擁擠 | 擁擠不堪 | 程度 |
| 刻苦努力 | 刻苦耐勞 | 努力≠耐勞 |
| 經濟落後 | 貧窮落後 | 經濟≠貧窮 |
| 高等植物 | 維管束植物 | 技術近義但唔可穩定替換 |
| 不成氣候 | 不成器 | 氣候≠器 |
| 事隔多年 | 事過境遷 | 隔年≠境遷 |
| 雷雨交加 | 風雨交加 | 雷雨≠風雨 |
| 入境簽證 | 簽證 | 上下位 |
| 歡聲雷動 | 掌聲雷動 | 歡聲≠掌聲 |
| 骨科醫生 | 骨科 | 醫生≠科室 |
| 值得品味 | 耐人尋味 | 品味≠尋味 |
| 初級小學 | 小學 | 上下位 |
| 地緣戰略 | 地緣政治 | 戰略≠政治 |
| 放手去做 | 放手一搏 | 去做≠一搏 |
| 金融槓桿 | 槓桿 | 上下位／省略 |
| 丟盔卸甲 | 抱頭鼠竄 | 場景唔同 |
| 剖腹自殺 | 剖腹 | 上下位 |
| 逆風而行 | 逆流而上 | 逆風≠逆流 |
| 遠隔重洋 | 遠渡重洋 | 遠隔≠遠渡 |
| 催眠狀態 | 催眠 | 狀態≠過程 |
| 頭腦清楚 | 清醒 | 清楚≠清醒 |

### no_natural fails（5）→ accepted

| head | 建議尾 | 問題 |
|------|--------|------|
| 無藥可救 | 不可救藥 | 明顯自然近義 |
| 倒背如流 | 滾瓜爛熟 | 明顯自然近義 |
| 自相殘殺 | 同類相殘 | 明顯自然近義 |
| 反覆思量 | 思前想後 | 明顯自然近義 |
| 體外受精 | 試管受孕 | 明顯自然近義 |

### adequate fails（4）

| head | 覆蓋邊 | 問題 |
|------|--------|------|
| 喃喃自語 | 喃喃 | 不完整／上下位 |
| 一線生機 | 一線希望 | 生機≠希望 |
| 直呼其名 | 指名道姓 | 語用不穩 |
| 籠絡人心 | 收買人心 | 籠絡≠收買 |

### Reaudit apply 結果

| 動作 | 結果 |
|------|------|
| 剔弱對 | **37**（34 sample fail 無向鍵 + adeq 覆蓋邊） |
| nn→accepted | **5**（無藥可救…體外受精） |
| adequate fails | **4** 移出 adq → nn（覆蓋邊已剔） |
| 完成度 | **5000／5000**（acc 1340／nn 3549／adq 111） |
| batch_id | `syn-len4-reaudit-20260719` |

腳本：`scripts/_syn_len4_final_audit_reaudit_apply.py`

---

## 首輪 formal audit（歷史，FAILED）

**結論：FAILED**（adequate_existing ok_rate **0.8571** ＜ 0.9；accepted／nn 過閘）。  
**Apply 已落地**（`scripts/_syn_len4_final_audit_apply.py`；`gate_status_post_apply=remediated_pending_reaudit`）。

### 首輪完成度（apply 前）

| 終局 | 頭數 |
|------|------|
| accepted | 1365 |
| no_natural | 3509 |
| adequate_existing | 126 |
| **合計** | **5000／5000** |

### 首輪抽樣

- seed = `20260718`；層 seed = `20260718 + batch_index`
- 每層 `sample_size_for` = `min(n, max(50, ceil(n*0.05)))`；adeq N=126 全抽

| 終局 | sample_n | ok | fail | ok_rate | ≥0.9 |
|------|----------|-----|------|---------|------|
| accepted | 500 | 450 | 50 | 0.9000 | ✓ |
| no_natural | 500 | 476 | 24 | 0.9520 | ✓ |
| adequate_existing | 126 | 108 | 18 | 0.8571 | ✗ |

### 首輪 Accepted fails（50）

| head | tail | reason |
|------|------|--------|
| 世界經濟 | 國際經濟 | 相關域（世界經濟≠國際經濟），唔可穩定替換 |
| 勤工儉學 | 半工半讀 | 相關教育模式，非同義層近義 |
| 大吉利是 | 大吉大利 | 粵語避諱口彩≠泛吉祥語，語用唔同 |
| 生活環境 | 居住環境 | 生活域≠居住域，相關非近義 |
| 流行音樂 | 流行曲 | 樂種≠歌曲（上下位／相關） |
| 水力發電 | 水電 | 發電方式≠水電合稱／水電費，替換唔穩定 |
| 三國鼎立 | 三足鼎立 | 史事專稱≠泛三方鼎立 |
| 國外市場 | 國際市場 | 國外≠國際，相關非近義 |
| 昂首挺胸 | 昂首闊步 | 姿態相關，非可獨立替換近義 |
| 轟動一時 | 風靡一時 | 轟動≠風靡，相關非同義層 |
| 參考手冊 | 使用手冊 | 參考手冊≠使用說明書 |
| 單純皰疹 | 皰疹 | 上下位（單純皰疹⊂皰疹） |
| 民間舞蹈 | 民族舞蹈 | 民間≠民族，相關舞種 |
| 毫無用處 | 一無是處 | 事物無用≠人品一無是處 |
| 血管硬化 | 動脈硬化 | 血管泛稱≠動脈硬化專稱 |
| 可供參考 | 僅供參考 | 可供≠僅供，語氣／語用唔同 |
| 卵母細胞 | 卵細胞 | 上下位（卵母細胞⊂卵細胞） |
| 爭權奪利 | 爭名奪利 | 權≠名，相關非近義 |
| 三代同堂 | 四世同堂 | 三代≠四世 |
| 放高利貸 | 放債 | 上下位（高利貸⊂放債） |
| 知識寶庫 | 知識庫 | 比喻寶庫≠知識庫系統 |
| 忍飢挨餓 | 飢寒交迫 | 忍飢≠飢寒交迫 |
| 肥頭大耳 | 大腹便便 | 形貌相關，所指部位唔同 |
| 另謀出路 | 另謀高就 | 出路≠高就（另覓職位） |
| 尊師重道 | 尊師愛徒 | 重道≠愛徒 |
| 羽翼豐滿 | 羽翼漸豐 | 已豐≠漸豐（程度） |
| 老弱婦孺 | 老弱殘兵 | 婦孺≠殘兵 |
| 入境手續 | 入境簽證 | 手續≠簽證 |
| 江湖術士 | 江湖騙子 | 術士≠騙子 |
| 餘情未了 | 意猶未盡 | 餘情≠意猶未盡 |
| 菲力牛排 | 牛排 | 上下位（菲力⊂牛排） |
| 學校同學 | 同學 | 冗餘收窄，非獨立近義層 |
| 庭外和解 | 和解 | 上下位（庭外和解⊂和解） |
| 有軌電車 | 電車 | 有軌電車≠泛電車／電氣車 |
| 百貨商場 | 百貨公司 | 商場≠公司 |
| 工科大學 | 理工大學 | 工科≠理工 |
| 國家預算 | 財政預算 | 國家預算≠財政預算 |
| 大便乾燥 | 便秘 | 症狀≠病名，相關非近義 |
| 如假包換 | 貨真價實 | 包換保證≠貨真價實 |
| 疲勞過度 | 精疲力竭 | 過度疲勞≠精疲力盡狀態 |
| 口齒清楚 | 口齒伶俐 | 清楚≠伶俐 |
| 互相推諉 | 推卸責任 | 互相推諉≠單方推卸責任 |
| 初試啼聲 | 初試身手 | 啼聲（出道）≠身手 |
| 心懷不滿 | 憤憤不平 | 不滿≠憤憤不平 |
| 獨立思想 | 獨立精神 | 思想≠精神 |
| 品種改良 | 育種 | 相關／上下位，唔可穩定替換 |
| 陰晴不定 | 喜怒無常 | 陰晴（可指天氣）≠性情喜怒 |
| 睾丸激素 | 雄性激素 | 上下位（睾酮類⊂雄激素） |
| 氣勢不凡 | 氣勢磅礴 | 不凡≠磅礴（程度／氣象） |
| 重新統一 | 統一 | 重新統一≠統一 |

### 首輪 no_natural fails（24）

#### 已無向覆蓋卻裁 nn（11）

| head | 覆蓋邊 | 問題 |
|------|--------|------|
| 十有八九 | 十之八九 | 應 adequate_existing |
| 忍無可忍 | 不堪忍受 | 應 adequate_existing |
| 初來乍到 | 新來乍到 | 應 adequate_existing |
| 從頭開始 | 從頭做起 | 應 adequate_existing |
| 狗血淋頭 | 狗血噴頭 | 應 adequate_existing |
| 志在必得 | 勢在必得 | 應 adequate_existing |
| 避重就輕 | 避實就虛 | 應 adequate_existing |
| 敬業精神 | 專業精神 | 邊偏相關；不應同時 nn |
| 試管嬰兒 | 體外受精 | 程序≠嬰兒；不應 nn 掩蓋衝突 |
| 自相殘殺 | 骨肉相殘 | 邊偏相關；不應 nn |
| 黯淡無光 | 前途渺茫 | 邊誤配；不應 nn 掩蓋衝突 |

#### 應改判 accepted（13）

| head | 建議尾 | 問題 |
|------|--------|------|
| 打定主意 | 下定決心 | 明顯自然近義 |
| 國外貿易 | 國際貿易 | 明顯自然近義 |
| 濛濛細雨 | 毛毛雨 | 明顯自然近義 |
| 中小企業 | 中小企 | 明顯自然近義 |
| 由此可見 | 由此可知 | 明顯自然近義 |
| 時過境遷 | 事過境遷 | 明顯自然近義 |
| 深藏不露 | 深藏若虛 | 明顯自然近義 |
| 浪子回頭 | 迷途知返 | 明顯自然近義 |
| 見好就收 | 適可而止 | 明顯自然近義 |
| 海峽兩岸 | 兩岸 | 明顯自然近義 |
| 找不自在 | 自找苦吃 | 明顯自然近義 |
| 門牌號碼 | 門牌 | 明顯自然近義 |
| 川流不息 | 絡繹不絕 | 人潮／車流可替換近義 |

### 首輪 adequate fails（18）

| head | 覆蓋邊 | 問題 |
|------|--------|------|
| 國際經濟 | 世界經濟 | 相關域 |
| 居住環境 | 生活環境 | 相關域 |
| 三足鼎立 | 三國鼎立 | 史事≠泛稱 |
| 喜怒無常 | 陰晴不定 | 天氣義干擾 |
| 風靡一時 | 轟動一時 | 風靡≠轟動 |
| 民族舞蹈 | 民間舞蹈 | 民族≠民間 |
| 半工半讀 | 勤工儉學 | 相關模式 |
| 心懷鬼胎 | 各懷鬼胎 | 誤配 |
| 爭名奪利 | 爭權奪利 | 名≠權 |
| 不予置評 | 無可奉告 | 語用唔同 |
| 標準規格 | 標準尺寸 | 規格≠尺寸 |
| 危急關頭 | 生死關頭 | 程度／場景 |
| 一面之交 | 一面之緣 | 交≠緣 |
| 敗興而歸 | 鎩羽而歸 | 敗興≠挫敗 |
| 女權運動 | 婦女運動 | 相關社運 |
| 婦道人家 | 女流之輩 | 語氣層不同 |
| 崇高理想 | 遠大理想 | 崇高≠遠大 |
| 嘰嘰咕咕 | 嘰哩咕嚕 | 相關非近義 |

### 首輪 Apply 結果

| 動作 | 結果 |
|------|------|
| 剔弱對 | **64**（50 sample fail＋14 extra covering／衝突邊） |
| nn→accepted | **13** |
| nn→adequate | **7** |
| adequate fails | **18** 移出 adq → nn |
| 完成度 | **5000／5000**（acc 頭 1379／nn 3506／adq 115） |

---

## 指令速查

```text
# 重抽 reaudit 樣本（seed 見 _syn_len4_final_audit_sample.py SEED）
PYTHONIOENCODING=utf-8 python scripts/_syn_len4_final_audit_sample.py

# 由 fixture + 硬編碼判決建 meta
PYTHONIOENCODING=utf-8 python scripts/_syn_len4_final_audit_build_meta.py

# 首輪 apply（已跑；meta.apply_status=applied）
PYTHONIOENCODING=utf-8 python scripts/_syn_len4_final_audit_apply.py --dry-run

# reaudit apply（已跑；meta.reaudit_apply_status=applied）
PYTHONIOENCODING=utf-8 python scripts/_syn_len4_final_audit_reaudit_apply.py --dry-run
```
