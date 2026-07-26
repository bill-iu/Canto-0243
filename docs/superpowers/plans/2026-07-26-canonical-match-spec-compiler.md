# Candidate 03：Canonical MatchSpec compiler seam 實作計劃

日期：2026-07-26  
狀態：grilling 完成，待實作  
目標分支：`dev`

## Problem Statement

ADR-0046 已指定 `ParsedQuery → MatchSpec` 為缺字型查詢的 dispatch seam，
但現行 Python 與 TypeScript implementation 仍把編譯知識分散在 grammar、
registry wrapper、position-match filter、candidate source 與 execution。

多個 query 形態各自攜帶 width、anchor position、code slots、mask 及特殊
flag；同一約束又可能同時出現在 slots、mask 與任意 `extra` 字典。execution
因此要補預設值、反推約束或修改傳入的 MatchSpec。近期中間位置 `@`、
equals span 稀疏碼及候選來源完整性修正都要跨 Python／TypeScript 多個
locality 同步修改，證明現有 module 未把 slot placement 與約束傳遞藏好。

現行 registry 主要只轉接 grammar 的 `toMatchSpec`，interface 接受所有
ParsedQuery 並以 `null`／`None` 同時表示「不適用」與「漏實作」。兩端的
代表案例亦各自保存，且多數只檢查部分欄位；即使完整 MatchSpec 已經漂移，
測試仍可能通過。

句格工作台另有 `ReplacementPlanV1 → MatchSpec` implementation。若只整理
一般查詢，工作台會繼續成為可繞過 canonical contract 的第二個入口。

本重構要完成 ADR-0046 的原意：由深層 compiler module 獨佔 MatchSpec
形成及驗證；execution 只讀完整、唯讀的語意規格。Python、PWA OPFS VFS
及瀏覽器 sql.js 可使用不同 physical execution plan，但必須共享同一
可觀察語意。

## Solution

### Compiler ownership

- Grammar 只負責把 raw query 解析成 typed ParsedQuery。
- Query compiler 只接受宣告使用 MatchSpec 的 typed query union。
- `compileQuery` 對合法輸入必定回傳完整 MatchSpec，不回傳 `null`／`None`。
- 純漢字詞條 lookup、一般 code lookup、relation lookup、unmatched 與 hint
  路徑留在原有 dispatch，不進入 compiler。
- 已宣告使用 MatchSpec 卻不能編譯，視為 implementation defect；使用者
  語法錯誤仍由 parser 產生 unmatched／hint。
- Workbench 另有 `compileReplacementPlan` input adapter；它與 query
  compiler 共用 canonical builder、投影與 invariant validation，但不
  吸收 session、undo、候選分頁或 UI 責任。

### Canonical MatchSpec

Compiler 對外輸出單一 canonical、唯讀 contract：

- width 必須大於零。
- slots 必定存在，採 deterministic ordering；每個位置及 value 都合法。
- 相同位置可存在不同維度的相容約束，但重複或互相衝突的同類約束會被拒絕。
- slot 的 collection value 正規化為 deterministic、不可變序列，避免
  mutable set 破壞 parity 或 cache identity。
- mask 必定存在且長度等於 width；它是 compiler 由 slot 語意生成的 hot-path
  投影，不是第二個可獨立修改的真相來源。
- equals span、compound policy、ranking policy、candidate scope 及 dual
  phoneme branches 使用明確 typed fields。
- 移除任意 `extra` 字典及平行 boolean flags。
- literal positions、partial rhyme／initial、prefix wildcard 等可推導資料
  不另存第二份權威狀態。
- dual phoneme 只建立目前需要的 initial／final typed branches，不引入
  通用 boolean-expression DSL。
- TypeScript 以 readonly value 加 compiler-boundary freeze 落實不可變；
  Python 使用 frozen dataclass 與 tuple。
- Compiler 出口及測試驗證 invariants；逐列 hot path 不重跑 validation。

### Semantic and physical separation

- MatchSpec 只描述「要匹配甚麼」，不包含 SQL、OPFS、ORM 或 index 指令。
- 語意上要求完整候選宇宙的情況以 typed candidate-scope policy 表達。
- Python、OPFS VFS 與 sql.js execution adapter 依本身能力選擇 candidate
  source 及 physical plan。
- Physical planning 每次 query／candidate snapshot 計算一次，不進入逐列
  filter。
- 同一 paging／load-more session 重用 immutable MatchSpec。
- 本重構不新增全域 compiler cache；若日後量測證明 physical planning
  成為瓶頸，再獨立設計可失效的 plan cache。

### Cross-runtime semantic authority

語意裁決優先次序：

1. `CONTEXT.md` 與已接受 ADR。
2. 明確產品案例及回歸測試。
3. Python 與 TypeScript 一致的現行行為。
4. 文件未定義而兩端不同時，採不改使用者可見結果的最小方案，並列為待決項。

建立人工審核的 shared golden corpus：

- 每個 query case 包含 raw query、mode 及完整 canonical MatchSpec。
- Python 與 TypeScript 讀取同一份 expected output。
- 覆蓋所有宣告使用 MatchSpec 的 query kind，以及頭／中／尾位置、稀疏碼、
  equals span、dual phoneme、compound 與錯誤邊界。
- Workbench plan 使用相同 canonical output 格式，但保留獨立 input case
  文件，避免混淆兩種 domain input。
- Expected output 不由任何 runtime implementation 自動產生。
- CI 以 exact canonical equality 驗證，並檢查每個 MatchSpec query kind
  至少有一個完整案例。

### Migration policy

- 以小 commit 分階段建立新 interface、compiler 及 caller cutover。
- 遷移中可使用短期 source-level adapter，令每個 commit 維持 green。
- Production caller 一旦切換便只走新 compiler，不設 feature flag 或
  新舊 compiler 雙跑。
- 每條 execution path 切換時，同時刪除該路徑的補約束及 fallback。
- 已確認的語意 bug 先加 shared golden regression case，再以獨立 commit
  修復；不與純搬遷混在一起。

## Preflight

開始實作前：

1. 保持在 `dev` 並同步 `origin/dev`；確認 working tree 沒有不相關變更。
2. 安裝 repo git hooks，確保所有文字檔為 LF。
3. 跑完整現有 query golden、MatchSpec、position-match、workbench parity、
   client build 及 Python 測試，保存 baseline。
4. 使用現有 browser benchmark、search performance marks 及 Python mask
   benchmark 保存改動前數據。
5. Baseline 至少包括 mask、稀疏碼、equals span、phoneme anchor、compound、
   workbench candidate 與純漢字詞條 lookup。
6. 若 baseline 已失敗，先記錄並分離既有問題；不要把無關修復混入本候選。

## Commits

以下每個提交都必須保持 codebase 可建置、可測試及可回退。若發現多個既有
語意差異，為每個差異插入獨立 regression commit，不要把它們壓成一次修復。

### Phase A：鎖定 contract 與決策

#### Commit 1：建立完整 shared MatchSpec golden corpus

- 把兩端現有代表案例遷移成單一、人工審核的完整 canonical expected output。
- 保留 workbench plan cases 為獨立 input corpus，但使用同一 output shape。
- 先覆蓋現行文件已明確定義且雙端一致的案例。
- Test runner 只透過公開 serializer 比較完整輸出，不讀 implementation helper。
- 不改 production caller 或查詢結果。

#### Commit 2：加入 query-kind coverage gate

- 從 query-kind meta SSOT 取得所有宣告使用 MatchSpec 的 kind。
- TypeScript 與 Python 測試都驗證每個 kind 有 golden case。
- 加入「lookup kind 不得誤進 MatchSpec compiler」的 characterization tests。
- 明確覆蓋純漢字 lookup 及其生成詞條行為，防止本重構改變該路徑。

#### Commit 3：記錄 superseding architecture decision

- 新增 canonical MatchSpec compiler ADR。
- 新 ADR supersede ADR-0046 的 compiler contract，以及與 typed candidate
  scope 衝突的舊執行 flag 表述。
- ADR-0046 只加入 superseded link，不重寫歷史內容。
- 更新 `CONTEXT.md` 的 compiler、canonical MatchSpec、candidate scope、
  semantic spec 及 physical plan 詞彙。
- 不在 ADR 寫 commit 或暫時 adapter 細節。

### Phase B：建立 canonical value module

#### Commit 4：加入 canonical MatchSpec types 與 serializer

- 在不切換 production caller 的情況下加入 readonly／frozen canonical types。
- 為 equals span、compound、ranking、candidate scope 及 dual branches 建立
  明確型別。
- Canonical serializer 使用固定 key 及 slot 次序，供兩端 golden parity。
- 保留舊 MatchSpec 作短期遷移來源，但新 module 不接受任意 `extra`。

#### Commit 5：加入 compiler finalizer 與 invariant tests

- 建立 compiler 私有 mutable draft 及唯一 finalizer。
- Finalizer 驗證 width、slot bounds、value、衝突、branch width 及 equals span。
- 由 slots 生成 deterministic mask、literal positions projection 及其他可推導
  hot-path 資料。
- TypeScript freeze nested values；Python 轉換為 frozen dataclass／tuple。
- 加入 invalid draft tests，確認錯誤在 compiler seam 發生。

#### Commit 6：加入短期 legacy-to-canonical migration adapter

- Adapter 只供尚未切換的 production caller 及 characterization tests。
- 集中讀取舊 `extra`，不得把舊欄位知識複製到多個 execution caller。
- Adapter output 必須通過同一 finalizer 與 exact golden tests。
- 標明刪除條件及目標 commit；不得成為正式公開 interface。

### Phase C：實作 strict query compilers

#### Commit 7：建立 MatchSpecQuery typed union 與 strict compiler shell

- TypeScript 建立 discriminated MatchSpecQuery union。
- Python 建立對等的 typed union／runtime assertion。
- Routing adapter 負責把 manifest 所宣告的 query kind 收窄後交給 compiler。
- Compiler shell 對 unsupported kind 立即失敗，不回傳空值。
- 暫不切換 production dispatch。

#### Commit 8：遷移 equals、serial 與 plus families

- 把 width、equals span、prefix placement、稀疏 code slots、literal anchor
  placement 搬入 compiler implementation。
- Grammar 留下 parse responsibility，不再成為新 compiler 的 dependency。
- 加入頭／中／尾 anchor、code sandwich 及 prefix wildcard exact cases。
- 若發現現行位置或稀疏碼 bug，以獨立 regression commit 修復後再繼續。

#### Commit 9：遷移 mask、rhyme 與 wildcard-code families

- 將 mask 內容轉成 canonical slot constraints，再由 finalizer 投影 mask。
- 以 slot kinds 表達 partial rhyme／initial，不保留平行 flags。
- 覆蓋 literal priority、serial phoneme、triple anchor 與中間 reference cases。
- 確認完整候選宇宙需求由 typed candidate scope 表達。

#### Commit 10：遷移 jyutping、ping-ze 與 relation／compound families

- 建立明確 dual phoneme initial／final branches。
- Ping-ze base query 透過 strict compiler recursion，不回到 registry。
- Compound kind、connective 及 rhyme anchor 使用 typed compound policy。
- 不建立通用 boolean expression 或 backend-specific plan。
- 完成所有 MatchSpec query kind 的 TypeScript exact golden coverage。

#### Commit 11：建立 Python 對等 query compiler

- 依相同 family 次序將 Python grammar builders 搬入 compiler module。
- 每完成一個 family 便跑 shared exact corpus。
- Python output 與 TypeScript output 必須 byte-for-byte canonical 等價。
- 不直接翻譯 TypeScript implementation；兩邊以 shared cases 與 contract
  對齊語意。

### Phase D：讓 execution 只讀 canonical spec

#### Commit 12：切換 TypeScript execution contract

- Position-match execution 改為只接受 canonical MatchSpec。
- 移除 optional slots／mask 補值、`extra` cast 及 runtime spec mutation。
- Phoneme index 是否已預篩等臨時狀態留在單次 execution context。
- Candidate source selection 讀 typed semantic policy，再建立 backend-local
  physical plan。
- 舊 caller 暫由單一 migration adapter 進入；已切 caller 不得走 adapter。

#### Commit 13：切換 Python execution contract

- Python position-match、candidate source 與 filter 改為只讀 frozen MatchSpec。
- 移除 `extra` lookup、mask／slot 補估及 mutable spec 操作。
- Candidate scope 決定語意完整性；ORM／cache source selection 留在 execution。
- 與 TypeScript 跑相同結果集及完整候選宇宙 regression tests。

#### Commit 14：切換一般查詢 production dispatch

- TypeScript query dispatch 改用 strict `compileQuery`。
- Python query dispatch 改用對等 compiler。
- Query explain IR 讀 canonical MatchSpec，不保留獨立重建知識。
- 每邊切換後立即跑 golden query、explain、position-match 與 lookup regressions。
- 不保留 production feature flag、新舊雙跑或 silent fallback。

### Phase E：接入 workbench 並刪除舊 seam

#### Commit 15：實作 canonical workbench compiler entry

- TypeScript 與 Python `compileReplacementPlan` 使用共用 finalizer。
- 保留 ReplacementPlan 的 domain mapping，但移除平行 MatchSpec 拼裝規則。
- Contiguous phoneme slots、equals span、candidate scope 與 sparse code 使用
  canonical typed representation。
- Workbench plan corpus在兩端做 exact canonical equality。

#### Commit 16：切換 workbench planners 與 snapshot callers

- PWA worker、sql.js fallback 及 Python workbench planner 改用 canonical entry。
- 同一 candidate snapshot／load-more session 重用 immutable MatchSpec。
- 不改 selection version、snapshot identity、POS projection、relaxation、undo
  或候選排序。
- 跑 workbench contract、planner、snapshot、candidate-session 及 reported
  regression tests。

#### Commit 17：刪除舊 registry、grammar builders 與 migration adapter

- 刪除 Python／TypeScript MatchSpec registry wrapper。
- 刪除 grammar 內 `toMatchSpec`／`to_match_spec` implementation。
- 刪除 partial representative validator、舊 serializer、legacy-to-canonical
  adapter 及已無 caller 的 helper。
- Canonical MatchSpec 成為唯一 production execution contract。
- 以 deletion test 確認 compiler knowledge 沒有重新散落到 grammar 或 filters。

#### Commit 18：收緊 compile-time 與 CI guards

- 禁止 production code 直接建構未 finalise 的 MatchSpec。
- CI 檢查 query kind coverage、shared corpus、generated meta 及 exact parity。
- 結構檢查禁止新增任意 `extra`、grammar compiler 或 execution spec mutation。
- Guard 聚焦 module interface 與禁止行為，不綁死檔案行數或私有 helper 名稱。

### Phase F：效能與跨渠道驗收

#### Commit 19：擴充現有 benchmark workload

- 沿用現有 browser benchmark 與 search performance marks，不建立平行框架。
- 加入真正經過 MatchSpec 的 mask、稀疏碼、equals span、phoneme、compound
  及 workbench cases。
- 分開記錄 compiler、physical planning、engine、冷查、暖查及 load-more。
- JSON output 包含 backend、lexicon version、裝置／瀏覽器識別與 corpus version。
- Python benchmark 使用對等 query 類型及可比較的 corpus identity。

#### Commit 20：完整驗收與文件收尾

- 跑 TypeScript typecheck、client build、全部 query／position-match／workbench
  self-check、Python tests、golden parity 與 explain parity。
- 驗證純漢字 lookup、生成詞條、提示文字、排序及 pagination 沒有改變。
- 在 desktop browser 分別測 OPFS VFS 與 sql.js fallback。
- 在實機手機 PWA 跑相同 corpus，覆蓋冷查、暖查及 load-more。
- 同一裝置與 backend 的暖查中位數／p95 不得出現超過約 10% 的穩定退步。
- Latency 不設為 CI 硬門檻；保存 before／after JSON 並在 handoff 如實報告。
- 更新活文件中的正式 module interface、測試及 benchmark 操作方式。

## Decision Document

- Grammar 只 parse；compiler 獨佔 ParsedQuery／ReplacementPlan 到 MatchSpec 的
  語意轉換。
- Query compiler 使用 strict MatchSpecQuery input，不以空值表示漏實作。
- Query 與 workbench 保留不同 input adapter，共用 canonical finalizer。
- MatchSpec 是 canonical、immutable、完整的語意 value。
- Slots 是逐位置約束 SSOT；mask 是 compiler 生成及驗證的 hot-path 投影。
- 移除任意 `extra` 及可由 slots／typed policy 推導的平行 flags。
- Dual phoneme 使用明確兩分支，不引入通用 boolean DSL。
- Semantic MatchSpec 不包含 backend-specific physical plan。
- Candidate scope 表達語意完整候選宇宙需要；execution 決定具體 source。
- 不新增全域 compiler cache。
- Python 與 TypeScript 各自保留 runtime adapter，以 shared exact golden corpus
  對齊語意。
- Production 不保留新舊 compiler 雙軌或 silent fallback。
- 語意 bug 與純搬遷分開 commit。
- 新 ADR supersede ADR-0046 的相關活決策；舊 ADR 保留歷史。

## Testing Decisions

良好測試穿過 parser、compiler 或 execution 的公開 interface，驗證 canonical
output、結果集及可觀察行為；不測 draft layout、私有 helper 或 switch 寫法。

必測 module：

- Query parser → strict compiler：所有 MatchSpec query kind。
- ReplacementPlan → canonical compiler：一般、contiguous phoneme、sparse code、
  unanchored scan 與 relaxation 代表案例。
- Canonical finalizer：width、slot bounds、衝突、mask projection、branch width、
  equals span 及 immutable collection。
- Python／TypeScript exact canonical parity。
- Position-match execution：mask、equals、phoneme、ping-ze、compound、完整候選
  universe 及 pagination。
- Query dispatch：MatchSpec family 進 compiler；lookup family 不進 compiler。
- Query explain IR：只投影 canonical MatchSpec。
- Workbench candidate snapshot、load-more、POS projection 及排序不變。
- 純漢字 lookup 與生成詞條完整回歸。

既有先例：

- Shared contract JSON parity tests。
- Golden query／golden explain corpus。
- Position-match engine self-check。
- Workbench plan-spec parity、planner、snapshot 及 candidate-session tests。
- Browser `?benchmark`、`?perf=1` marks 及 DB benchmark。
- Python mask／startup benchmark 與 benchmark enforcement。

效能測試要求：

- 實作前後使用同一 lexicon、裝置、browser、backend、query corpus 及 run count。
- 冷查與暖查分開；先 warm up 再計中位數與 p95。
- Compiler timing 與完整 engine timing分開。
- OPFS VFS、sql.js fallback、Python 及實機手機 PWA 都要有結果。
- 不因單次抖動失敗；只有可重現的約 10% 以上退步才阻擋完成。

## Out of Scope

- 改查詢語法、hint 文案、結果排序政策或 UI。
- 改純漢字 lookup、生成詞條或 compact entry layout。
- 新增 SQL index、改 OPFS 儲存格式或替換 sql.js。
- 工作台 session、undo、selection reducer、candidate snapshot identity 或 POS
  filter 架構；這些屬 Candidate 04 或其他候選。
- 通用 query IR 重寫或通用 boolean constraint language。
- 全域 MatchSpec／physical plan cache。
- Candidate 02、04、05 的 implementation。
- 本計劃階段建立 PR、release 或部署；後續實作可建立 GitHub tracking issue。

## Handoff

Luna 實作時：

1. 保持在 `dev`，先同步 `origin/dev`，確認沒有不相關 working-tree 變更。
2. 可先由本 MD 建立 GitHub tracking issue，issue 可保存完整計劃；對話只
   回報 issue 連結、狀態與短摘要，不重貼全文。
3. 先保存 baseline tests 與 benchmark，再按 Phase／Commit 次序工作。
4. 每個提交只完成一個可驗證步驟；如發現語意 bug，插入獨立 regression
   commit，不與搬遷混合。
5. 每個提交後跑最小相關驗證；每個 Phase 結束跑雙端 shared parity。
6. 不建立 production feature flag，不保留已切換 caller 的 runtime fallback。
7. 遇到文件未定義且 Python／TypeScript 行為不同時停止裁決，記錄案例並交回
   Sol grilling；不要自行選一端成為標準。
8. 所有文字檔保持 LF；不要無意識修改 `skills-lock.json`。
9. 完成後 commit 並 push 到 `origin/dev`。
10. 回報提交清單、完整測試結果、before／after benchmark、未完成項及任何偏離
   計劃之處。
11. 不建立 PR 到 `main`；待 Sol review 後再由使用者確認下一步。
