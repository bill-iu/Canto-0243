# 詞庫勘誤（維護者）

領域詞彙見 [CONTEXT.md](../CONTEXT.md) § **詞庫勘誤**。與 **關係補錄**（近義／反義）無關。

## 檔案

`data/lexicon/lexicon_corrections.tsv`（tab 分隔，git 追蹤）

| 欄 | 說明 |
|----|------|
| `char` | 字面 |
| `code` | **現有**詞條 0243 碼（鎖定列） |
| `jyutping` | **現有**粵拼（與 code 一齊唯一鎖定） |
| `action` | `set_jyutping`、`set_code` 或 `delete` |
| `value` | `set_jyutping`：新 jyutping（連帶重算 code／聲韻）；`set_code`：新 0243 碼（長度須等於字面音節數，唔改 jyutping） |
| `note` | 發現原因、參考 |
| `status` | `pending` 或 `applied` |
| `applied_at` | 套用日（`YYYY-MM-DD`） |

## 流程

1. 使用過程發現錯字 → 加一行 `status=pending`。
2. 檢查累積：`python -m ingest apply-lexicon-corrections --check`（**≥20** 筆 pending 會提示可套用）。
3. 套用：`python -m ingest apply-lexicon-corrections --apply`  
   - 改 `lyrics.db`  
   - export `dist/words-lexicon.json`  
   - sync README 詞條數  
   - TSV 內已套用列改為 `applied`
4. **手動** `git commit` TSV（及 README 若有變）。
5. 夠批後 **詞庫發佈**（`docs/release.md` § 步驟 3）：覆寫現有 semver 的 `lyrics.db`／json，唔為每批勘誤開新 portable hotfix。

## 範例

```tsv
char	code	jyutping	action	value	note	status	applied_at
某字	2	wrong6	set_jyutping	right6	填詞時發現	pending	
```

刪錯列：`action=delete`，`value` 留空。

只改碼（粵拼已啱）：

```tsv
你	9	nei5	set_code	4	code 與 jyutping 唔一致	pending	
```
