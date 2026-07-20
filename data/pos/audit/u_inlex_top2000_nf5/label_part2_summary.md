# u_inlex_top2000_nf5 manual POS label — part2

**File:** `data/pos/audit/u_inlex_top2000_nf5/label_part2.tsv`
**Universe slice:** in-lexicon still-`u` top2000_nf5 batch part2
**n:** 343
**Date:** 2026-07-19

**Rules:** `n/v/a/r/x` multi-ok（comma 按 a,n,r,v,x 字母序）；`u` only fragment/unclear；`family=idiom` 僅真熟語；`voice` 全空；`note` 只標 `u` 理由／成語截 borderline。

## Counts

| pos bucket | n | % |
|------------|--:|---:|
| formal（非 u） | 343 | 100.00% |
| `u` fragment/unclear | 0 | 0.00% |
| **total** | **343** | 100% |

| family | n |
|--------|--:|
| empty | 268 |
| `idiom` | 75 |
| voice non-empty | 0 |

### pos distribution（exact string）

| pos | n |
|-----|--:|
| n | 151 |
| v | 69 |
| a,v | 43 |
| a | 31 |
| n,v | 16 |
| a,x | 9 |
| v,x | 7 |
| a,n | 4 |
| r | 3 |
| x | 3 |
| a,r | 3 |
| n,x | 2 |
| r,x | 1 |
| r,v | 1 |

### Formal tag hits（multi 計入每個 tag；一列可多 hit）

| tag | hits |
|-----|-----:|
| n | 173 |
| a | 90 |
| r | 8 |
| v | 136 |
| x | 22 |
| multi rows | 86 |

## `u` patterns（0）

_None._ 本批 343 列皆可標 formal（完整詞／固定短語／專名／科技 NP；無合成殘字或主謂截斷）。

**Full `u` list (0):** —

## `family=idiom`（75）

| literal | pos |
|---------|-----|
| 嫁狗隨狗 | v,x |
| 洗手不幹 | v |
| 琴瑟和鳴 | a,v |
| 蠶食鯨吞 | v |
| 克己復禮 | v |
| 升斗小民 | n |
| 將門虎子 | n |
| 成年累月 | r |
| 文人相輕 | a,v |
| 用兵如神 | a,v |
| 略見一斑 | v |
| 舐犢情深 | a |
| 身歷其境 | a,v |
| 久病成醫 | a,x |
| 克己奉公 | v |
| 官樣文章 | n |
| 擁兵自重 | v |
| 流水不腐 | a,x |
| 白日見鬼 | v,x |
| 碩大無朋 | a |
| 一脈相傳 | a,v |
| 丟盔卸甲 | v |
| 寡廉鮮恥 | a |
| 肝膽俱裂 | a,v |
| 項上人頭 | n |
| 餓虎撲食 | v |
| 地靈人傑 | a,x |
| 瞎子摸象 | n,v |
| 細微末節 | n |
| 魚肉百姓 | v |
| 一觸即潰 | a,v |
| 代罪羔羊 | n |
| 勇冠三軍 | a |
| 奇文共賞 | v,x |
| 孰能無過 | x |
| 清水衙門 | n |
| 無則加勉 | v |
| 誤上賊船 | v |
| 開門揖盜 | v |
| 驕兵必敗 | a,x |
| 失道寡助 | a,x |
| 愛人如己 | v |
| 懸樑刺股 | n,v |
| 無遠弗屆 | a,v |
| 皇天后土 | n,x |
| 邪不勝正 | a,x |
| 一無所長 | a |
| 以儆效尤 | v |
| 同氣連枝 | a,n |
| 狼多肉少 | a |
| 一枕黃粱 | n,v |
| 打落水狗 | v |
| 陽關大道 | n |
| 集腋成裘 | v |
| 加油添醋 | v |
| 辭不達意 | a,v |
| 出將入相 | n,v |
| 橡皮圖章 | n |
| 求才若渴 | a,v |
| 無機可乘 | a |
| 珠胎暗結 | v |
| 瓜田李下 | n |
| 磨拳擦掌 | v |
| 萬世師表 | n |
| 承先啓後 | v |
| 明槍易躲 | a,x |
| 焚琴煮鶴 | v |
| 疾風勁草 | n,x |
| 綱舉目張 | v |
| 賣官鬻爵 | v |
| 地覆天翻 | a,v |
| 大塊朵頤 | v |
| 棋逢敵手 | a,v |
| 良禽擇木 | v |
| 鑿壁偷光 | n,v |

未標 idiom（固定但非成語桶）：出入平安`x`（賀語）、有何指教`x`（客套）、禁止停車`v,x`（告示）、過時不候`v,x`（告示套語）、實不相瞞`r,x`（話語標記）、統一資源`n`（URI 術語根）、後進先出`n`（LIFO 術語）、有損壓縮`n`（lossy compression）、五卅運動／戊戌政變`n`（史專名）、樹上開花`n,v`（計謀名亦可作字面）。

## Formal patterns worth keeping

- **專名／地名／書名／品牌 → n**：春秋繁露、費利克斯、撒馬爾罕、舊約全書、高麗王朝、漢坦病毒、西班牙港、孟加拉語、楚漢戰爭、後西遊記、西薩摩亞、印地安納、施洗約翰、拜科努爾、達魯花赤、因紐特人、東坡肘子、魔術方塊
- **科技／醫／政經 NP → n**：大氣壓強、微細加工、伽瑪射線、羥基丁酸、羥自由基、有損壓縮、絕對地址、胸腺嘧啶、分形幾何、反射療法、腔腸動物、臨界壓力、動眼神經、重力異常、資料傳輸、品質管制、麥芽糖醇、隱形飛機、導彈潛艇
- **成語／熟語 → 多 a/v/r + family=idiom**：嫁狗隨狗、洗手不幹、琴瑟和鳴、克己復禮、升斗小民、將門虎子、成年累月、蠶食鯨吞、文人相輕、略見一斑、舐犢情深、擁兵自重、碩大無朋、丟盔卸甲、寡廉鮮恥、開門揖盜、集腋成裘、瓜田李下、焚琴煮鶴、鑿壁偷光…
- **篇章／套語 → r,x／x**：出入平安、有何指教、實不相瞞、孰能無過、過時不候、禁止停車
- **短詞 formal**：眼梢`n`、留話`v`、隨風倒`a,v`、消極性`n`

## Borderline（已標 formal；可再審）

| literal | pos | note |
|---------|-----|------|
| 無則加勉 | v | 成語截「有則改之無則加勉」；family=idiom |
| 後人乘涼 | v | 成語截「前人栽樹後人乘涼」；family 空 |
| 明槍易躲 | a,x | 成語截「明槍易躲暗箭難防」；family=idiom |
| 良禽擇木 | v | 成語截「良禽擇木而棲」；family=idiom |
| 死而不僵 | a,v | 成語截「百足之蟲死而不僵」；family 空 |
| 統一資源 | n | URI 術語根（統一資源定位符）；可再審 |
| 出入平安 | x | 賀語；未標 idiom |
| 有何指教 | x | 客套詢句；未標 idiom |
| 禁止停車 | v,x | 告示／祈使 |
| 樹上開花 | n,v | 三十六計名／字面動 |
| 身歷其境 | a,v | 常作「身臨其境」異體；仍 formal idiom |
| 磨拳擦掌 | v | 常作「摩拳擦掌」；仍 formal idiom |
| 代罪羔羊 | n | 常作「替罪羔羊」；仍 formal idiom |
| 見馬克思 | v | 死亡委婉語；可再審 x |

## Policy notes

1. **唔造 POS**：本批無合成殘字／主謂截斷 → `u`=0。
2. **multi 從嚴**：只標兩棲皆常見者；comma 按 a,n,r,v,x。
3. **family**：僅 75 條真成語／固定熟語標 `idiom`；能產短語、政經／科技 NP、賀語／告示套語 family 空。
4. **voice**：本批無語態對，全空。
5. **下一步**：與 part1／3–5 合併後可 `_apply.py` upsert（note 帶 `u-inlex-nf5`）再抽 gate sample。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex_top2000_nf5/label_part2.tsv` | 343 列已填 pos |
| `data/pos/audit/u_inlex_top2000_nf5/label_part2_summary.md` | 本摘要 |
