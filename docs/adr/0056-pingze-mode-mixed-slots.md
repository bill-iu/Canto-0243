# ADR-0056：獨立平仄模式及混合碼位

日期：2026-07-10

## 決定

平仄搜尋使用獨立 `pingze` 模式及 `m1`、`m2`、`m3` sub-mode，不再從一般輸入自動辨識或轉換 `P`／`Z`。平仄模式的 `P`／`Z` 成為逐位 MatchSpec constraint：`P` 對應 394052 的 `0`／`3`，`Z` 對應其他碼位；數字 slot 則按所選 sub-mode 的既有等價規則比對。

平仄 slot 與既有通配、韻錨和字面錨組合，沿用同一條 MatchSpec、排序、去重及分頁路徑。平仄模式不支援粵拼錨，並提供模式切換提示。

## 後果

- 一般模式的 `p`、`z` 聲母和粵拼片段不再被平仄 classifier 攔截。
- `mode=pz&pzmode=m1|m2|m3` 必須隨 URL、歷史和 tab frame 保存；沒有 `pzmode` 的平仄 URL 預設使用 `m1`。
- Python 服務端與 TypeScript PWA port 必須維持同一個 mode-aware parser、tone-class constraint 和測試契約。
- 舊有全域平仄串列 redirect 移除；ADR-0031 關於 394052 canonical code 的歷史決定不變。
