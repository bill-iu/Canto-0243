# China-idiom 成語 POS 補標 Implementation Plan

**Goal:** 為 4,147 筆已審 `lexicon-pos-gap` 成語建立專案 POS，清除 family leaf deferred 缺口。

**Architecture:** 新的離線工具核對 China-idiom commit/hash，從 family review 精確取母體，輸出 POS review 與 hash-locked quality ledger；品質通過後只新增缺失 SSOT 列。正常 runtime、build 與 dependencies 不讀外源。

**Spec:** [`docs/superpowers/specs/2026-07-19-chengyu-pos-backfill-design.md`](../specs/2026-07-19-chengyu-pos-backfill-design.md)

## Task 1：來源與母體 fail closed

- [x] 測試精確選取 4,147 筆 `lexicon-pos-gap` accept/chengyu。
- [x] 核對 source commit 與 CSV SHA-256 sidecar。
- [x] 缺欄、缺記錄、母體漂移或重複字面拒絕寫入。

## Task 2：保守 POS／voice 審核

- [x] 以句法槽、語義頭、固定結構建立候選。
- [x] 多詞性只收分別有證據的常見用法。
- [x] 移除「形容」關鍵詞、`得～`、一般動作詞等過寬規則。
- [x] 對正式候選全量異常掃描，以逐筆 override 修正系統性例外。
- [x] voice 預設空；14 個被動候選逐筆收斂為 4 個固定受事義。
- [x] 證據不足列終局 `u`，不以 `x` 或推測值湊覆蓋。

## Task 3：品質帳與寫入閘

- [x] review 閉集驗證 family、POS、voice、confidence、verdict 與 evidence。
- [x] 全量覆核 `u`／`passive`／`x`／罕見多詞性 strata，其餘固定 seed 分層抽樣。
- [x] quality meta 鎖定 review SHA-256；未過 `>90%` 或 hash 漂移不得 apply。
- [x] apply 對既有同值冪等跳過，既有不同值 fail closed。

## Task 4：實際套用與驗證

- [x] 產生 4,147 筆終局 review：208 正式 POS、3,939 `u`、4 `passive`。
- [x] 品質帳 sample 3,967：3,964 OK、3 SOFT、0 BAD。
- [x] dry-run 恰有 4,147 additions，正式 apply 後重跑 changed=0。
- [x] `deferred_missing_project_pos` 降為 0，carrier/meta version 升至 `0.6.0`。
- [x] 執行完整 POS/client 回歸與 dependency 檢查。
- [x] commit 並 push `dev`。
