# Canto-0243

<p align="center">
  <a href="../README.md">繁體中文</a> · <b>简体中文</b> · <a href="README.en.md">English</a>
</p>

填写粤语歌词时，常见困难一是不知道有哪些字可用，二是需要在**同音、押韵、近义**之间快速换字，同时又要符合 0243 与粤拼读音。传统做法是在词典、韵书、近义表之间反复查阅，手动尝试「这一位置能否换成另一个字」——效率低，且容易遗漏许多可用字。[0243.hk](https://0243.hk) 已是近年来较好用的粤语填词检索网站，但偶尔会出现 502 Bad Gateway 无法访问；检索时也可能长时间加载；或缺少所需功能——这些情况都会拖慢创作进度。

**Canto-0243**（**ONE·揾·韵**）是在 Cursor、Codex、Grok Build、GitHub Copilot 等多种 AI Agent 协助下开发的离线粤语填词检索工作台：依据 **0243／02493 数字码**、**粤拼**、**韵母／声母规则**与 **近义／反义关系**，在数秒内列出符合条件的**词条**。例如输入 `23就` 可查找同调且与「就」押韵的尾字；输入 `香港=` 可查找与「香港」押韵的候选词；输入 `~开心` 或切换**近反义模式**可查找近义／反义词；输入 `~~`／`!!` 可查找填词常用的二字近义／反义复合词。套件解压即可使用，词库与近反义资料均存于本地，无需联网。

**授权**：程序依 [Canto-0243 License](../LICENSE)（CC BY-NC-SA 4.0 + 附加条款；**非 OSI 开源**）。**词条库** `lyrics.db` 与同版 `words-lexicon.json` 依 [`LYRICS_DB_LICENSE.md`](../LYRICS_DB_LICENSE.md)（CC BY-SA 3.0 混合）。第三方资料见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。  
**技术栈**：FastAPI · SQLAlchemy · SQLite（离线单机）· 纯 HTML/JS 前端  
**领域词汇**：见 [`CONTEXT.md`](../CONTEXT.md) · 贡献指南 [`CONTRIBUTING.md`](CONTRIBUTING.md)

---

## 最新版本

<!-- words-count:zh-Hans -->
目前总词条列数：**193,294**（`lyrics.db` · `words` 表）
<!-- /words-count:zh-Hans -->

官方离线资料包：**[Canto-0243 v1.0.3](https://github.com/bill-iu/Canto-0243/releases/tag/v1.0.3)**（`canto-0243-portable.zip`、`canto-0243-portable-macos-x86_64.tar.gz`、`lyrics.db`、`words-lexicon.json`、`LYRICS_DB_LICENSE.md`；Apple Silicon arm64 过渡期暂不提供）。问题与建议欢迎提交 [GitHub Issues](https://github.com/bill-iu/Canto-0243/issues)。

---

## 功能

* **0243／02493 编码搜索**：**0243模式** `mode=m1`（0243 等价变体）与 **02493模式** `mode=m2`（02493 码、区分二声）。
* **多种查询语法**：纯汉字 · 纯数字 · **粤拼查询** · **粤拼锚** · 混合码字（`23就`）· wildcard · **串列韵／声锚**（`04困=49倒=`、`23就=`）· **四字部分韵／声锚**（`穷?潦倒=`、`=穷?潦倒`）· **前缀通配等号**（`?香港=`、`?=困潦倒`）· 等号韵／声（`香港=`、`2=我3`）· 韵／声锚（`就=`、`?+就=`、`?港=?`）· **加号锚**（`23+就=`）。
* **近反义**：**近反义模式** `mode=syn` 全栏 UI（不接受粤拼）；或在 0243搜索模式下 `~词`／`!词`、反义复合 `!!`、近义复合 `~~`。
* **词库与收录**：**词库埠** raw lookup + **收录决策**；多字词级标音或音节拼接读音。
* **近反义资料**：**静态词林埠**（cilin／国语辞典近义／反义语料）；运行时与 ingest 共用同一规则。
* **结果排序**：同一 match tier 内 **纯汉字** → **essay 词频** → **curated** → **pron_rank** → 字面（详见 [`CONTEXT.md`](../CONTEXT.md) § 搜索结果排序）。

---

## 快速开始

### 1. 下载与安装（一般用户）

完整离线体验请用官方 portable 套件，**无需** clone 源码或自行导入词库。

1. 从 [GitHub Releases](https://github.com/bill-iu/Canto-0243/releases) 下载 **`canto-0243-portable.zip`**（Windows）与 **`canto-0243-portable-macos-x86_64.tar.gz`**（Intel Mac）；建议对照 [`Canto-0243 v1.0.3`](https://github.com/bill-iu/Canto-0243/releases/tag/v1.0.3)。
2. 解压缩整个文件夹（例如 `canto-0243-portable`）或 tar 内容。
3. 按平台启动：
   * **Windows**：解压后双击 **`START.bat`**（无需安装 Python）。
   * **macOS（Intel x86_64）**：解压 tar 后进入 `canto-0243-portable/`，双击 **`Canto-0243.command`**（会开 Terminal）。若被拦截：**右键→打开** → 确认；若只见「恶意软件」对话框：按 **完成** → **系统设定→隐私与保安** → **强制开启**（Canto-0243）→ 再双击。
   * **macOS（Apple Silicon）**：arm64 tar 过渡期**暂不提供**。
   * **Linux**：`chmod +x START.sh && ./START.sh`（须本机 Python 3.10+）。

**环境要求**：Windows／macOS **免安装**（套件已内建 Python）；Linux 仍须 Python 3.10+。

| 入口 | URL |
|------|-----|
| 前端（搜索教学位于顶栏） | http://127.0.0.1:8000/frontend/index.html |
| API 文档 | http://127.0.0.1:8000/docs |
| 健康检查 | http://127.0.0.1:8000/health |

套件内已含 `lyrics.db` 与静态近反义资料。疑难排解见解压后文件夹内 `README.txt`。

### 2. 如何使用

**三种模式**（顶栏 segmented control）：

| 模式 | `mode` | 用途 |
|------|--------|------|
| **0243模式**（松） | `m1` | 0243 码等价变体 |
| **02493模式**（紧） | `m2` | 02493 码，区分二声 |
| **近反义** | `syn` | 输入汉字列出近义／反义栏（不接受粤拼） |

**语法族**（皆可在 **0243搜索模式** 使用，除非另有说明）：

* **字面／数字／粤拼**：直接输入「你好」、`23`、`nei hou`。
* **位置与通配符**：`香??`、`?你?`、`3_`、`23?`。
* **串列韵／声锚**：左至右每位数字一音节码；`{码}{字}=` 韵、`{码}={字}` 声（如 `23就=`、`04困=49倒=`、`?3人=?`）；**四字部分韵／声锚**用 `?` 通配单格（如 `穷?潦倒=`、`=穷困?倒`）。
* **前缀通配等号**：`?{词≥2}=` 首音节通配＋整段韵模板（如 `?香港=`、`?困潦倒=`）；声母对称 `?={词≥2}`（如 `?=困潦倒`）。
* **数字 + 尾字**：`23就`（尾字与「就」押韵）、`23@就`（尾字字面固定）、`23+就`（延长位置约束；输入 `*` 等同 `+`）。
* **等号锚点**：`=` 在锚字**后**比较韵母（`就=`、`?+就=`）、在锚字**前**比较声母（`?=就`）；整词 `香港=`、码夹 `2=我3`。
* **粤拼锚**：缺字查询内用粤拼取代汉字参考字（`?syut?` 中格音节、`23o` 码后**末格**韵母、`3hon4` 首格音节等）；**并非**整段粤拼查询；**近反义模式**不接受。
* **近反义关系查询**：`~开心`、`!你`、`33!开心`。
* **反义复合词**：`!!`、`33!!`、`!!你`、`33!!你`（如生死、是非）。
* **近义复合词**：`~~`、`33~~`、`~~你`、`33~~你`（如朋友、恐惧）；**不适用近反义模式**。

应用内 **「搜索教学」** 提供完整可点击示例；下方「查询语法速查」与教学页一致，供离线查阅。

### 3. 从 Git clone（开发者）

clone 所得源码**不包含**完整 `lyrics.db`。若要在本机运行 `python main.py`，请先从 Releases 下载 `lyrics.db` 置于项目根目录，或按下方 Maintainer 流程自行构建。

```bash
pip install -r requirements.txt
python main.py
```

亦可使用 `./start.sh`（创建 venv 并打开浏览器；仍需自备 `lyrics.db`）。

**随仓库提供**（第 1 层，见「资料来源」）：essay 词频、curated 常用词、反义／近义复合列表，以及 bundled 近反义 静态文件。**单字 rime `char.csv` 与 antisem 不在 git 中**——clone 后请先执行 `python scripts/bootstrap_data.py`（第 2 层）。

---

## Maintainer：重建词条库与近反义

产物均为本地／gitignore 文件，**请勿** commit。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

```bash
pip install -r requirements-dev.txt
python scripts/bootstrap_data.py
# 1. 自上游词表整理多字词级标音（见 THIRD_PARTY_NOTICES § 多字词级标音）
# 2. 导入 words 表（会同步更新 README 词条列数）：
python scripts/ingest/import_data.py
# 3. 近反义 ingest：
python -m ingest report
python -m ingest normalize --source current_static
python -m ingest build-relations
```

可选近反义来源（默认关闭）见 `data/syn_ant/sources.yaml`。

### 官方资料 Release

再分发前核对 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。**勿**将大文件 commit 至 git。  
**分渠道发布**（发布主理／发布补件角色）、**词库发布** checklist 见 [release.md](release.md)（[ADR-0018](adr/0018-split-channel-release.md)）。

| 资产 | 用途 |
|------|------|
| `lyrics.db` | 完整**词条库**（`words` + `word_relations`） |
| `canto-0243-portable.zip` | Windows 免安装套件（内建 venv + `START.bat`） |
| `canto-0243-portable-macos-x86_64.tar.gz` | macOS 免安装文件夹 + **`Canto-0243.command`**（Intel；现行渠道） |
| `canto-0243-portable-macos-arm64.tar.gz` | macOS 免安装（Apple Silicon；过渡期暂不提供） |
| `words-lexicon.json` | **词级标音**附件 |
| `LYRICS_DB_LICENSE.md` | **词条库**与同版 **词级标音附件**之授权（CC BY-SA 3.0 混合） |

```powershell
# Windows 全量（建置 + 上传 Release）:
powershell -ExecutionPolicy Bypass -File scripts/release-windows-local.ps1 -Tag vX.Y.Z -Upload
```

```bash
# 发布补件（现行：macOS 脚本；须 lyrics.db 对齐 Release；gh auth 须对 upstream 有 write）
git fetch origin && git checkout main && git merge origin/main
bash scripts/release-macos-local.sh --tag vX.Y.Z --test   # 本机 smoke（首次会下载建置用 CPython 至 .build-python/）
GH_REPO=bill-iu/Canto-0243 bash scripts/release-macos-local.sh --tag vX.Y.Z --arch x86_64 --upload --tar-only
```

手动取得建置用 Python：`bash scripts/fetch-macos-build-python.sh`（仅 x86_64；Apple CLT 内建 Python 不足以产出可搬移 venv）。详见 [release.md](release.md)。

---

## 查询语法速查

與 App「搜索教学」可點擊例子一致。音节格位由左至右數第 1、2、3…格。

### 基本查询

| 输入示例 | 说明 |
|----------|------|
| `就` | 查呢個字嘅所有讀音 |
| `你好` | 查呢個詞語 |
| `syut` | 粵拼查询（冇声調） |
| `nei hou` | 粵拼查询（冇声調） |
| `ming4 baak6` | 粵拼查询（有声調） |

### 0243／02493 數字

| 输入示例 | 说明 | 模式 |
|----------|------|------|
| `23` | 找同音字 | 0243模式 |
| `93` | 02493 增加數字 9 | 02493模式 |

**標點等价**（查询分派自動正規化）：全形 `？` 與 `?` 等价；全形 `～`／`！` 與 `~`／`!` 等价；`~~`／`!!` 與 `～～`／`！！` 及混合写法（如 `~～`）等价。

### 缺字查询（遮罩）

用 `?`／`_`／`%` 表该格任意字。首格字面可省略 `+`（`香??` 等同 `+香??`）。

| 输入示例 | 说明 |
|----------|------|
| `香??` | 三字，第 1 格字面「香」 |
| `?你?` / `?+你?` | 三字，第 2 格字面「你」 |
| `_识_` | 三字，第 2 格字面「识」 |
| `3_` | 二字：第 1 格同码 `3`，第 2 格任意 |
| `23?` | 三字：第 1–2 格码 `23`，第 3 格任意 |
| `门0` | 二字：第 1 格字面「门」＋尾码 `0`（normalize 為 `+门0`） |

### 加号锚（`+`）

`+` 连接**码**同**锚字**，标明锚字在哪一格。

| 写法 | 该格约束 |
|------|----------|
| `锚字`（无 `=`） | 字面固定是锚字 |
| `锚字=` | 同锚字**韵母** |
| `+=锚字` | 同锚字**声母** |

输入 `*`／`＊` 等同 `+`（normalize 為 `+`）。

| 输入示例 | 词长 | 说明 |
|----------|------|------|
| `23+好` | 3 | 码 `23` + 第 3 格字面「好」 |
| `23+好=` | 3 | 码 `23` + 第 3 格同「好」韵 |
| `23+=好` | 3 | 码 `23` + 第 3 格同「好」声 |
| `2+好3` | 3 | 第 2 格字面「好」，首尾码 `2`／`3` |
| `2+好=3` | 3 | 第 2 格同「好」韵，首尾码 `2`／`3` |
| `+门0`（`门0`） | 2 | 第 1 格字面「门」+ 尾码 `0` |
| `+门=0` | 2 | 第 1 格同「门」韵 + 尾码 `0` |

> 二字 `23o`（末格韵母）≠ 三字 `23+o`（多一槽）；见下方粤拼锚。

### 韵／声锚（`=`）

`字=` 比韵母；`=字` 比声母。锚字不一定要出現在结果字面。

| 输入示例 | 说明 |
|----------|------|
| `就=` | 单字，同「就」韵 |
| `?+就=` | 二字，尾格同「就」韵 |
| `?+港=?` | 三字，中格同「港」韵（`?港=?` 等价） |
| `=就` | 单字，同「就」声 |
| `?=就` | 二字，尾格同「就」声 |
| `香=?` / `+香=?` | 二字，首格同「香」韵 |

### 串列韵／声锚

连续數字：每位一音节码。`{码}{字}=` 比韵；`{码}={字}` 比声。`=` 永遠在参考字右侧。

| 输入示例 | 说明 |
|----------|------|
| `4困=` | 一字，同「困」韵 |
| `04困=` | 二字，第 2 格同「困」韵 |
| `23就=` | 二字，码 `23` + 尾格同「就」韵 |
| `04困=49倒=` | 四字，第 2／4 格韵錨 |
| `04=困49=倒` | 四字，第 2／4 格声錨 |
| `?3人=?` | 三字，中格码 `3` + 尾格同「人」韵 |
| `?4困=4潦=9倒=` | 四字，第 1 格通配 + 其余韵錨 |

**不同于整词等号**：`04困=49倒=` 只约束锚格韵母；`0449穷困潦倒=` 要求四字**整词**韵母 tuple 一致。

### 四字部分韵／声锚

四字骨架內，`?` 標**哪一格不限制**；其余汉字格逐格比該字韵母或声母（结果不使同骨架逐字相等）。

| 输入示例 | 说明 |
|----------|------|
| `穷?潦倒=` | 第 **2** 格任意；穷／潦／倒 各比韵 |
| `穷困?倒=` | 第 3 格任意 |
| `穷困潦=?` | 第 4 格任意 |
| `=穷?潦倒` | 第 2 格任意；穷／潦／倒 各比声 |
| `=穷困?倒` | 第 3 格任意 |
| `=穷困潦?` | 第 4 格任意 |

### 前缀通配等号

首音节**完全**通配（声、韵、码皆不限），其余音节逐格同參考模板。

| 输入示例 | 说明 |
|----------|------|
| `?香港=` | 第 1 格任意，第 2–3 格同「香港」韵 |
| `?困潦倒=` | 第 1 格任意，第 2–4 格同「困潦倒」韵（须尾 `=`） |
| `?=困潦倒` | 第 1 格任意，第 2–4 格同「困潦倒」声 |

### 通配码锚

首格 `?` 通配 + 连续码 + 尾参考字（韵）。加长一槽用 `+`。

| 输入示例 | 说明 |
|----------|------|
| `?30人` | 三字，码 `30` + 尾格同「人」韵 |
| `?30+人` | 四字，首格任意 + 码 `30` + 尾格同「人」韵 |

### 粤拼锚

缺字族內用拉丁粤拼取代汉字参考字；**不是**整段粤拼查询。**近反义模式**不收。

| 输入示例 | 说明 |
|----------|------|
| `?+yut?`（`?yut?`） | 三字，中格韵母 `yut` |
| `?+syut?`（`?syut?`） | 三字，中格音节 `syut` |
| `?+hon`（`?hon`） | 二字，末格音节 `hon` |
| `3hon4` | 二字，码 `34`，首格音节 `hon` |
| `3?hon4` | 三字，中格音节 `hon` |
| `23o` | 二字，码 `23`，末格韵母 `o` |
| `23+o` | 三字，码 `23` + 末格韵母 `o`（比 `23o` 多一槽） |
| `3h4` | 二字，码 `34`，首格声母 `h` |
| `23ngo` | 二字，码 `23`，末格音节 `ngo` |
| `23ei0` | 三字，码 `230`，中格韵母 `ei` |

### 整词等号／码夹

| 输入示例 | 说明 |
|----------|------|
| `香港=` | 二字，整词同「香港」韵 |
| `大蛋糕=` | 三字，整词同「大蛋糕」韵 |
| `34英皇=` | 五字，前码 `34` + 整词同「英皇」韵 |
| `=香港` | 二字，整词同「香港」声 |
| `2我=3` | 二字，码 `23`，首格同「我」韵 |
| `2=我3` | 二字，码 `23`，首格同「我」声 |

### 近义／反义

| 输入示例 | 说明 |
|----------|------|
| `~开心` | 近义于「开心」 |
| `!你` | 反义于「你」（含镜像近义） |
| `33!开心` | 33 同音＋反义于「开心」 |
| `mode=syn`＋`开心` | 近反义模式（两栏 UI） |

### 反义复合词

| 输入示例 | 说明 |
|----------|------|
| `!!` | 二字反义复合（如生死、是非） |
| `33!!` | 33 同音＋反义复合 |
| `!!你` | 反义复合，尾字与「你」押韵 |
| `33!!你` | 33 同音＋反义复合＋尾字与「你」押韵 |

### 近义复合词

| 输入示例 | 说明 |
|----------|------|
| `~~` | 二字近义复合（如朋友、恐惧） |
| `33~~` | 33 同音＋近义复合 |
| `~~你` | 近义复合，尾字与「你」押韵 |
| `33~~你` | 33 同音＋近义复合＋尾字与「你」押韵 |

```http
GET /words/search/?q=你好&mode=m1
GET /words/search/?q=23就&mode=m1
GET /words/search/?q=23就=&mode=m1
GET /words/search/?q=04困=49倒=&mode=m1
GET /words/search/?q=?香港=&mode=m1
GET /words/search/?q=香港=&mode=m1
GET /words/search/?q=2=我3&mode=m1
GET /words/search/?q=nei%20hou&mode=m1
GET /words/search/?q=?syut?&mode=m1
GET /words/search/?q=23o&mode=m1
GET /words/search/?q=3hon4&mode=m1
GET /words/search/?q=!你&mode=m1
GET /words/search/?q=~~&mode=m1
GET /words/search/?q=开心&mode=syn
```

---

## 进阶：架构与部署

### 架构概览

```text
查询字符串 → query_parse（语法分类 · ParsedQuery · build_match_spec）
         → query_dispatch（优先序 registry → executors）
                ↓
    position_match · word_lookup_executor · relation_syntax_executor
                ↓
    domain/lexicon（收录决策）· domain/thesaurus（静态词林）· domain/relations（近反义池／关系图）
                ↓
         words 表 · word_cache（短词 preload）
                ↓
         essay_sort · JSON 结果（纯数字含 X-Search-Total）
```

| 层 | 路径 | 职责 |
|----|------|------|
| 领域 | `app/domain/lexicon/` | 词库埠 · **收录决策** |
| 领域 | `app/domain/thesaurus/` | **静态词林埠** |
| 领域 | `app/domain/relations/` | **近反义池** · **关系图** · ranking |
| 服务 | `app/services/query_parse.py` | `parse_query` · `build_match_spec` |
| 服务 | `app/services/query_dispatch.py` | `search_words` registry |
| 服务 | `app/services/position_match.py` | 位置比对 · 等号／码夹 |
| 服务 | `app/services/*_executor.py` | lookup · `~`/`!` · `!!` · `~~` |

设计原则：领域规则位于 `app/domain/`；ingest 与运行时共用同一埠与池规则。

### 部署与资料库

**产品保证路径**：离线单机 + **SQLite**（`lyrics.db`）。新 schema 仅透过 SQLite bootstrap／`scripts/db/init_db.py` 维护。

**PostgreSQL**：冻结中的 scaffold，**非**主要交付目标。实验用见 `requirements-postgres.txt` 与 [`CONTEXT.md`](../CONTEXT.md) § 产品边界。

### 项目结构

```text
Canto-0243/
├── app/                    # API · domain · services · models
├── frontend/               # index.html（查韵首屏；含关系补录分页）
├── portable/               # START.bat · START.sh · env.portable
├── data/                   # 见「资料来源」三层模型
├── ingest/                 # python -m ingest
├── scripts/                # bootstrap · build-portable · import_data
├── tests/
├── docs/                   # CONTRIBUTING · README.* · release
├── main.py · start.sh      # 开发入口
├── README.md               # 繁中（GitHub 首页）
├── LICENSE · THIRD_PARTY_NOTICES.md
├── CONTEXT.md · WORKLOG.md · AGENTS.md · skills-lock.json
└── requirements*.txt
```

### 资料来源与授权

再分发前请核对 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。收录与排序见 [`CONTEXT.md`](../CONTEXT.md) § 词库与排序。

| 层级 | 说明 | 例子 |
|------|------|------|
| **1 · 随仓库** | clone 即可得 | `data/essay/`、`data/lexicon/`、`data/syn_ant/`、bundled cilin／thesaurus |
| **2 · bootstrap** | `python scripts/bootstrap_data.py` | rime `char.csv`、antisem |
| **3 · maintainer 自建** | gitignore；**词条库**授权见 [`LYRICS_DB_LICENSE.md`](../LYRICS_DB_LICENSE.md) | `lyrics.db`、词级标音 JSON |

近义／反义默认管线：`data/syn_ant/sources.yaml`（cilin、guotong、antisem、compound 列表）。详表见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。

---

## 测试

目前 **565** 个 unittest。

```bash
python -m unittest discover -s tests -q
```

关键回归：纯汉字 strict code、wildcard、`mode=syn`、等号／码夹、粤拼、粤拼锚、`~~`／`!!` 复合词。

---

## 依赖

| 层 | 文件 | 用途 |
|----|------|------|
| Runtime | `requirements.txt` | FastAPI + SQLAlchemy + SQLite |
| Ingest / dev | `requirements-dev.txt` | ingest 与 legacy 脚本 |
| PostgreSQL（冻结） | `requirements-postgres.txt` | 实验用 |

---

## Canto-0243 授权与使用

您可将本工具用于粤语填词、查韵、换字等用途，并作为**商业创作**（例如歌曲、剧本、已发表歌词）的组成部分——前提是遵守下列限制：

* **不得**将本工具重新打包、转售，或作为竞争性产品单独发布。
* **不得**将本工具提供为**付费 API**、订阅或按量计费的查询／推理服务（免费自托管或免费公开访问另论，但仍须遵守署名等条款）。
* 任何公开发布的 fork、改进或衍生版本须**沿用同一授权**（或实质等同条款），并在合理显眼位置保留 **Canto-0243** 名称。若您运营公开网站、网页 app 或 API（包括免费），须显示例如「Powered by Canto-0243」并链接至官方仓库。
* 若您运营**商业软件**或**付费推理服务**，希望将本工具整合入产品，请先与版权人联络或于官方 repo 开 Issue 商议书面授权。

除上述条款外，本授权在实务上等效于 [Creative Commons Attribution-NonCommercial-ShareAlike 4.0（CC BY-NC-SA 4.0）](https://creativecommons.org/licenses/by-nc-sa/4.0/) 加上附加限制。完整法律文本见 [`LICENSE`](../LICENSE)。

请在任何未来 fork 或发布中保留 **Canto-0243** 名称！

---

## 致谢与第三方授权

### 项目致谢

本项目在作者几乎无编程基础的起步阶段，得益于 **[ivorhoulker](https://github.com/ivorhoulker)** 担任顾问：在设计与实施上提供了大量意见与指导，并提出许多宝贵的修改建议。若无这些协助，**Canto-0243** 不会出现。

亦感谢 **「0243理论」发明人黄志华老师**，奠定粤语填词数字化的理论基础。感谢 [0243.hk](https://0243.hk) 开发者 **Daniel Tam** 先生开发该网站，解决了许多人的填词问题，并启发作者开发本工具。

### 资料与语料致谢

Canto-0243 整合多个开源词典、语料与近反义资源。我们明确感谢以下团队与专案（再分发前请阅读各上游完整条款；授权总表见 [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)）：

* **Rime 粤语（单字读音 `char.csv`、essay 词频）**：来自 [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) 与 [rime/rime-cantonese](https://github.com/rime/rime-cantonese)，采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。欢迎为上述项目点 star。
* **词林同义词（Cilin）**：经 [yaleimeng/Final_word_Similarity](https://github.com/yaleimeng/Final_word_Similarity)／[liao961120/cilin](https://github.com/liao961120/cilin) 汇出，采用 **MIT** 授权。
* **国语辞典近义／反义（guotong）**：来自 [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary)，采用 [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE)。
* **ChineseAntiword（antisem）**：来自 [liuhuanyong/ChineseAntiword](https://github.com/liuhuanyong/ChineseAntiword)；上游**未明示授权**，本地使用须署名，再分发前请自行核对条款。
* **words.hk 粤典词表**：来自 [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/)，**公有领域**（致谢 [words.hk](https://words.hk/)）。
* **多字词级标音上游**（maintainer 自建 `lyrics.db` 时）：[CC-Canto](https://cantonese.org/download.html)（[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)）、[开放词典 · 粤语词典](https://kaifangcidian.com/xiazai/)（[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)）。

使用上述资料构建或再分发词库时，您同意遵守各自授权；部分来源含**非商业**或**署名**要求。可选近反义来源（如 COW）默认关闭，见 `data/syn_ant/sources.yaml`。

---

## 相关文件

| 文件 | 内容 |
|------|------|
| [`README.md`](../README.md) | 繁体中文（GitHub 首页） |
| [`README.zh-Hans.md`](README.zh-Hans.md) | 本文件（简体中文书面语） |
| [`README.en.md`](README.en.md) | English documentation |
| [`LICENSE`](../LICENSE) | Canto-0243 License（程序） |
| [`LYRICS_DB_LICENSE.md`](../LYRICS_DB_LICENSE.md) | **词条库**与 `words-lexicon.json` 资料授权 |
| [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) | 第三方资料授权 |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | 贡献与 PR · 源码根目录约定 |
| [`CONTEXT.md`](../CONTEXT.md) | 领域词汇表 |
| [`WORKLOG.md`](../WORKLOG.md) | 变更记录 |
| [`AGENTS.md`](../AGENTS.md) | Agent 协作指引 |

---

**最后更新**：2026-06-20（README：词条库授权与 `LYRICS_DB_LICENSE.md` 分开标示）
