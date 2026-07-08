# 版本同步指南

本專案提供自動同步 README 中版本號與 GitHub Release 最新版本的解決方案。

## 自動化方式 (推薦)

### GitHub Actions

- **觸發時機**：當發佈新 Release 時自動執行
- **工作流文件**：`.github/workflows/sync-version.yml`
- **功能**：自動檢查版本號，更新三個 README 檔案，並提交/推送變更

**手動觸發**（若需要）：
```bash
gh workflow run sync-version.yml
```

## 手動同步方式

### 使用 Python 腳本

```bash
# 自動同步版本號
python scripts/sync-version.py

# 預覽修改（不實際更新）
python scripts/sync-version.py --dry

# 檢查是否需要更新（退出碼：0=已最新, 1=需更新）
python scripts/sync-version.py --check
```

**需求**：Python 3.7+（內建函式庫，無額外依賴）

### 使用 Shell 命令（快速）

```bash
# 一行命令同步
python scripts/sync-version.py
```

## 工作原理

1. **API 查詢**：呼叫 GitHub API 取得 `bill-iu/Canto-0243` 最新 Release 版本號
2. **檔案掃描**：檢查三個 README 中的版本注釋標記
   - `README.md` - 繁體中文
   - `docs/README.zh-Hans.md` - 簡體中文
   - `docs/README.en.md` - English
3. **版本更新**：若檢測到差異，自動更新版本號
4. **輸出報告**：顯示當前版本、最新版本、修改狀態

## 版本標記格式

README 中使用 HTML 注釋標記來標識版本欄位：

```markdown
<!-- version:zh-Hant -->
目前版本：**v1.0.6**
<!-- /version:zh-Hant -->
```

**脚本只會修改這些標記之間的版本號，其他内容保持不變。**

## 注意事項

- GitHub API 無需認證即可使用（有速率限制）
- 腳本會自動檢測版本號格式（v1.0.5 或 1.0.5）
- 若為離線環境，請手動編輯 README 或提供 GitHub Token

## 故障排除

| 問題 | 解決方案 |
|------|---------|
| `無法連接 GitHub API` | 檢查網路連線，或稍後重試 |
| `無法找到版本號` | 確保 Release 存在，檢查 `.github/workflows/sync-version.yml` |
| `修改了但沒推送` | 檢查 Git 權限和分支設置 |

## 下次 Release 時

1. 在 GitHub 發佈新 Release（例如 v1.0.6）
2. 靜候 1-2 分鐘，GitHub Actions 會自動執行
3. README 中的版本號會自動更新到 v1.0.6
4. 檢查 Actions 執行結果（綠色 ✓ 表示成功）
