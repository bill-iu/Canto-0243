# 詞條庫資料授權 / Lyrics database license

**適用檔案 / Applies to:** `lyrics.db`、`words-lexicon.json`（同版 Release tag 匯出 / export for the matching release tag）

**Canto-0243 程式**依 [Canto-0243 License](LICENSE)（非商業、禁止再打包等 / non-commercial, no repackage, etc.）。  
**本文件只適用詞級標音資料**，唔涵蓋程式、介面或 zip 內其他 curated 列表。  
**Canto-0243 program code** is under [Canto-0243 License](LICENSE). **This file covers lexicon data only**, not the app, UI, or other curated lists in the portable zip.

---

## 摘要 / Summary

**詞條庫**為**混合編纂**；上述兩個檔案之對外分發條款整體為 **Creative Commons 署名-相同方式分享 3.0**（[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)），因編纂內含 **相同方式分享** 素材（尤其 **CC-Canto**）。你可依 CC BY-SA 3.0 分享或改作**資料檔**，須標明來源並對衍生作品沿用相同授權。  
The lexicon is a **mixed compilation**. Distribution of these **data files** is under **CC BY-SA 3.0**, because the build includes **ShareAlike** material (notably **CC-Canto**). You may share and adapt the **database files** under CC BY-SA 3.0 with attribution and ShareAlike on derivatives.

---

## 主要上游來源（非 exhaustive）/ Major upstream sources

詳見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) § maintainer-built multi-char lexicon。  
See also [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) § maintainer-built multi-char lexicon.

| 來源 / Source | 連結 / Link | 在 `lyrics.db` 角色 / Role | 上游授權 / Upstream license |
|---------------|-------------|---------------------------|----------------------------|
| CC-Canto | [cantonese.org/download](https://cantonese.org/download.html) | 多字讀音（主要 SA 成分）/ Multi-char readings (major SA) | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/) |
| words.hk 粵典詞表 | [wordslist](https://words.hk/faiman/analysis/wordslist/) | 多字讀音 / Multi-char readings | 公有領域（致謝 appreciated）/ Public domain |
| 開放詞典 · 粵語詞典 | [kaifangcidian.com](https://kaifangcidian.com/xiazai/) | 補洞 / Fill gaps | [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| Rime／essay／maintainer ingest | 見 NOTICES / See NOTICES | 單字與關係管線 / Single-char & relations | 依各上游 / Per upstream |
| Maintainer 勘誤 | `data/lexicon/lexicon_corrections.tsv` |  curated 修正 / Curated fixes | 本專案 curation / Project curation |

---

## 再分發 `lyrics.db` 或 `words-lexicon.json` 時 / If you redistribute these files

1. **署名 / Attribute** CC-Canto、words.hk 及其他所用來源（見 THIRD_PARTY_NOTICES）。  
2. **相同方式分享 / ShareAlike**：若發布改編後之詞庫，須以 **CC BY-SA 3.0**（或相容 SA 條款）授權衍生作品。  
3. **唔好**假設**應用程式**係 CC BY-SA——只有呢兩個**資料檔**受本文件約束。  
   **Do not** assume the **application** is CC BY-SA — only these **data files**.

---

## 過渡期說明 / Transition note

移除 CC-Canto 預設 merge 管線另案追蹤（GitHub issue [#9](https://github.com/bill-iu/Canto-0243/issues/9)）。在此之前，Release 上 **`lyrics.db` 資產**仍應標 **CC BY-SA 3.0 混合**。  
Removing CC-Canto from the default merge pipeline is tracked in issue [#9](https://github.com/bill-iu/Canto-0243/issues/9). Until then, release **`lyrics.db`** assets remain **CC BY-SA 3.0 mixed**.
