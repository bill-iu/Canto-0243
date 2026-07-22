# u_inlex_top2000_nf manual POS label — part2

**File:** `data/pos/audit/u_inlex_top2000_nf/label_part2.tsv`  
**Universe slice:** in-lexicon still-`u` top2000_nf batch part2  
**n:** 400  
**Date:** 2026-07-19  

**Rules:** `n/v/a/r/x` multi-ok（comma 按 a,n,r,v,x 字母序）；`u` only fragment/unclear；`family=idiom` 僅真熟語；`voice` 全空；`note` 只標 `u` 理由。

## Counts

| pos bucket | n | % |
|------------|--:|---:|
| formal（非 u） | 399 | 99.75% |
| `u` fragment/unclear | 1 | 0.25% |
| **total** | **400** | 100% |

| family | n |
|--------|--:|
| empty | 393 |
| `idiom` | 7 |
| voice non-empty | 0 |

### Formal tag hits（multi 計入每個 tag；一列可多 hit）

| tag | hits |
|-----|-----:|
| n | 210 |
| v | 128 |
| a | 81 |
| r | 24 |
| x | 23 |
| multi rows | 67 |

## `u` patterns（1）

| pattern | n | examples |
|---------|--:|----------|
| 合成詞殘字 | 1 | 牴 |

**Full `u` list (1):** 牴（牴觸殘字）

## `family=idiom`（7）

| literal | pos |
|---------|-----|
| 睇唔過眼 | a,v |
| 至關重要 | a |
| 一如既往 | a,r |
| 前所未有 | a |
| 徒勞無功 | a,v |
| 斬釘截鐵 | a,r |
| 語無倫次 | a |

未標 idiom（固定但非成語桶）：不負責任`a`（能產貶評）、聽人講`v`（能產）、打圓場`v`（動詞短語）、全國人民`n`（政稱）。

## Formal patterns worth keeping

- **專名／地名／品牌 → n**：洛杉磯、珠江、李白、法拉利、唐朝、嫦娥、比利時、小米、天虹、公安部
- **粵語常用**：望實、有講、熊人、硬淨、爭在、睇唔過眼、第二度、粒聲、耳筒、腸仔、螺絲批、覺覺豬、驚青、驟眼、蒲、出糧、企定定、唔忿氣、大食、亞叔、屋村、拜山、殘廁、猛咁、睇水、組仔、跣、經已、些少、上畫
- **擬聲／語氣 → x**：耶、唷、汪汪、南無
- **連／介／助 → x**：毋、皆因、縱然、起見、連同、以致、乃、箇
- **科技／政經 NP → n**：變壓器、介質、模擬器、智能手機、驅動程序、基站、港股、專櫃

## Borderline（已標 formal；可再審）

| literal | pos | note |
|---------|-----|------|
| 有着 | v | 普通話「有着」結構；近體標記黏着 |
| 爭在 | r,x | 粵反詰「爭在乎」；近虛 |
| 致 | v,x | 致使／以致義；兩棲 |
| 第二度 | n,r | 粵「另一處」；亦序數 |
| 粒聲 | n | 多見於「冇粒聲」；量+名 NP |
| 淑／霖／楠／芸／淩 | n | 多專名用字；非純殘則留 n |
| 南無 | x | 佛教用語；嘆／虛 |
| 該死 | a,x | 形／咒罵語 |
| 吱喳 | v,x | 擬聲作動 |
| 幻 | a,n | 虛幻／幻象；動詞義少 |
| 維 | n,v | 維度／維持／姓 |
| 末 | n | 末端主義；副用較少故不 multi |

## Policy notes

1. **唔造 POS**：合成詞殘字（牴）一律 `u`。
2. **multi 從嚴**：只標兩棲皆常見者；comma 按 a,n,r,v,x。
3. **family**：僅真成語／粵固定熟語標 `idiom`。
4. **voice**：本批無語態對，全空。
5. **下一步**：與 part1／3–5 合併後可 upsert（note 帶 `u-inlex-top2000-nf;agent-label;review`）再抽 gate sample。

## Files

| path | role |
|------|------|
| `data/pos/audit/u_inlex_top2000_nf/label_part2.tsv` | 400 列已填 pos |
| `data/pos/audit/u_inlex_top2000_nf/label_part2_summary.md` | 本摘要 |
