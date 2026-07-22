# Architecture Decision Records

活決策讀 **canonical**；*stub* 只轉址（全文見 git）。

## Canonical

| ID | 主題 |
|----|------|
| [0007](./0007-word-ranking-signals.md) | 詞條排序信號 |
| [0010](./0010-compound-queries-via-match-spec.md) | 複合查詢走 MatchSpec |
| [0022](./0022-file-length-300-lines.md) | 單檔 ≤300 行 |
| [0028](./0028-code-sandwich-equals-unification-and-per-digit-loose-variants.md) | 碼夾等號統一 |
| [0031](./0031-394052-canonical-code-and-search-modes.md) | 394052 碼與三檔 |
| [0044](./0044-portable-delivery-and-release.md) | 免安裝 + 分渠道發佈（§1 運送歷史；見 0068） |
| [0068](./0068-desktop-pyapp-delivery.md) | **Desktop** + **PyApp** 交付（正名；取代 venv 運送） |
| [0070](./0070-macos-app-bundle-primary-entry.md) | macOS 主入口 **`.app`**（退役 `.command`；單次 Gatekeeper） |
| [0045](./0045-pwa-delivery-and-lexicon-channel.md) | PWA 交付 + 詞庫渠道 |
| [0046](./0046-query-dispatch-seams-and-ssot.md) | 查詢分派 seam + SSOT |
| [0047](./0047-lexicon-volume-and-phoneme-contract.md) | 詞庫體積 + j2 音素 |
| [0048](./0048-search-ux-navigation-and-windowing.md) | 搜尋 UX／視窗化／**查詢語意解釋** |
| [0049](./0049-readiness-gate.md) | 就緒閘 |
| [0050](./0050-relation-runtime.md) | 近反義 runtime |
| [0051](./0051-jyutping-and-anchor-phoneme.md) | 粵拼錨 + 歧義雙列 + 錨點選項 |
| [0052](./0052-positional-anchor-query-syntax.md) | **位置錨語法**（通配碼錨／`+`／串列） |
| [0053](./0053-connective-compound-hybrid.md) | **連接詞複合**：詞庫∪合成 + syn/ant 互斥 |
| [0054](./0054-portable-read-path-no-write-connective.md) | **Portable**：連接詞合成唔寫庫 + word_cache disk 暖啟 |
| [0055](./0055-portable-gate-db-probe-word-cache-tail.md) | **Portable 閘**：DB 探針解鎖；word_cache→tail |
| [0057](./0057-categorized-rime-lexicon-source.md) | **Rime 分類詞語來源**取代 legacy phrase |
| [0058](./0058-project-pos-sidecar-carrier.md) | **專案自建詞性**：獨立 **詞性載體**（唔入 lyrics.db 主表） |
| [0059](./0059-portable-release-fingerprint-update-notice.md) | **套件發佈指紋**＋**套件更新提示**（Desktop；唔自動覆蓋） |
| [0060](./0060-project-pos-inlex-fragment-alias.md) | **庫內難標 u**：fragment 分流 + **詞性字面別名** + 雙軌覆蓋 |
| [0061](./0061-pos-family-leaf-subtypes.md) | **語彙族細分**：成語／俗語／諺語 + 篩選 + 外源只提案非 dependency |
| [0062](./0062-rhyme-equals-initial-caret.md) | **同韻 `=`／同聲 `^`**（舊左 `=` 相容） |
| [0063](./0063-lf-line-endings.md) | **文字檔一律 LF**（`.gitattributes`／editorconfig／pre-commit 自動修） |
| [0064](./0064-workbench-candidate-page-size.md) | **工作台候選**首屏 400 + load-more（廢 120 硬頂） |
| [0065](./0065-workbench-manual-input-and-undo.md) | **工作台手改**（雙擊單格／段手打）+ **句稿復原**入條件面板 |
| [0066](./0066-workbench-wildcard-and-phoneme-ref.md) | **通配符格** + **韻／聲參考字串**（覆蓋／長度跟勾選） |
| [0067](./0067-portable-venv-pack-transport.md) | ~~venv.pack 運送~~ → superseded by **0068** |
| [0069](./0069-workbench-replacement-span-line-width.md) | **替換段**寬＝句長（取消 4 格硬頂；phoneme≤6；skip@20） |

## Stubs

0001–0006、0008–0009、0011–0014、0016–0021、0023（雙檔）、0024–0027、0029–0030、0032–0043 → 見各檔 `superseded by`。

## 編號說明

- **缺 0015** — 歷史跳號。
- **0023 曾雙檔** — PWA → 0045；衍生反義 → 0050。
- 位置錨 **0052**；解釋文案併入 **0048 §4**。
