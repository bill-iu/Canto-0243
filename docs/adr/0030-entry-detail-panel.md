# 詞條詳情面板（搜尋清單精簡 + 右側詳情）

0243搜尋模式嘅扁平結果清單改為**只顯示字面**；點擊後喺右側（z 軸上層）開啟**詞條詳情**面板，顯示粵拼、0243／02493 碼、音韻結構、詞頻、收錄來源、近反義等。近反義模式 chip 版面不變。

**點擊狀態機**（同一詞條 = 字面 α）：面板關閉時點清單 → 開面板並以該字面提交搜尋；面板開啟且同一字面 → 只聚焦面板；面板開啟且不同字面或點面板外 → 只關閉面板、該次 click 不觸發搜尋（避免誤觸）；詳情內近反義 chip 豁免，直接開新詞詳情並搜尋。重新搜尋後面板保持開啟，內容切換為新字面，被點擊讀音預選為「讀音1」。

**雙端共享**：業務邏輯放 `frontend/entry-detail-core.mjs`；PWA（React）與 Portable（vanilla DOM）各自渲染；樣式共用 `frontend/entry-detail.css`。DB 查詢留各端資料層，core 只收 plain object。首版 i18n 繁中 + `entry-detail-i18n.mjs` 架構，英文獨立 PR。

**Considered:** 頂部下推式窄屏面板、Web Component 共用 DOM、prep-only PR 先 land core——均因偏離現有 `frontend/*.mjs` 慣例或增加整合成本而拒絕。平仄／矩陣首版不顯示，extension point 留待後續 issue。