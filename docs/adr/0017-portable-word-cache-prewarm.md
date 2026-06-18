# Portable 詞庫快取預暖

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 詞庫快取索引、免安裝交付、Portable 套件。

## 我們決定

1. **建置時預暖** — `scripts/warm_word_cache.py` 自 bundle 內 `lyrics.db` 建**詞庫快取索引**並寫入 `.cache/word_meta.bin`；`build-portable.ps1`／`build-portable.sh` 每次建置皆執行。
2. **內容指紋** — 磁碟快照以 `lyrics.db` 的 size + SHA-256 綁定，**唔綁路徑**；Portable 解壓後路徑變更仍可還原。
3. **冷建 fallback** — 指紋不符或無快照時仍走 runtime 冷建；優先使用 DB 已存的 `finals`／`initials` 建索引，減少逐行粵拼推導。
4. **就緒閘不變** — 不新增 `/ready` 階段欄位；還原與冷建對創作者仍統一為**詞庫快取索引**載入。

**Considered Options**

- 僅優化冷建、不打包快照 — Portable 首次仍 ~10s+，不符免安裝體感。
- 指紋含絕對路徑 — 建置機還原成功、創作者解壓後必失效。
- UI 區分「快取還原／索引建立」— 收益低且擴張 `/ready` 契約。

**Consequences**

- Portable zip／`.app` 體積略增（`.cache` 與 `lyrics.db` 同階層）。
- 詞庫發佈只換 `lyrics.db` 時指紋變更，首次啟動會冷建一次（已微優化）。
- 維護者可單獨執行 `python scripts/warm_word_cache.py <bundle-root>` 刷新快照。
