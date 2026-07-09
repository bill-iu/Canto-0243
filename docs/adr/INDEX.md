# Architecture Decision Records

活決策優先讀 **canonical** 檔；標 *stub* 者只作轉址（歷史全文見 git）。

## Canonical（建議閱讀序）

| ID | 主題 |
|----|------|
| [0001](./0001-readiness-gate-server-contract.md) | 就緒閘 server 契約 |
| [0003](./0003-phase3-gate-ui-and-compound-syn-snapshot.md) | 閘 UI 極薄 + 近義複合快照 |
| [0005](./0005-jyutping-anchor-query-syntax.md) | 粵拼錨語法 |
| [0007](./0007-word-ranking-signals.md) | 詞條排序信號 |
| [0009](./0009-ambiguous-jyutping-anchor-dual-results.md) | 歧義 m／ng 雙列 |
| [0010](./0010-compound-queries-via-match-spec.md) | 複合查詢走 MatchSpec |
| [0012](./0012-wildcard-code-anchor-query-syntax-v2.md) | 通配碼錨 v2 |
| [0013](./0013-plus-slot-connector-alias-normalize.md) | `+` 連接符別名 |
| [0014](./0014-serial-phoneme-anchor-and-prefix-wildcard-equals.md) | 串列錨／前綴等號 |
| [0021](./0021-search-usability-layer.md) | 查詢語意解釋文案 |
| [0022](./0022-file-length-300-lines.md) | 單檔 ≤300 行 |
| [0023-runtime → 0043](./0043-runtime-derived-antonyms.md) | Runtime 衍生反義 |
| [0028](./0028-code-sandwich-equals-unification-and-per-digit-loose-variants.md) | 碼夾等號統一 |
| [0029](./0029-anchor-phoneme-options-exclude-rare-pron-rank.md) | 錨點剔罕見讀音 |
| [0031](./0031-394052-canonical-code-and-search-modes.md) | 394052 碼與三檔 |
| [0041](./0041-p2-relation-write-and-pool-projection.md) | 關係直寫 + 池投影入口 |
| [0043](./0043-runtime-derived-antonyms.md) | Runtime 衍生反義（canonical） |
| [0044](./0044-portable-delivery-and-release.md) | Portable 交付 + 分渠道發佈 |
| [0045](./0045-pwa-delivery-and-lexicon-channel.md) | PWA 交付 + 詞庫渠道 |
| [0046](./0046-query-dispatch-seams-and-ssot.md) | 查詢分派 seam + SSOT |
| [0047](./0047-lexicon-volume-and-phoneme-contract.md) | 詞庫體積 + j2 音素契約 |
| [0048](./0048-search-ux-navigation-and-windowing.md) | 搜尋 UX／視窗化／導航 |

## Stubs（superseded）

0002、0004、0006、0008、0011、0016–0020、0023-introduce、0023-runtime、0024–0027、0030、0032–0040、0042 → 見各檔內指向。

## 編號說明

- **缺 0015** — 歷史跳號，未補。
- **0023 曾雙檔** — 靜態 PWA 渠道 vs 衍生反義；後者改 **0043**。
