# 詞庫勘誤（維護者）

領域詞彙見 [CONTEXT.md](../CONTEXT.md) § **詞庫勘誤**。與 **關係補錄**（近義／反義）無關。

## 檔案

`data/lexicon/lexicon_corrections.tsv`（tab 分隔，git 追蹤）

| 欄 | 說明 |
|----|------|
| `char` | 字面 |
| `old_jyutping` | **現有**粵拼（與字面一齊鎖定目標讀音） |
| `old_code` | **現有** 0243 碼（可選；`set_code` **必填**） |
| `action` | `set_jyutping`、`set_code` 或 `delete` |
| `value` | `set_jyutping`：新 jyutping（連帶重算 code／聲韻）；`set_code`：新 0243 碼（長度須等於字面音節數，唔改 jyutping） |
| `note` | 發現原因、參考 |

**唔**含 `status`／`applied_at`：每次 `build-db` 詞條從源重建時**必**套用 overlay，唔以狀態機決定是否生效。

## 流程

1. 使用過程發現錯字 → 加一行（Web UI `/lexicon/corrections` 或手改 TSV）。
2. 檢查累積：`python -m ingest apply-lexicon-corrections --check`。
3. **建議**：全量重建 `python -m ingest build-db`（truncate → ingest → overlay → relations…）。
4. **可選** hotfix 現有庫：`python -m ingest apply-lexicon-corrections --apply`（直接改 `lyrics.db` + export）。
5. **手動** `git commit` TSV（及 README 若有變）。

## 範例

```tsv
char	old_jyutping	old_code	action	value	note
某字	wrong6	2	set_jyutping	right6	填詞時發現
```

刪錯列：`action=delete`，`value` 留空。

只改碼（粵拼已啱）：

```tsv
不斷	but1 dyun6	34	set_code	32	編碼混入 tyun5
```
