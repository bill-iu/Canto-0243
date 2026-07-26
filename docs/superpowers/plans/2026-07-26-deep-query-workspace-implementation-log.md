# Candidate 02：Deep Query Workspace 實作紀錄

日期：2026-07-26
分支：`dev`
追蹤 issue：[#146](https://github.com/bill-iu/Canto-0243/issues/146)

## 已完成切片

- R1–R4：characterization、pending/ready/error race matrix、效能基線。
- R5–R9：Query Workspace 接管 visible results、total、POS filter、shuffle、auto-fill、checkpoint 與 ready/error transitions。
- R10–R12：Navigation Adapter commit/checkpoint seam；App 不再以 `saveLeavingSearchTab` 鏡像結果。
- R13–R14：Entry Detail Adapter 與可取消的 per-tab detail lifecycle。
- R15–R18：controls/results/detail view model、結果 render boundary、App 移除 reducer state 直出。
- R19：checkpoint 以 workspace 的可見 rows/offset 為唯一 durable projection。
- R20：搜尋 loading/error/count 與 entry-detail relation loading 加入 live-region/busy 語意。
- R21：`?perf=1` 增加 shell/workspace/results/detail/list render counters；無 `?perf=1` 時維持 no-op。

## 主要模組

- `client/src/query-workspace/useQueryWorkspace.ts`
- `client/src/query-workspace/useQueryWorkspaceDetail.ts`
- `client/src/query-workspace/detail-adapter.ts`
- `client/src/query-workspace/navigation-adapter.ts`
- `client/src/query-workspace/QueryWorkspaceResultsBoundary.tsx`
- `client/src/search-perf.ts`

## 驗證

每個 implementation slice 均 commit/push 到 `origin/dev`。目前驗證包含：

```text
npx tsc -p client/tsconfig.app.json --noEmit
npm run self-check:ci -- --id query-workspace-state --id query-workspace-detail --id query-workspace-characterization --id query-workspace-adapter --id query-workspace-navigation --id search-perf
node --test tests/query_tabs_state_test.mjs tests/search_navigation_test.mjs
npm run build
```

最後一次結果：query-workspace 5/5、search-perf 1/1、Node tests 37/37，Vite build 與 Pages artifact guardrail 通過。

## 尚未宣稱的事項

- 尚未量測真實手機／瀏覽器 p95，因此不宣稱固定百分比效能提升；`?perf=1` 只提供下一輪同環境比較的 counters/marks。
- #146 保持 open，待 `dev` 經 PR merge 到 `main` 並完成 cross-host/browser acceptance 後才關閉。
