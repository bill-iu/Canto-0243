# ADR-0038: 關係索引去重 + 開庫音素契約

J2 緊湊化後 `lyrics.db` ~90 MB，距 I3 目標 75 MB 仍差一截。`word_relations` 同時有 **表 CONSTRAINT UNIQUE**（`sqlite_autoindex_…`）與顯式 **`uq_word_relation`**，各 ~6 MB。EXPLAIN 確認雙向 `idx_word_rel_*` 與字表索引仍有用；第一刀只拆重複 UNIQUE（**U1**：留 autoindex，`finalize` DROP 顯式 uq）。

另：**M1** 對 JSON 音素欄 decode 為空會令舊 OPFS／本機庫 **靜默零結果**。**C1**：開庫驗 `lexicon_meta` + 抽樣；本機 Python 可自動 `migrate_phoneme_compact`；PWA purge 渠道快取並要求重載（唔喺瀏覽器 migrate）。

**閘（G75-A）**：I3 75 MB 目標暫不硬改；I2 95 MB 仍為硬閘。

**後果**：`finalize_lexicon_indexes` 與 bootstrap 唔再建第二份 UNIQUE；舊庫首次啟動可能多一次遷移／重下包。
