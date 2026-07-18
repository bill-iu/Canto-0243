# P0 full-system POS audit (full_r1)

**Sample:** `data/pos/audit/full_r1/p0_sample_part{1–5}.tsv` (merged intent: `p0_sample.tsv`)  
**Universe:** 18781 P0 mother-body literals  
**Sample n:** 1098 (seed 20260720, manifest)  
**Threshold:** ok_rate > 0.90  
**Date:** 2026-07-19  

**Policy**
- **gate:** primary POS must be correct → BAD if wrong primary  
- **low draft:** OK if usable draft; BAD if clearly wrong primary  
- **u:** OK if hard; BAD+`fix_pos` if clear class  
- **idiom family wrong:** `fix_family` empty (∅)  
- ok_rate = (OK+SOFT)/n  

## Counts

| verdict | n | % |
|---------|--:|---:|
| OK | 307 | 28.0% |
| SOFT | 28 | 2.6% |
| BAD | 763 | 69.5% |
| **total** | **1098** | 100% |

**ok_rate = (OK+SOFT)/n = 335/1098 = 0.3051**

**FAIL** (0.3051 ≯ 0.90)

> Overall FAIL is expected: **low|u** mass under-tag (~663 rows) dominates. Gate / draft strata are the actionable quality signal (see below).

## By stratum

| stratum | OK | SOFT | BAD | n | ok_rate |
|---------|---:|-----:|----:|--:|--------:|
| high\|gate\|idiom | 42 | 0 | 8 | 50 | 0.840 |
| high\|gate\|plain | 62 | 0 | 0 | 62 | **1.000** |
| high\|u\|idiom | 0 | 0 | 50 | 50 | 0.000 |
| low\|low\|idiom | 6 | 1 | 11 | 18 | 0.389 |
| low\|low\|plain | 181 | 17 | 22 | 220 | **0.900** |
| low\|u\|idiom | 0 | 0 | 50 | 50 | 0.000 |
| low\|u\|plain | 0 | 9 | 604 | 613 | 0.015 |
| medium\|gate\|plain | 16 | 1 | 19 | 36 | 0.472 |
| **gate combined** (high+medium) | 120 | 1 | 27 | 148 | **0.818** |
| **draft low\|low combined** | 187 | 18 | 33 | 238 | **0.861** |

## Top error patterns (BAD)

1. **u→formal under-tag** (~704) — `no-source;fallback` mass-`u`; clear n/v/a/r/x available (low|u plain + high|u idiom + low|u idiom)
2. **之字格假陽 n on predicate / adverbial idioms** (8, high|gate) — 乘人之危、趁人之危、揮之不去、處之泰然、言之過早、趨之若鶩 → `v`；乍看之下、忽然之間 → `r`
3. **cow-single wrong primary on low draft** (22) — adj/adv as n or wrong class: 完整/容易/實在/幼稚/似乎/難以/響亮/放寬/有用…
4. **cow-multi false `a` on medium|gate** (19) — 寫→v、缺乏→v、乾淨→a only、勢均力敵→a、第十→x…
5. **idiom family false positive** (7) — 亞美尼亞、匆匆離去、彈道導彈、核糖核酸、空空導彈、化學變化、政黨政治、默罕默德 → `fix_family` ∅  
   *(8 if count 默罕默德 separately from ABAC map; listed in BAD table)*
6. **cow n on stative idioms** (low|low|idiom) — 中規中矩/彬彬有禮/無影無蹤/無法無天/默默無聞 → `a`

## Gate impact note

| bucket | ok_rate | note |
|--------|--------:|------|
| high\|gate\|plain | 1.00 | clean |
| high\|gate\|idiom | 0.84 | 8 之字格 predicate BAD — **priority apply** |
| medium\|gate\|plain | 0.47 | cow-multi a-noise — **priority apply** |
| **all gate** | **0.82** | still under 0.90 |

Priority fix before gate re-sample: high|gate 8 BAD + medium|gate 19 BAD (already in 閘用詞類).

## SOFT list (all 28)

| literal | stratum | pos | note |
|---------|---------|-----|------|
| 小偷小摸 | low\|low\|idiom | n | n 可；亦有動用；熟語可留 |
| 傳真 | low\|low\|plain | n | n,v 動用常見 |
| 傷 | low\|low\|plain | v | n,v 傷勢名用常見 |
| 傷風 | low\|low\|plain | n | n,v 病名／動 |
| 匯款 | low\|low\|plain | n | n,v 動用常見 |
| 圍繞 | low\|low\|plain | n,v | 主 v；n 薄 |
| 恐懼 | low\|low\|plain | n | n,a,v 多類 |
| 流出 | low\|low\|plain | n,v | 真 dual 可 |
| 滑 | low\|low\|plain | v | 主標動可；形「滑溜」常見 |
| 真的 | low\|low\|plain | a | a,r 副用常見 |
| 空 | low\|low\|plain | n | a,n,v 多類 |
| 突擊 | low\|low\|plain | n | n,v 動用常見 |
| 練習 | low\|low\|plain | n | n,v 動用常見 |
| 考試 | low\|low\|plain | n | n,v 動用常見 |
| 遲疑 | low\|low\|plain | n,v | a 亦常見 |
| 遺憾 | low\|low\|plain | n | n,a 形用常見 |
| 還原 | low\|low\|plain | n | n,v 動用常見 |
| 長期 | low\|low\|plain | n | a,n,r 多類 |
| 佈 | low\|u\|plain | u | 動為主；u 邊介可 |
| 別 | low\|u\|plain | u | 多類；u 可 |
| 套 | low\|u\|plain | u | 多類；u 可 |
| 屬 | low\|u\|plain | u | 多類；u 可 |
| 平 | low\|u\|plain | u | 多類；u 可 |
| 毛 | low\|u\|plain | u | 多義；u 可 |
| 然 | low\|u\|plain | u | 文言虛；u 可 |
| 程 | low\|u\|plain | u | 量／名；u 可 |
| 罷 | low\|u\|plain | u | 多類；u 可 |
| 代 | medium\|gate\|plain | a,n | 名／動／虛；a 假陽 → suggest n,v,x |

## BAD list (all)

### A. high|gate|idiom — keep family；fix_pos (8)

| literal | was | fix_pos | fix_family | note |
|---------|-----|---------|------------|------|
| 乍看之下 | n | r | idiom | 之字格假陽 n；副「初看」 |
| 乘人之危 | n | v | idiom | 謂語成語；n 假陽毒名詞閘 |
| 忽然之間 | n | r | idiom | 之字格假陽 n；副 |
| 揮之不去 | n | v | idiom | 謂語成語；n 假陽 |
| 處之泰然 | n | v | idiom | 謂語成語；n 假陽 |
| 言之過早 | n | v | idiom | 謂語成語；n 假陽 |
| 趁人之危 | n | v | idiom | 謂語成語；n 假陽毒名詞閘 |
| 趨之若鶩 | n | v | idiom | 謂語成語；n 假陽 |

### B. high|u|idiom — fill formal POS；keep family (50)

| literal | fix_pos | literal | fix_pos |
|---------|---------|---------|---------|
| 一年四季 | n | 一望無邊 | a |
| 一望無際 | a | 一覽無餘 | v |
| 乜乜物物 | n,x | 修修補補 | v |
| 健健康康 | a | 勉勉強強 | a,r |
| 原原本本 | a,r | 呼哧呼哧 | r |
| 嚴嚴實實 | a,r | 大大話話 | a |
| 安安心心 | a,r | 安安穩穩 | a,r |
| 從從容容 | a,r | 打打鬧鬧 | v |
| 指指點點 | v | 搖搖晃晃 | v |
| 敲敲打打 | v | 方方面面 | n |
| 昏昏沉沉 | a | 星星點點 | a,n |
| 有增無減 | v | 有心無力 | a |
| 有所不知 | v | 有教無類 | v |
| 有驚無險 | a | 期期艾艾 | a |
| 正正經經 | a,r | 求求其其 | a |
| 清清爽爽 | a | 清清白白 | a |
| 無惡不作 | v | 甜甜蜜蜜 | a |
| 生生世世 | n,r | 病病歪歪 | a |
| 瘋瘋癲癲 | a | 真真假假 | a |
| 磕磕撞撞 | v | 稀稀拉拉 | a |
| 空空蕩蕩 | a | 罵罵咧咧 | v |
| 老老實實 | a,r | 花花搭搭 | a |
| 花花綠綠 | a | 行行企企 | v |
| 輕輕鬆鬆 | a,r | 隨隨便便 | a,r |
| 風風雨雨 | n | 鬆鬆垮垮 | a |

### C. low|low|idiom (11)

| literal | was | fix_pos | fix_family | note |
|---------|-----|---------|------------|------|
| 中規中矩 | n | a | idiom | cow n 假陽 |
| 亞美尼亞 | n | — | ∅ | 國名；非熟語 |
| 匆匆離去 | v | — | ∅ | 普通 VP；非熟語 |
| 彈道導彈 | n | — | ∅ | 軍事技術 NP；非熟語 |
| 彬彬有禮 | n | a | idiom | cow n 假陽 |
| 核糖核酸 | n | — | ∅ | RNA 術語；非熟語 |
| 無影無蹤 | n | a | idiom | cow n 假陽 |
| 無拘無束 | v | a | idiom | stative 形 |
| 無法無天 | n | a | idiom | cow n 假陽 |
| 空空導彈 | n | — | ∅ | 軍事技術 NP；非熟語 |
| 默默無聞 | n | a | idiom | cow n 假陽 |

### D. low|low|plain — wrong primary (22)

| literal | was | fix_pos | note |
|---------|-----|---------|------|
| 不在場 | n | a | 缺席狀態＝形 |
| 似乎 | v | r | 副，非動 |
| 加重 | n | v | 動，非名 |
| 大好 | v | a | verb-suffix 假陽 |
| 完整 | n | a | 形，非名 |
| 容易 | n | a | 形，非名 |
| 實在 | n | a,r | 形／副 |
| 幼稚 | n | a | 形，非名 |
| 放寬 | n | v | 動，非名 |
| 放肆 | n,v | a,v | 主形 |
| 有用 | n,v | a | 形 |
| 有關 | n,v | a,x | 形／介 |
| 每年 | a | r | 副 |
| 消瘦 | n | a,v | 形／動 |
| 濕 | n | a | 形 |
| 當時 | n | n,r | 時間名／副 |
| 純淨 | n | a | 形 |
| 經紀人 | n,v | n | v 假陽 |
| 胡言亂語 | n | v | 動 |
| 逃避現實 | n | v | VO 動 |
| 難以 | a | r | 副 |
| 響亮 | v | a | 形 |

### E. low|u|idiom (50) — clear POS；3 family clears

| literal | fix_pos | fix_family | note |
|---------|---------|------------|------|
| 一心一德 | a | idiom | |
| 一手一腳 | n,r | idiom | |
| 一死一傷 | n | idiom | |
| 一瘸一拐 | v | idiom | |
| 一言一行 | n | idiom | |
| 一長一短 | a | idiom | |
| 一顰一笑 | n | idiom | |
| 不大不小 | a | idiom | |
| 予取予攜 | v | idiom | |
| 予取予求 | v | idiom | |
| 人五人六 | a | idiom | |
| 倔頭倔腦 | a | idiom | |
| 化學變化 | n | ∅ | 普通 NP；非熟語 |
| 半明半暗 | a | idiom | |
| 可喜可賀 | a | idiom | |
| 同名同姓 | a | idiom | |
| 呵呵大笑 | v | idiom | |
| 大喊大叫 | v | idiom | |
| 大模大樣 | a,r | idiom | |
| 大鳴大放 | v | idiom | |
| 如火如荼 | a | idiom | |
| 實報實銷 | v | idiom | |
| 小恩小惠 | n | idiom | |
| 快人快語 | a | idiom | |
| 惶惶不安 | a | idiom | |
| 惺惺相惜 | v | idiom | |
| 政黨政治 | n | ∅ | 普通 NP；非熟語 |
| 救國救民 | v | idiom | |
| 救苦救難 | v | idiom | |
| 有條有理 | a | idiom | |
| 有權有勢 | a | idiom | |
| 束手束腳 | a,v | idiom | |
| 沒大沒小 | a | idiom | |
| 沒完沒了 | a | idiom | |
| 流裏流氣 | a | idiom | |
| 無私無畏 | a | idiom | |
| 無聲無息 | a,r | idiom | |
| 直來直去 | a,r | idiom | |
| 直來直往 | a,r | idiom | |
| 相輔相成 | v | idiom | |
| 知己知彼 | v | idiom | |
| 笨手笨腳 | a | idiom | |
| 美侖美奐 | a | idiom | |
| 耗時耗力 | a,v | idiom | |
| 胡裏胡塗 | a | idiom | |
| 自私自利 | a | idiom | |
| 自賣自誇 | v | idiom | |
| 若即若離 | a | idiom | |
| 越幫越忙 | v | idiom | |
| 默罕默德 | n | ∅ | 專名；非熟語 |

### F. medium|gate|plain (19)

| literal | was | fix_pos | note |
|---------|-----|---------|------|
| 乾淨 | a,n | a | n 假陽毒閘 |
| 勢均力敵 | r,v | a | 形；r,v 假陽 |
| 古物 | a,n | n | a 假陽 |
| 失明 | a,n | a,v | n 假陽 |
| 寫 | a,v | v | a 假陽 |
| 弄亂 | a,v | v | a 假陽 |
| 忙 | a,n | a | n 假陽 |
| 最後 | a,n | n,r | a 假陽 |
| 根據 | a,n | n,x | a 假陽 |
| 概括 | a,n,v | v,n | a 假陽 |
| 理解 | a,n,v | n,v | a 假陽 |
| 瞎 | a,n | a,v | n 假陽 |
| 第十 | a,n | x | 序數＝虛 |
| 繼承 | a,v | v,n | a 假陽 |
| 缺乏 | a,n,v | v | a,n 假陽 |
| 超過 | r,v | v | r 假陽 |
| 轉移 | a,n,v | v,n | a 假陽 |
| 遠離 | a,n,v | v | a,n 假陽 |
| 顫抖 | a,n,v | v | a,n 假陽 |

### G. low|u|plain (604) — under-tag (parts 2–5)

All rows with `pos=u` and `stratum=low|u|plain` except the 9 SOFT monosyllables above. Each has `fix_pos` filled in the part TSVs. Summary by fix_pos primary:

| fix_pos (primary class) | approx n | examples |
|-------------------------|--------:|----------|
| n | ~240 | 三明治、世界盃、事務、光學、名單、平原、智慧、熒幕… |
| v | ~200 | 上車、偷走、叫醒、打消、擺脫、減肥、認爲、關機… |
| a | ~100 | 不錯、奇怪、得意、寬敞、暗淡、沉悶、艱難、龐大… |
| r / multi with r | ~40 | 一共、一向、互相、偏偏、儘量、或許、極爲、狠狠… |
| x / multi with x | ~20 | 們、可是、它、除非、雖、別的、再者… |
| multi (n,v / a,v / …) | ~50 | 仰卧起坐、來電、化妝、盈利、研發… |

Full per-row detail: `p0_sample_part2.tsv` (from 一元復始)、`part3.tsv`、`part4.tsv`、`part5.tsv` (through 龐大).

## OK patterns worth keeping

- **high|gate plain:** len4 NP（主義／系統／大學／機構…）、true n,v duals（完成、幫助、投票、發展…）、closed-class（但、給、自己、其他）、reviewed multi（句 n,x、大把 a,r、驚 a,v）
- **high|gate idiom:** classic 之字格名物（喪家之犬、神來之筆、莫逆之交…）、seed／reviewed v·a（一石二鳥、半途而廢、完整無缺）
- **low draft nouns/verbs:** 實體名（手套、飛機、長頸鹿…）同典型動（打電話、逃走、防止…）

## Apply path (not run this pass)

```text
# dry-run then apply BAD+fix_pos (and family clears via p2 tooling as needed)
python -m ingest.project_pos_audit apply --verdicts data/pos/audit/full_r1/p0_sample_part1.tsv --dry-run
```

**Priority apply order**
1. high|gate|idiom 8 BAD（閘毒）  
2. medium|gate 19 BAD（閘毒）  
3. low|low draft 22 BAD（升 trust 前）  
4. high|u / low|u bulk（覆蓋升級，非閘毒）  

## Files

| path | role |
|------|------|
| `p0_sample_part1.tsv` | gate + high u + low-low start (250) |
| `p0_sample_part2.tsv` | low-low rest + low u idiom + low u start (250) |
| `p0_sample_part3.tsv` | low u plain (250) |
| `p0_sample_part4.tsv` | low u plain (250) |
| `p0_sample_part5.tsv` | low u tail + medium gate (98) |
| `p0_sample.tsv` | rebuild via `python data/pos/audit/full_r1/_merge_p0.py` (parts are SSOT) |
| `p0_summary.md` | this summary |
| `manifest.json` | sample meta |

## Confirm pass

**未過門檻**：overall ok_rate **0.3051 ≯ 0.90** → **P0 full-system r1 FAIL**（u 層主導）。  
**閘用子集** ok_rate **0.818** 仍未過；修 27 gate BAD 後重抽 gate 層。  
**low|low draft** ok_rate **0.900** 貼近門檻。
