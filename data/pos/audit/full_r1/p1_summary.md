# P1 full-system POS audit (full_r1)

**Sample:** `data/pos/audit/full_r1/p1_sample.tsv` (n=292)  
**Universe:** Essay Top-5000（manifest seed 20260720）  
**Threshold:** ok_rate = (OK+SOFT)/n > 0.90  
**Date:** 2026-07-19  
**Scope:** audit-only（未 apply SSOT）

## Counts

| verdict | n | % |
|---------|---|---|
| OK | 134 | 45.9% |
| SOFT | 27 | 9.2% |
| BAD | 131 | 44.9% |
| **total** | **292** | 100% |

**ok_rate = (OK+SOFT)/n = 161/292 = 0.551**

**FAIL** (0.551 ≯ 0.90)

> 整體未過門檻，主因係 **low|u** 欠標（預期：fallback `u` 大多可正式標）。閘用層（high+medium gate）單獨 = **60/69 = 0.870**（仍 <0.90）；**high|gate|plain 單獨 50/50 = 1.00**。

## By stratum

| stratum | n | OK | SOFT | BAD | ok_rate | ≥0.90 |
|---------|--:|---:|-----:|----:|--------:|:-----:|
| high\|gate\|plain | 50 | 47 | 3 | 0 | **1.000** | ✅ |
| high\|u\|idiom | 1 | 0 | 0 | 1 | 0.000 | ❌ |
| high\|u\|plain | 3 | 3 | 0 | 0 | **1.000** | ✅ |
| low\|low\|plain | 84 | 67 | 10 | 7 | **0.917** | ✅ |
| low\|u\|idiom | 5 | 0 | 0 | 5 | 0.000 | ❌ |
| low\|u\|plain | 130 | 10 | 11 | 109 | 0.162 | ❌ |
| medium\|gate\|plain | 19 | 7 | 3 | 9 | 0.526 | ❌ |
| **gate 合計**（high+medium） | **69** | **54** | **6** | **9** | **0.870** | ❌ |

## Top error patterns (BAD)

1. **low|u 欠標可回收**（~109/131）  
   fallback `u` 有清晰正式類：實體名、動、形、副、虛、專名。  
   例：上課→v、正常→a、特登→r、否則→x、臺灣→n、阿玲→n。

2. **cow-multi 假陽 a**（medium|gate，8/9 BAD）  
   COW 把非形塞入 `a`，毒同形閘：  
   - 假 a 應刪：一些→x；寫→v；代→n,v；最後→n,r；根據→n,x；理解／轉移→n,v；關→n,v  
   - 假 n on stative：乾淨→a

3. **cow-single 形／副誤 n／a**（low|low，7/7 BAD）  
   失望／尷尬／斜／方便／無能 → a；砍 → v；難以 → r。

4. **熟語 family 有 POS 可標**（low|u|idiom，5/5）  
   family=idiom 正確留；pos=u 欠標：一模一樣→a,r；不知不覺→r；今時今日→n,r；自言自語→v；越來越多→r。

5. **假 idiom family**（1）  
   哈哈哈哈：笑擬聲重疊非固定熟語 → 清 family（fix_family 空）；u 可留。

## BAD detail（全部 131）

### high|u|idiom（1）

| literal | was | fix_pos | fix_family | reason |
|---------|-----|---------|------------|--------|
| 哈哈哈哈 | u + idiom | *(keep u)* | *(empty → clear)* | 笑擬聲重疊非固定熟語 |

### low|low|plain（7）

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 失望 | n | a | stative 形；n 假陽 |
| 尷尬 | n | a | stative 形；n 假陽 |
| 斜 | n | a | 自由形；n 假陽 |
| 方便 | n | a | 形；n 假陽 |
| 無能 | n | a | 形；n 假陽 |
| 砍 | n | v | 自由詞係動 |
| 難以 | a | r | 副「難以+VP」 |

### low|u|idiom（5；family 留 idiom）

| literal | fix_pos | reason |
|---------|---------|--------|
| 一模一樣 | a,r | 形／副「完全相同」 |
| 不知不覺 | r | 副 |
| 今時今日 | n,r | 名／副「現今」 |
| 自言自語 | v | 動 |
| 越來越多 | r | 副 |

### medium|gate|plain（9）

| literal | was | fix_pos | reason |
|---------|-----|---------|--------|
| 一些 | a,n | x | 量／不定指虛；a 假陽 |
| 乾淨 | a,n | a | stative；n 假陽 |
| 代 | a,n | n,v | 名／動；a 假陽 |
| 寫 | a,v | v | 只係動；a 假陽 |
| 最後 | a,n | n,r | 名／副；a 假陽 |
| 根據 | a,n | n,x | 名／介；a 假陽 |
| 理解 | a,n,v | n,v | 真名動；a 假陽 |
| 轉移 | a,n,v | n,v | 真名動；a 假陽 |
| 關 | a,v | n,v | 名／動；a 假陽 |

### low|u|plain（109）

| literal | fix_pos | note |
|---------|---------|------|
| 三星 | n | 專名／星級 |
| 上課 | v | |
| 上門 | v | |
| 下手 | v | |
| 不好意思 | a | |
| 不得不 | r | |
| 丫嘛 | x | |
| 中年 | n | |
| 今個 | x | |
| 仔細 | a | |
| 估到 | v | |
| 優化 | v | |
| 先講 | v | |
| 入房 | v | |
| 再次 | r | |
| 初初 | r | |
| 勾 | v | |
| 千祈 | r | |
| 又是 | r,x | |
| 口供 | n | |
| 否則 | x | |
| 咁鬼 | r | |
| 喫飯 | v | |
| 嘆 | v | |
| 嚟到 | v | |
| 四圍 | n,r | |
| 四川 | n | 地名 |
| 外賣 | n | |
| 多次 | r | |
| 大力 | a,r | |
| 大戰 | n,v | |
| 好話 | n | |
| 家裏 | n | |
| 對面 | n | |
| 小海 | n | 專名 |
| 巨哥 | n | 專名 |
| 廟 | n | |
| 廢事 | a,v | |
| 得多 | r | |
| 心裡面 | n | |
| 心諗 | v | |
| 快手 | n | |
| 手掌 | n | |
| 手腳 | n | |
| 扶 | v | |
| 抖 | v | |
| 捽 | v | |
| 改 | v | |
| 教畜 | n | |
| 星 | n | |
| 更是 | r | |
| 最多 | r | |
| 有意 | a,v | |
| 有限 | a | |
| 朝頭早 | n,r | |
| 正常 | a | |
| 正話 | r | |
| 死者 | n | |
| 注定 | v | |
| 淫 | a | |
| 溝女 | v | |
| 漢堡包 | n | |
| 無所謂 | a | |
| 熟 | a | |
| 特登 | r | |
| 狗仔 | n | |
| 琴日 | n,r | |
| 琴晚 | n,r | |
| 番鹼 | n | |
| 癡線 | a | |
| 發叔 | n | 專名 |
| 盡量 | r | |
| 直至 | x | |
| 眼色 | n | |
| 睡 | v | |
| 神父 | n | |
| 稱爲 | v | |
| 立刻 | r | |
| 笨 | a | |
| 絲襪 | n | |
| 老細 | n | |
| 而不是 | x | |
| 胸口 | n | |
| 臺灣 | n | 地名 |
| 舊 | a | |
| 舒服 | a | |
| 茄 | n | |
| 表情 | n | |
| 表白 | v | |
| 複雜 | a | |
| 訓 | v | |
| 說了 | v | |
| 課室 | n | |
| 調用 | v | |
| 講解 | v | |
| 賊 | n | |
| 走入 | v | |
| 輕鬆 | a | |
| 轆 | n,v | |
| 途中 | n,r | |
| 過人 | v | |
| 那個 | x | |
| 閃 | v | |
| 阿玲 | n | 專名 |
| 面紅 | a,v | |
| 面色 | n | |
| 馬尾 | n | |
| 馬戲 | n | |
| 鬚 | n | |

## SOFT（27；計入 ok_rate）

| stratum | literals |
|---------|----------|
| high\|gate | 嘉；提供；這個問題 |
| low\|low | 享受；卡；叉；回覆；提示；矛盾；觀；鏈接；隔離；預告 |
| low\|u | 一講；卒；又講；堂；平；界；眼望；篤；船船；袋袋；香香 |
| medium\|gate | 不安；滿；驚訝 |

## OK patterns worth keeping

- **high|gate** 已審列：封閉類 x／r（件、但係、佢、唔、四、若…）；真 V+suffix（做過、傳來、兜過、看完、睇住）；真 n,v（思考、支持、消耗、移動、處理）；已修 verb-suffix 假陽（也好→x、原來→r、世上→n、相→n）
- **high|u plain** 殘片刻意 u：咗去、咗好、我過
- **low|low** 實體名／典型動：學校、巴士、口罩、朱古力、聽／看／問…
- **low|u** 截斷合理 u：你是、個月、地個、我入、我市、我怕、要有、過你；黏着 政／罕 皓

## Gate impact note

- **medium|gate 9 BAD** 已入閘用：假 `a` 令非形與形同桶（一些／寫／代／最後／根據／理解／轉移／關）；假 `n` 令乾淨與名同桶。優先 apply 此 9 列。
- **high|gate 0 BAD** — 本輪 high 閘用抽樣乾淨（先前 r1/r2 修補已反映）。
- **low|u** BAD 唔入閘（缺標行為）；apply 後可抬 trust 成閘用，屬覆蓋升級而非閘毒。

## Confirm

| 指標 | 結果 |
|------|------|
| 全樣本 ok_rate | **0.551** → **FAIL**（>0.90） |
| high\|gate ok_rate | **1.000** → PASS |
| gate 合計 ok_rate | **0.870** → FAIL（差 medium cow-multi） |
| 建議下一刀 | apply medium 9 BAD + low draft 7 BAD；可選 batch 提案 low\|u 高頻 head |

## Files

| path | role |
|------|------|
| `data/pos/audit/full_r1/p1_sample.tsv` | 292 列 verdicts |
| `data/pos/audit/full_r1/p1_summary.md` | 本摘要 |
| `data/pos/audit/full_r1/manifest.json` | 抽樣框 |
