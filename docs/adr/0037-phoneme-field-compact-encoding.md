# ADR-0037: 音素欄位緊湊化（J2 / I3）

`words.initials`／`finals` 由 JSON 字串（如 `["an","iu","ou"]`）改為**字典序 id + `.` 分隔**（S1，例 `14.40.51`），以縮短表內容與 `idx_length_code_finals` 鍵。唯一韻／聲集合小（~61／~25），適合固定 vocab 常量（K1；`''` → id 0）。未知 token 於 encode／建庫時 **fail**。

**存放**：代碼常量（Python `app/domain/lexicon/phoneme_codec.py` 與 PWA `client/src/db/phoneme-codec.ts` 同步）+ `lexicon_meta` 指紋（`phoneme_vocab_version`／`phoneme_vocab_fingerprint`）。**M1**：runtime **只**認緊湊形；舊 JSON 庫須 `python -m ingest.migrate_phoneme_compact` 或全量 `build-db`。

**查詢**：整詞 equals 仍用欄位 equality（compact 字面）；前綴通配等多 slot 用 **P1** 定界安全 `LIKE`（整段 encode span，唔做裸 substring）。PWA／word_cache 倒排喺 **decode 後 token** 上建。

**閘（I3-A）**：CONTEXT 目標 ≤75MB／索引 ≤35MB 暫保留；encode 後量度再定硬 cap 或改 CONTEXT。唔為砌 75 而喺本 PR 亂砍 `word_relations`。

**量度（首次 compact + VACUUM，~439k 列）**：解壓 `lyrics.db` 約 **106 MB → ~90 MB**；仍高於 75 MB 目標——差額主要喺 `word_relations` 與字面索引，另開瘦身。I2 95 MB 閘仍過。

**後果**：fixture／本機 `lyrics.db` 必須遷移；雙渠道版本須對齊；vocab 擴充要改常量 + 重建。
