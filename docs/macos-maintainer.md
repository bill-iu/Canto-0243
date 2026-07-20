# macOS Intel 維護者速查（發佈補件）

本機路徑（Macintosh HD）：`~/Projects/Canto-0243`  
上游：`https://github.com/bill-iu/Canto-0243`  
角色：**發佈補件** — 只建置／上傳 macOS tar；Release 由 Windows 發佈主理先建立。

完整流程見 [release.md](release.md)。

---

## 首次設定（做一次）

```bash
# 1. Clone（若已有資料夾可略過）
mkdir -p ~/Projects
git clone https://github.com/bill-iu/Canto-0243.git ~/Projects/Canto-0243
cd ~/Projects/Canto-0243

# 2. GitHub CLI 登入（upload 需要）
gh auth login
gh auth status

# 3. 系統 Python（export_words_lexicon 尾段用，建置腳本會呼叫）
python3 -m pip install --user sqlalchemy python-dotenv

# 4. 建置用 CPython 3.12（首次建置時 macos-tar.sh 會自動下載到 .build-python/）
```

---

## 日常：拉最新 main

```bash
cd ~/Projects/Canto-0243
git switch main
git pull
```

---

## 一鍵本地打包 tar（唔上傳）

**前置**：已 `git checkout` 到要建置的 tag，且 `HEAD` 對齊該 tag。

```bash
cd ~/Projects/Canto-0243
git fetch origin --tags
git checkout v1.0.3          # 換成目標 tag

bash scripts/macos-tar.sh --tag v1.0.3
```

產物：`dist/canto-0243-portable-macos-x86_64.tar.gz`

本機試跑（唔上傳）：

```bash
bash scripts/macos-tar.sh --tag v1.0.3 --test
```

---

## 打包並上傳 Release（發佈補件）

**前置**：GitHub 上該 tag 的 Release 已存在（主理已放 zip + 詞庫）。

```bash
cd ~/Projects/Canto-0243
git fetch origin --tags
git checkout v1.0.3

bash scripts/macos-tar.sh --tag v1.0.3 --upload
```

腳本會：**一律從 Release 下載 `lyrics.db`**（覆寫本機 stale copy）→ 建置 → 只上傳 tar（`--clobber` 覆蓋）。

**唔好**依賴 repo 根目錄舊 `lyrics.db`；補 tar 時 Release 資產才是 SSOT。

完成後回到 main：

```bash
git switch main
```

---

## 刷新同一 tag 的 tar（打包修正、語意不變）

主理已 `git tag -f` 並 push 後：

```bash
cd ~/Projects/Canto-0243
git fetch origin --tags
git checkout v1.0.3
bash scripts/macos-tar.sh --tag v1.0.3 --upload
git switch main
```

---

## 改程式後 commit + push（例子）

```bash
cd ~/Projects/Canto-0243
git switch main
git pull

# …改檔…

git status
git add scripts/portable_venv.py    # 或 git add -p
git commit -m "fix(portable): 簡述原因"
git push origin main
```

---

## 新 tag 由主理建立後，補件建 tar

```bash
cd ~/Projects/Canto-0243
git fetch origin --tags
git checkout v1.0.4               # 主理已 push tag + Publish Release
bash scripts/macos-tar.sh --tag v1.0.4 --upload
git switch main
```

---

## 常見檢查

```bash
# 目前 commit 是否等於 tag？
git rev-parse HEAD
git rev-parse v1.0.3^{commit}

# Release 有咩資產？
gh release view v1.0.3 -R bill-iu/Canto-0243

# 建置 Python 在嗎？
test -x .build-python/python/bin/python3.12 && echo OK

# 詞庫是否對齊 Release？（補 tar 前建議）
mkdir -p /tmp/canto-check
gh release download v1.0.3 -R bill-iu/Canto-0243 -p lyrics.db -D /tmp/canto-check
python3 -c "import sqlite3; print('release', sqlite3.connect('/tmp/canto-check/lyrics.db').execute('select count(*) from words').fetchone()[0])"
```

---

## 手動等同指令（唔用包裝腳本時）

```bash
cd ~/Projects/Canto-0243
export GH_REPO=bill-iu/Canto-0243
export PORTABLE_BUILD_PYTHON="$PWD/.build-python/python/bin/python3.12"
bash scripts/release-macos-local.sh --tag v1.0.3 --arch x86_64 --upload
```

---

## 創作者下載後（俾朋友）

1. 重新下載最新 tar（舊包可能缺修復）
2. 解壓 → 雙擊 `Canto-0243.command`
3. Gatekeeper 只應彈**一次**（針對 `.command`）；若仍逐檔彈 python／`.so`，請回報並確認 tar 日期

臨時修舊包（Terminal）：

```bash
cd ~/Downloads/canto-0243-portable
xattr -cr .
export PYTHONHOME="$PWD/venv"
sed -i '' "s|^home = .*|home = $PWD/venv/bin|" venv/pyvenv.cfg
open Canto-0243.command
```
