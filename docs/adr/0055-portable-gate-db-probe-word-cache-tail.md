# Portable 就緒閘 = DB 探針；word_cache 改 tail

**Portable 就緒閘解鎖**唔再等 **詞庫快取索引** 建完。解鎖條件：進程 lifespan 完成後 **DB 可查**（探針：`words.char = 事業` 存在）。**詞庫快取索引** 改入 **離線啟動預載** tail：閘解鎖後背景建／restore；**背景預載標示** 以含 word_cache 權重嘅誠實進度反映至 **啟動完畢**。解鎖後即可 **查詢分派**；cache 未好時走既有 SQL 降級。`GATE_DEGRADE_MS` 唔再作為「索引未完就開閘」主路徑。

對齊 PWA「開庫即可搜、索引背景暖」體感。拒絕：閘仍綁全量 word_cache；解鎖後擋搜等 cache。見 CONTEXT § 就緒閘解鎖、啟動完畢、背景預載標示、詞庫快取索引。
