# POS 語彙族細分與三軸篩選 Implementation Plan

**Goal:** 擴充語彙族葉值，使用 China-idiom 作離線成語提案來源，並在搜尋與句格工作台提供高信任三軸篩選。

**Architecture:** `project_pos.tsv` 繼續是單一 SSOT；carrier 輸出高信任展示三軸。純 TypeScript matcher 組合各軸 OR／跨軸 AND，搜尋與工作台共用。China-idiom importer 只接受外部 CSV 路徑並產生 proposal／來源 sidecar，正常 build、test、runtime 不讀外源。

**Spec:** [`docs/superpowers/specs/2026-07-19-pos-family-leaf-subtypes-design.md`](../specs/2026-07-19-pos-family-leaf-subtypes-design.md)

---

## Task 1：同步領域契約與載體

**Files:** `CONTEXT.md`、`docs/adr/0061-pos-family-leaf-subtypes.md`、`ingest/project_pos.py`、`client/src/pos/types.ts`、`client/src/pos/carrier.ts`、`tests/smoke/test_project_pos.py`、`client/scripts/pos-meta-self-check.ts`

- [ ] 先加 parser／carrier／chip 葉值測試。
- [ ] family 閉集加入 `chengyu|suyu|yanyu`，更新四個中文標籤。
- [ ] 保證 carrier 只輸出 high family／voice／show；`same_pos` 仍只看 gate POS。
- [ ] 把 domain docs 的產品篩選由語彙族單選更新成三軸 filter，保留單值 SSOT 與傘葉語意。
- [ ] 執行 Python POS smoke 及 TS POS self-check。

## Task 2：建立純三軸 filter contract

**Files:** create `client/src/pos/filter.ts`、create `client/scripts/pos-filter-self-check.ts`

- [ ] 先寫軸內 OR、軸間 AND、全空、缺標、high-only、傘葉與主被動 cases。
- [ ] 定義 JSON-safe `PosFilterState`，三軸各為去重陣列。
- [ ] 實作 normalize／toggle／reset／active count／entry match／literal match／result match。
- [ ] `idiom` 與葉值互斥正規化；葉與葉可多選。
- [ ] 確認 helper 不調用 gate POS，campaign contract 不受影響。

## Task 3：China-idiom 離線提案與審核帳

**Files:** create `ingest/project_pos_family_leaf.py`、create `tests/smoke/test_project_pos_family_leaf.py`、create `data/pos/family_leaf_mother_body.txt`、create `data/pos/proposals/family_leaf_proposals.tsv`、create `data/pos/proposals/family_leaf_source.meta.json`

- [x] fixture 覆蓋 header 驗證、繁化、去重、詞庫交集、母體命中／未命中、family 漏標、project POS gap 與 hash sidecar。
- [x] 統一 scope 納入完整 lexicon 的 China-idiom 命中；非母體項只進 audit，不直接寫 SSOT。
- [ ] `freeze` 只收當刻 `family=idiom`，排序穩定且不覆蓋既有 freeze。
- [ ] `propose` 接受 `--china-idiom-csv` 與 `--source-commit`；只產 `chengyu` pending。
- [ ] `status` 分開 pending、accept、keep_idiom、reject 與三葉數。
- [ ] `apply` fail closed、只改 family、保持其他軸、重跑冪等。
- [ ] clone 外源到 repo 外暫存目錄，記錄 commit/hash；不修改 dependencies／lockfile，不 vendor CSV。

## Task 4：實際細分批次與品質帳

**Files:** `data/pos/proposals/family_leaf_proposals.tsv`、create `data/pos/audit/family_leaf_review.tsv`、create `data/pos/audit/family_leaf_quality_r1.tsv`、create `data/pos/audit/family_leaf_quality_report.md`、`data/pos/project_pos.tsv`、`data/pos/project_pos.meta.json`

- [ ] 先審 China-idiom 命中的高信心成語，錯誤／跨界不直接寫 SSOT。
- [ ] 依 CONTEXT 優先序補明顯粵語俗語、書面諺語；分不清明確 `keep_idiom`。
- [ ] apply 過審帳並 bump carrier version。
- [ ] 固定 seed 抽樣終局列，`OK+SOFT >90%`；未過則修正再抽。
- [ ] 重建 `client/public/project-pos-index.json`，核對來源 CSV 未進 git。

## Task 5：搜尋三軸 filter UX 與分頁

**Files:** create `client/src/pos/PosFilterControl.tsx`、modify `client/src/App.tsx`、`client/src/pwa-app.css`、query tab state files、create `client/scripts/pos-filter-ui-self-check.ts`

- [ ] 先測 filter state tab round-trip、結果 layout filter、badge、reset 與 umbrella normalization。
- [ ] 搜尋列旁加漏斗；desktop popover、mobile bottom sheet；三組 chips 即時生效。
- [ ] 選取狀態用 `aria-pressed`、文字與填色；支援 Escape、outside click、close、reset。
- [ ] filter state 跟 tab，不進 URL；未載 carrier 時 disabled。
- [ ] 普通／近反義／錨結果一律按 literal 過濾；外部缺載體項在 active filter 下排除。
- [ ] active filter 首批不足 render batch 時串行續取至填滿或 raw exhausted；結果數不冒充未知全域 total。
- [ ] shuffle 只作用於符合結果，filter 改變重設 render window。

## Task 6：工作台三軸 filter

**Files:** `client/src/workbench/useWorkbenchCandidates.ts`、`client/src/workbench/WorkbenchPage.tsx`、`client/src/workbench/workbench-page.css`、`client/scripts/pos-meta-self-check.ts`

- [ ] 在既有同詞類 seed filter 後套用 creator filter，三候選組一致。
- [ ] 重用 filter control／state，工作台 session 獨立於搜尋 tabs。
- [ ] 放寬後 exact 結果仍受硬 filter；active filter 下不顯示未過濾的 relaxation count。
- [ ] 零結果不清除條件；缺 carrier 時工作台仍可用。

## Task 7：完整驗證與交付

- [ ] `python tests/smoke/test_project_pos.py`
- [ ] `python tests/smoke/test_project_pos_family_leaf.py`
- [ ] `npx tsx scripts/pos-meta-self-check.ts`
- [ ] `npx tsx scripts/pos-filter-self-check.ts`
- [ ] 相關 query tab／workbench self-check。
- [ ] `npx tsc -b`、`npm run lint`、`npm run build`。
- [ ] `git diff --check`，確認 dependency／lockfile／完整外源 CSV 無變更。
- [ ] 依功能批次 commit，最終 push `dev`；未經用戶確認不開 `dev -> main` PR。
