# macOS Intel 維護者速查（發佈補件）

本機路徑（Macintosh HD）：`~/Projects/Canto-0243`  
上游：`https://github.com/bill-iu/Canto-0243`  
角色：**發佈補件** — 只建置／上傳 macOS **Desktop** tar（PyApp）；Release 由 Windows 發佈主理先建立。

完整流程見 [release.md](release.md)。運送形態見 [ADR-0068](adr/0068-desktop-pyapp-delivery.md)。

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

# 3. Rust（PyApp + desktop-shell）
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"
cargo --version

# 4. 系統／建置 Python（wheel + slim scripts）
# 可選：.build-python 經 fetch-macos-build-python.sh（3.12 standalone）
python3 -m pip install --user build wheel setuptools sqlalchemy python-dotenv

# 5. Node（client dist-portable）
# 需要 npm；首次建置會 npm ci
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
git checkout v1.1.0          # 換成目標 tag
source "$HOME/.cargo/env"   # 若新開 shell

bash scripts/macos-tar.sh --tag v1.1.0
```

產物：`dist/canto-0243-desktop-macos-x86_64.tar.gz`

本機試跑（唔上傳；**首次可需網**）：

```bash
bash scripts/macos-tar.sh --tag v1.1.0 --test
```

---

## 打包並上傳 Release（發佈補件）

**前置**：GitHub 上該 tag 的 Release 已存在（主理已放 Desktop zip + 詞庫）。

```bash
cd ~/Projects/Canto-0243
git fetch origin --tags
git checkout v1.1.0
source "$HOME/.cargo/env"

bash scripts/macos-tar.sh --tag v1.1.0 --upload
```

腳本會：從 Release 下載 `lyrics.db` → `npm run build:portable`（若缺）→ fetch rime（若缺）→ `build-desktop.sh`（PyApp）→ 上傳 **Desktop tar** + manifest；若仍有舊名 `canto-0243-portable-macos-*.tar.gz` 會刪除。

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
git checkout v1.1.0
bash scripts/macos-tar.sh --tag v1.1.0 --upload
git switch main
```

---
