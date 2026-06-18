# 分渠道全量發佈（Windows 本機 + Intel MacBook）

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 分渠道發佈、全量發佈、詞庫發佈。

取代 [ADR-0008](0008-release-publishing-tiers.md) 中 **§2 全量觸發**、**§6 全量 CI 全有或全無**、**§8 長期 CI**（tag 觸發 `release-full.yml`）。ADR-0008 其餘分層（全量 vs 詞庫、同一 semver）仍有效。

## 我們決定

1. **兩條建置渠道** — **Windows 渠道**：維護者 Windows 本機 `build-portable.ps1` + `release-windows-local.ps1` 上傳 zip／db／lexicon；**macOS 渠道**：Intel MacBook fork 同步後 `release-macos-local.sh` 建 **x86_64** tar 並上傳至**同一 upstream Release tag**（`GH_REPO` 指向上游，fork 不作第二下載頁）。
2. **發佈時序** — Windows zip 齊即 **Publish** Release；macOS x86_64 tar **之後**補上同一 tag。Release notes 須註明 macOS 待補／arm64 暫不提供。
3. **停用 CI 全量** — 移除 tag 觸發之 `release-full.yml` 與 `release-macos-intel-beta.yml`；保留 `ci.yml`（測試）與 `release-lexicon.yml`（詞庫）。
4. **詞庫前置（修訂）** — 詞庫發佈須該 tag 已有 **Windows zip + macOS x86_64 tar**；**不要求** arm64 tar（過渡期不提供）。
5. **架構過渡** — Intel Mac 無法 native 建 arm64；arm64 tar 待日後 M 系列建置機或 CI 再補，不阻塞 x86_64 渠道。

**Considered Options**

- 維持 `release-full.yml` tag CI — macOS matrix 反覆失敗、與本機驗收脫節；放棄。
- macOS 發佈在 fork Release — 創作者須兩處下載；與「同一 semver 一頁」衝突。
- 五件套齊才 Publish — 阻塞 Windows 創作者；改為 Windows 先發、macOS 後補。
- Intel Mac cross-build arm64 — 不可行（無 arm64 slice）；維持分架構 tar。

**Consequences**

- [docs/release.md](../release.md) 為發佈唯一操作手冊；須維護 `release-windows-local.ps1` 與 `release-macos-local.sh`。
- MacBook 須對 upstream 有 `gh` write 權限；建議 `--tar-only` 避免覆寫 Windows 上傳的 db／json。
- 詞庫 workflow gate 改為 zip + x86_64，唔再要求 arm64。
