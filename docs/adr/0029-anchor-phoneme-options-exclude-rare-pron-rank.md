# 錨點選項剔罕見讀音（pron_rank）

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § **錨點選項**、**語境錨點選項**、**等號參考讀音**、**組詞讀音**。延續 [ADR-0004](0004-reference-reading-query-normalize-position-match.md)、[ADR-0028](0028-code-sandwich-equals-unification-and-per-digit-loose-variants.md)。

Grill 共識（2026-07）：`39難`（碼夾等號尾韻）因「難」詞庫列含 rime **罕見**讀音 `no4`，**錨點選項** union 帶入韻母 `o`，誤命中大量 `o` 韻詞。填詞場景應保留預設／常用多讀 union（如 `39起`→`飛機`），但唔應讓罕見讀音滲入一般押韻錨。

## 決定

1. **`anchor_phoneme_options`（錨點選項）**：構建單字 union 時，按 rime `char.csv` **pron_rank** 剔除 **罕見** 讀音；**預設**、**常用**、以及 **pron_rank 未知**（詞庫收錄但 rime 未標）仍入 union。
2. **語境錨點選項**（`contextual_*_options_at_position` 語料掃描支）：**唔**用 pron_rank 剔罕見；反映已收錄詞語在該字位嘅**組詞讀音**（如 `窮?潦倒=` 中「潦」→`lou5`）。
3. **等號參考讀音**：不變；內嵌聲（`2=我3`）等仍走 pron_rank 單列權威。
4. **雙端**：Python `app/domain/lexicon/reference_reading.py` 與 PWA `anchorPhonemeOptions` 須 parity。

## Considered Options

- **尾韻改全走等號參考讀音（剔 union）** — 會收窄 `39起` 類尾韻字面／同韻結果；ADR-0028 已拒絕。
- **語境掃描亦剔罕見** — 可能丟失成語位實際標音；**拒絕**。
- **只修資料刪 `no4`** — 治標，下一個罕見字仍會爆；**拒絕**。

## Consequences

- **行為**：`39難` 唔再因 `no4` 帶 `o`；「潦」單字 `lou5`（**常用**）仍留錨點 union，與語境／後綴對齊並存，**潦倒**類 case 唔受影響。
- **測試**：加 regression（`39難` 唔含典型 `o` 韻誤命中；`潦` 錨點仍含 `ou`）；golden／explain parity 按需更新。
- **ADR-0004**「錨點 union 多讀」以本 ADR 為準：union 僅預設＋常用（＋未知），不含罕見。

## Status

`accepted`（Grill 定案；待實作）