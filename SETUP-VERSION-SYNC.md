## 版本同步功能設置完成 ✓

已成功添加 README 版本同步功能。以下是完整的設置說明：

### ✓ 已完成的部分

1. **README 更新** ✓
   - 在所有三個 README 中添加了「目前版本」行：
     - `README.md` (繁體中文)
     - `docs/README.zh-Hans.md` (簡體中文)
     - `docs/README.en.md` (English)
   - 當前版本：`v1.0.5`

2. **Python 脚本** ✓
   - 創建了 `scripts/sync-version.py`
   - 可以自動從 GitHub API 獲取最新版本號
   - 支持 `--dry`、`--check` 標誌

3. **文檔** ✓
   - 創建了 `docs/version-sync.md`
   - 詳細使用說明

4. **PR 已提交** ✓
   - PR #42：dev → main

### ⏳ 需要手動完成的部分

**GitHub Actions Workflow 文件**

由於 OAuth 權限限制，workflow 文件無法透過當前的認證方式推送。您有兩種選擇：

#### 選項 A：透過 GitHub Web UI 創建（推薦）

1. 訪問：https://github.com/bill-iu/Canto-0243/new/dev?filename=.github%2Fworkflows%2Fsync-version.yml

2. 將以下內容複製到編輯器：

```yaml
name: Sync Version to README

on:
  release:
    types: [published, created]
  workflow_dispatch:

jobs:
  sync-version:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          ref: ${{ github.ref }}

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Sync version
        run: python scripts/sync-version.py

      - name: Check if files changed
        id: verify
        run: |
          if git diff --quiet; then
            echo "changed=false" >> $GITHUB_OUTPUT
          else
            echo "changed=true" >> $GITHUB_OUTPUT
          fi

      - name: Commit and push if changed
        if: steps.verify.outputs.changed == 'true'
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add README.md docs/README.*.md
          git commit -m "chore: Sync version to latest release"
          git push
```

3. 點擊「Commit changes」，選擇 commit 到 `dev` 分支

4. 該文件會自動包含在後續的 PR 中

#### 選項 B：本地推送 (需要特殊權限)

```bash
# 如果您有合適的 GitHub 權限，可以直接推送
git add .github/workflows/sync-version.yml
git commit -m "feat: Add GitHub Actions workflow for version sync"
git push origin dev
```

### 立即使用 Python 脚本

無需等待 workflow，您現在就可以手動同步版本：

```bash
# 同步版本號
python scripts/sync-version.py

# 預覽修改（不實際更新）
python scripts/sync-version.py --dry

# 檢查是否需要更新
python scripts/sync-version.py --check
```

### 下次 Release 時

一旦 workflow 文件創建：

1. 在 GitHub 發佈新 Release（例如 v1.0.6）
2. 靜候 1-2 分鐘，GitHub Actions 會自動執行
3. README 版本號會自動更新
4. 檢查 Actions 執行結果

### 相關文件

- 脚本：`scripts/sync-version.py`
- 文檔：`docs/version-sync.md`
- PR #42：dev → main
- PR #41：fix/readme-cleanup → main (已合併)
