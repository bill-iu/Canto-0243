# Contract: Versioned Lexicon Package

**Scope**: portable 與 PWA 共用之「詞庫資料包」版本契約（非實作細節）  
**Spec**: [../spec.md](../spec.md)

## Purpose

確保：
- PWA 與 portable 在同一個 release 版本號下使用相同版本的詞庫資料包
- PWA 的資料更新只在 release 發生

## Contract

### Version source of truth

- 詞庫資料包版本必須以 **release semver tag** 表達（例如 `v1.0.3`）

### Unique identity per version

- 每個 release 版本必須能以「唯一識別」取得對應資料包
- 若使用者已緩存舊版，系統仍可繼續使用舊版；新版取得不應破壞舊版可用性

### Compatibility expectation

- 同一個 release 版本號下，portable 與 PWA 對相同查詢輸入應呈現等價結果（以使用者觀察為準）

