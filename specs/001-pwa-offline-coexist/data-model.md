# Data Model: PWA Offline Coexist

**Date**: 2026-07-02  
**Spec**: [spec.md](./spec.md)

此功能以「離線交付」為核心，因此資料模型以「版本化詞庫資料包」與「離線就緒狀態」為主；不引入使用者帳號或雲端資料。

## Entities

### Entity: Versioned Lexicon Package

**Represents**: 某個 release 版本對應的離線詞庫資料包。  
**Key attributes**:
- **Release version**: semver（例如 `v1.0.3`）
- **Package identity**: 可由唯一識別取得對應資料包（例如版本化的資產路徑/檔名）
- **Integrity state**: 是否可被當作「離線可用」的完整資料包（可由「是否可成功完成查詢」作為驗證標準）

**Relationships**:
- 與「離線就緒狀態」一對多：一台裝置可存在多個版本的離線資料包（例如舊版仍可用，新版待下載）

### Entity: Offline Readiness State

**Represents**: 裝置端是否具備完整離線運作所需資源（包含詞庫資料包）。  
**States**:
- **Not Ready**: 尚未完成離線就緒（可能首次開啟、或 cache 被清除）
- **In Progress**: 正在準備離線就緒（下載/緩存中）
- **Ready**: 已完成離線就緒，可在完全離線狀態下查詢
- **Failed**: 離線就緒失敗（例如儲存空間不足/下載中斷）

**State transitions**:
- Not Ready → In Progress → Ready
- Not Ready → In Progress → Failed
- Ready → Not Ready（系統清除/使用者清除網站資料等外部因素）

## Validation Rules (feature-level)

- 若「離線就緒狀態」不是 Ready，系統不得誤導使用者為已可離線查詢（可仍允許線上操作，但需清楚標示）
- Release version 必須可與 portable 對齊（同一版號代表同一套詞庫資料）

