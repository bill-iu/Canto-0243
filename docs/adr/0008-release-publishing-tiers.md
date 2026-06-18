# Release 發佈分層

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 全量發佈、詞庫發佈、免安裝交付、Portable 套件。

交付形態（建置時 pre-build venv）見 [ADR-0006](0006-portable-zero-install-delivery.md)。本 ADR 只定 **發佈節奏、artifact 政策與 CI 契約**。

> **修訂**：tag 觸發全量 CI、雙平台 matrix 全有或全無 — 見 [ADR-0018](0018-split-channel-release.md)（**已取代**下列 §2、§6、§8 之 CI 部分）。發佈改為 Windows 本機 + Intel MacBook 分渠道手動上傳。

## 我們決定

1. **兩層發佈** — **全量發佈**：程式、依賴、詞庫與雙平台 **Portable 套件** 一併更新的正式發佈線；**詞庫發佈**：只更新 `lyrics.db` 與／或 `words-lexicon.json`，Portable zip／`.app` 沿用同一 semver 已發佈版本。
2. ~~**全量觸發** — `release-full` workflow 僅由 strict semver tag 觸發~~ → **ADR-0018**：手動分渠道，無 tag CI。
3. **雙 workflow** — ~~`release-full.yml`~~ + `release-lexicon.yml`（詞庫）；詞庫以 `workflow_dispatch` 觸發。
4. **詞庫掛同一 semver** — 詞庫發佈只替換該 semver GitHub Release 上的 db／json asset；Release notes 註明「詞庫更新 YYYY-MM-DD」。不為純詞庫更新另開 semver tag。
5. **詞庫前置條件** — 目標 semver 上須已有 **Windows zip + macOS x86_64 tar**（ADR-0018；arm64 過渡期不要求）；否則 lexicon workflow fail。
6. ~~**全量 CI 全有或全無**~~ → **ADR-0018**：Windows 可先 Publish，macOS 後補同一 tag。
7. **過渡期手動** — 維護者本地跑 build 腳本 + `gh release upload`（見 [docs/release.md](../release.md)）。
8. ~~**長期 CI push tag 自動全量**~~ → **ADR-0018**：長期以分渠道本機建置為主；CI 保留測試與詞庫 workflow。

**Considered Options**

- 每次 Release 四件套齊更新（無分層）— 詞庫常變時維護者 full build 成本不必要；pre-build 雖可接受（~1–1.5 min／platform）仍浪費 WM 時間。
- 詞庫另開 semver tag — 創作者難對照「程式版 vs 詞庫版」；與「去最新 Release 下載」習慣衝突。
- 全量 CI 一邊 fail 仍發 partial artifact 或沿用舊 platform 檔 — tag 與 artifact 版本混亂。
- 薄包 + 創作者端 wheelhouse（建置時不 pre-build venv）— 曾評估；維護者 full build 更快但改動交付承諾；**維持 ADR-0006 pre-build venv**。
- 過渡期 CI 先做 lexicon、full 長期手動 — 收益不對稱；full 才是 CI 主要價值（雙 WM 齊 artifact）。

**Consequences**

- 須維護 [docs/release.md](../release.md) 手動 checklist，直至 CI 落地。
- CI 實作須分 OS 跑 `build-portable.ps1`／`build-portable.sh`（venv 不可跨 OS）。
- 詞庫發佈不得在未完成全量的 semver 上單獨進行。
- Release notes 須區分「正式版全量」與「詞庫更新（同 tag）」。
