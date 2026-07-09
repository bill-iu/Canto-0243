# ADR-0047: 詞庫體積、音素緊湊與開庫契約

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 詞條庫瘦身、詞條索引瘦身、音素欄位緊湊化、詞庫發佈閘、短語收錄門檻。

整合並取代：[0027](./0027-lyrics-db-schema-slim.md)、[0033](./0033-lexicon-index-slim-and-phrase-admission-gate.md)、[0037](./0037-phoneme-field-compact-encoding.md)、[0038](./0038-relation-index-dedupe-and-phoneme-open-contract.md)、[0039](./0039-relation-leaf-codes-and-syn-degree-cap.md)。

## 1. Schema／索引瘦身（I2 方向）

1. 刪冗餘／未用索引前以 EXPLAIN + 黃金查詢驗證。
2. **短語收錄門檻** — 機構／店名等後綴拒收表；唔以單字「路」通殺。
3. **發佈閘** — 解壓 db／索引體積與 golden parity／bench 約束（見 CONTEXT 閘數值；I3 75MB 目標可修訂）。

## 2. 音素緊湊（j2）

1. `initials`／`finals` 為字典序 id + `.` 分隔；vocab 常量雙端同步 + `lexicon_meta` 指紋。
2. Runtime **只**認 compact；舊 JSON 須 `migrate_phoneme_compact` 或 `build-db`。
3. **開庫契約** — 驗 meta + 抽樣非 JSON；Portable 可自動 migrate；PWA purge 重下渠道包（唔在瀏覽器 migrate）。

## 3. 關係表體積

1. **UNIQUE 去重** — 唔建雙份 unique 索引。
2. **葉碼** — Cilin `group_codes` 存葉碼字串，讀取 expand。
3. **CAP-U@20** — 無向 syn 鄰居度上限；ant／semantic 唔 cap。

**Consequences** — fixture／渠道包必須 j2；改 vocab 要 rebuild；關係寫入見 ADR-0041。
