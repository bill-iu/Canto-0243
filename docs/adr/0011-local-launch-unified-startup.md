# 本機啟動統一編排

領域詞彙：見 [CONTEXT.md](../../CONTEXT.md) § 本機啟動、就緒閘、離線啟動預載。延續 [ADR-0006](0006-portable-zero-install-delivery.md)。

創作者雙擊 `START.bat`／`start.sh` 後數秒無可見回饋，易以為啟動失敗；`start.sh` 與 Portable 啟動腳本行為分叉（等 `/` vs `/frontend/index.html`、`run_main_block_startup` 與 lifespan 重複 bootstrap）。我們決定：

1. **`scripts/local_launch.py`** 為唯一啟動編排：立刻終端回饋 → free_port → 背景 `main.py` → 等 HTML 200 → 開瀏覽器 → 背景 `--gate`（不等 gate 才開瀏覽器）。
2. **四入口委派**：`start.sh`、`portable/START.bat`、`portable/START.sh`、`portable/macos/launcher`。
3. **刪 `run_main_block_startup()`** — lifespan 單次 `create_all` + `bootstrap_local_db()`，背景 word_cache／static／compound_syn 不變。
4. **Dev pip stamp** — `start.sh` 僅 `requirements.txt` hash 變更時 pip；Portable 永不 pip。
5. **驗收** — seam 測試 + 維護者手跑 `scripts/bench_startup.py`（不進 CI）。

**Considered Options**

- 各腳本 inline 對齊 — 已證明會再分叉。
- 先開瀏覽器再等 HTTP — 違反 CONTEXT「不得無法連線」。
- yield 前零 bootstrap — schema race 風險過高。

**Consequences**

- Portable build 須複製 `local_launch.py`（`portable_venv` RUNTIME_SCRIPTS）。
- 維護者以 `./start.sh` + bench 驗 Portable 體感（ADR-0006 §5）。
- 架構檢視 #C → #B → #E 排在本功能之後。
