# Canto-0243

<p align="center">
  <a href="README.md">繁體中文</a> · <b>简体中文</b> · <a href="README.en.md">English</a>
</p>

填粤语歌词，通常一系就「唔知有咩字」，一系就要喺**同音、押韵、近义**之间快速换字，又要对准 0243 与粤拼读音。传统做法系在词典、韵书、近义表之间揾嚟揾去，手动试「呢个位可唔可以换另一个字」——慢，而且容易漏咗好多可以用嘅字。[0243.hk](https://0243.hk) 已经算系近年最好用嘅粤语填词查找网站，但系偶尔都会 502 Bad Gateway 上唔到；或者喺揾字嘅时候无限轮回 load 唔到；又或者你想揾某个字但系佢冇𠮶个功能——呢啲时候就会拖慢你嘅进度。

**Canto-0243**（**ONE·揾·韵**）系我利用唔同嘅AGENT开发嘅一个离线粤语填词查找工作台：依 **0243／02493 数字码**、**粤拼**、**韵母／声母规则**与 **近义／反义关系**，帮你在几秒内列出可替换嘅**词条**。打 `23就` 揾同调又同「就」同韵嘅尾字；打 `香港=` 揾同「香港」同韵嘅候选词；打 `~开心` 或切换**近反义模式**揾近义/反义词；打 `~~`／`!!` 揾填词常用嘅二字近义／反义复合词。套件解压即用，词库与近反义资料都在本地环境，唔使常驻云端。

**授权**：程序代码依 [Canto-0243 License](LICENSE)（CC BY-NC-SA 4.0 + 附加条款；**非 OSI 开源**）。第三方资料见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。  
**技术栈**：FastAPI · SQLAlchemy · SQLite（离线单机）· 纯 HTML/JS 前端  
**领域词汇**：见 [`CONTEXT.md`](CONTEXT.md) · 贡献指南 [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)

---

## 最新版本

<!-- words-count:zh-Hans -->
目前总词条列数：**193,277**（`lyrics.db` · `words` 表）
<!-- /words-count:zh-Hans -->

官方离线资料包：**[Official data bundle v1.0.0-data](https://github.com/ICE-U-code/Canto-0243/releases/tag/v1.0.0-data)**（`canto-0243-portable.zip`、macOS `tar.gz`、`lyrics.db`、`words-lexicon.json`）。问题与建议欢迎 [GitHub Issues](https://github.com/ICE-U-code/Canto-0243/issues)。

---

## 功能

* **0243／02493 编码搜寻**：**0243模式** `mode=m1`（0243 等价变体）与 **02493模式** `mode=m2`（含 9 键声调、分清二声）。
* **多种查询语法**：纯汉字 · 纯数字（分页 + 总数 header）· **粤拼查询**（`syut`／`nei hou`／`ming4 baak6`）· 混合码字（`23就`）· wildcard（`3_`、`23?`）· 等号韵／声（`香港=`、`2=我3`）· 韵／声锚（`?就=`）。
* **近反义**：**近反义模式** `mode=syn` 全栏 UI（不收粤拼）；或在 0243搜寻模式下 `~词`／`!词`、反义复合 `!!`、近义复合 `~~`。
* **词库与收录**：**词库埠** raw lookup + **收录决策**；多字词级标音或音节拼接读音。
* **近反义资料**：**静态词林埠**（cilin／国语辞典近义／反义语料）；runtime 与 ingest 共用同一规则。
* **结果排序**：同 match tier 内 **纯汉字** → **essay 词频** → **curated** → **pron_rank** → 字面（详见 [`CONTEXT.md`](CONTEXT.md) § 搜寻结果排序）。

---

## 快速开始

### 1. 下载与安装（一般使用者）

完整离线体验请用官方 portable 套件，**毋须** clone 源码或自行灌库。

1. 从 [GitHub Releases](https://github.com/ICE-U-code/Canto-0243/releases) 下载 **`canto-0243-portable.zip`**（建议对照 [`Official data bundle v1.0.0-data`](https://github.com/ICE-U-code/Canto-0243/releases/tag/v1.0.0-data)）。
2. 解压缩整个资料夹（例如 `canto-0243-portable`）。
3. 依平台启动：
   * **Windows**：双击 **`START.bat`**。
   * **macOS**：建议下载 `canto-0243-portable-macos.tar.gz`；解压后双击 `START.command` 或执行 `./START.sh`。
   * **Linux**：`chmod +x START.sh && ./START.sh`

**需求**：Python 3.10+（已加入 PATH）。首次启动会自动建立 venv 并安装依赖；浏览器会开启搜寻页。

| 入口 | URL |
|------|-----|
| 前端（搜寻教学在顶栏） | http://127.0.0.1:8000/frontend/index.html |
| API 文件 | http://127.0.0.1:8000/docs |
| 健康检查 | http://127.0.0.1:8000/ |

套件内已含 `lyrics.db` 与静态近反义资料。疑难排解见解压后资料夹内 `README.txt`。

### 2. 如何使用

**三种模式**（顶栏 segmented control）：

| 模式 | `mode` | 用途 |
|------|--------|------|
| **0243模式**（松） | `m1` | 0243 码等价变体 |
| **02493模式**（紧） | `m2` | 02493 码，分清二声 |
| **近反义** | `syn` | 打汉字列出近义／反义栏（不收粤拼） |

**语法族**（皆可在 **0243搜寻模式** 使用，除非注明）：

* **字面／数字／粤拼**：直接打「你好」、`23`、`nei hou`。
* **位置与 wildcard**：`香??`、`?你?`、`3_`、`23?`。
* **数字 + 尾字**：`23就`（尾字同「就」同韵）、`23@就`（尾字字面固定）、`23*就`（加长位置）。
* **等号锚点**：`=` 在锚字**后**比韵母（`?就=`）、在锚字**前**比声母（`?=就`）；整词同「香港」同韵 `香港=`、码夹 `2我=3`。
* **近反义关系查询**：`~开心`、`!你`、`33!开心`。
* **反义复合词**：`!!`、`33!!`、`!!你`、`33!!你`（如生死、是非）。
* **近义复合词**：`~~`、`33~~`、`~~你`、`33~~你`（如朋友、恐惧）；**不适用近反义模式**。

App 内 **「搜寻教学」** 有完整可点击例子；下方「查询语法速查」与教学页一致，供离线查阅。

### 3. 从 Git clone（开发者）

clone 源码**不**含完整 `lyrics.db`。若要在本机跑 `python main.py`，请先从 Releases 下载 `lyrics.db` 放专案根目录，或走下方 Maintainer 管线自建。

```bash
pip install -r requirements.txt
python main.py
```

亦可使用 `./start.sh`（建 venv 并开浏览器；仍须自备 `lyrics.db`）。

**随 repo 已有**（第 1 层，见「资料来源」）：essay 词频、curated 常用词、反义／近义复合列表，以及 bundled 近反义 static 档。**单字 rime `char.csv` 与 antisem 不在 git**——clone 后请先跑 `python scripts/bootstrap_data.py`（第 2 层）。

---

## Maintainer：重建词条库与近反义

产物均为本地／gitignore，**勿** commit。详见 [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)。

```bash
pip install -r requirements-dev.txt
python scripts/bootstrap_data.py
# 1. 自上游词表整理多字词级标音（见 THIRD_PARTY_NOTICES § 多字词级标音）
# 2. 汇入 words 表（会同步更新 README 词条列数）：
python scripts/ingest/import_data.py
# 3. 近反义 ingest：
python -m ingest report
python -m ingest normalize --source current_static
python -m ingest build-relations
```

可选近反义来源（预设关闭）见 `data/syn_ant/sources.yaml`。

### 官方资料 Release（四件套）

再分发前核对 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。**勿**将大档 commit 入 git。

| 资产 | 用途 |
|------|------|
| `lyrics.db` | 完整**词条库**（`words` + `word_relations`） |
| `canto-0243-portable.zip` | Windows 离线套件（`START.bat`） |
| `canto-0243-portable-macos.tar.gz` | macOS 离线套件（`START.command`／`START.sh`） |
| `words-lexicon.json` | **词级标音**副件 |

```bash
python scripts/export_words_lexicon.py -o dist/words-lexicon.json
python scripts/update_readme_words_count.py
# 若大幅更新 README.md，可重新生成简体版：
# python scripts/gen_readme_zh_hans.py
# Windows:
powershell -ExecutionPolicy Bypass -File scripts/build-portable.ps1
# macOS / Linux:
bash scripts/build-portable.sh
# 上传四件套至 GitHub Release（portable 须 zip + macOS tar.gz 齐备）
```

---

## 查询语法速查

与前端「搜寻教学」可点击例子一致。

### 基本查询

| 输入范例 | 说明 |
|----------|------|
| `就` | 查呢个字嘅所有读音 |
| `你好` | 查呢个词语 |
| `syut` | 粤拼查询（冇声调） |
| `nei hou` | 粤拼查询（冇声调） |
| `ming4 baak6` | 粤拼查询（有声调） |

### 0243／02493 数字

| 输入范例 | 说明 | 模式 |
|----------|------|------|
| `23` | 找同音字 | 0243模式 |
| `93` | 02493 增加数字 9 | 02493模式 |

### 字面位置

| 输入范例 | 说明 |
|----------|------|
| `香??` | 三字词，第一个字系「香」 |
| `?你?` | 三字词，中间系「你」 |
| `23?就` | 四字词，23＋？＋就 |

### 数字 + 尾字

| 输入范例 | 说明 |
|----------|------|
| `23就` | 二字，23 同音，尾字同「就」同韵 |
| `23@就` | 二字，23 同音，尾字必须系「就」 |
| `23*就` | 三字，23 同音，第三个字系「就」 |
| `23*就=` | 三字，23 同音，第三个字同「就」同韵 |
| `23*=就` | 三字，23 同音，第三个字同「就」同声 |

### 韵母锚点

| 输入范例 | 说明 |
|----------|------|
| `香=?` | 二字，首字同「香」同韵 |
| `?就=` | 二字，尾字同「就」同韵 |
| `??就=` | 三字，尾字同「就」同韵 |

### 声母锚点

| 输入范例 | 说明 |
|----------|------|
| `=香?` | 二字，首字同「香」同声 |
| `?=就` | 二字，尾字同「就」同声 |
| `??=就` | 三字，尾字同「就」同声 |

### 右 `=` 查韵母（整词／码夹）

| 输入范例 | 说明 |
|----------|------|
| `香港=` | 二字，整词同「香港」同韵 |
| `大蛋糕=` | 三字，整词同「大蛋糕」同韵 |
| `34英皇=` | 五字，前码 34＋整词同「英皇」同韵 |
| `2我=3` | 二字，23 同音，首字同「我」同韵 |
| `23就=` | 二字，23 同音＋尾字同「就」同韵（同 `23就`） |

### 左 `=` 查声母

| 输入范例 | 说明 |
|----------|------|
| `=香港` | 二字，整词同「香港」同声 |
| `2=我3` | 二字，23 同音，首字同「我」同声 |

### 万用字元

| 输入范例 | 说明 |
|----------|------|
| `3_` | 二字，首字和 3 同音，尾字不限 |
| `23?` | 三字，头两字 23 同音，第三个字不限 |

### 近义／反义

| 输入范例 | 说明 |
|----------|------|
| `~开心` | 近义于「开心」 |
| `!你` | 反义于「你」（含镜像近义） |
| `33!开心` | 33 同音＋反义于「开心」 |
| `mode=syn`＋`开心` | 近反义模式（两栏 UI） |

### 反义复合词

| 输入范例 | 说明 |
|----------|------|
| `!!` | 二字反义复合（如生死、是非） |
| `33!!` | 33 同音＋反义复合 |
| `!!你` | 反义复合，尾字同「你」同韵 |
| `33!!你` | 33 同音＋反义复合＋尾字同「你」同韵 |

### 近义复合词

| 输入范例 | 说明 |
|----------|------|
| `~~` | 二字近义复合（如朋友、恐惧） |
| `33~~` | 33 同音＋近义复合 |
| `~~你` | 近义复合，尾字同「你」同韵 |
| `33~~你` | 33 同音＋近义复合＋尾字同「你」同韵 |

```http
GET /words/search/?q=你好&mode=m1
GET /words/search/?q=23就&mode=m1
GET /words/search/?q=香港=&mode=m1
GET /words/search/?q=2=我3&mode=m1
GET /words/search/?q=nei%20hou&mode=m1
GET /words/search/?q=!你&mode=m1
GET /words/search/?q=~~&mode=m1
GET /words/search/?q=开心&mode=syn
```

---

## 进阶：架构与部署

### 架构概览

```text
查询字串 → query_parse（语法分类 · ParsedQuery · build_match_spec）
         → query_dispatch（优先序 registry → executors）
                ↓
    position_match · word_lookup_executor · relation_syntax_executor
    · compound_ant_executor · compound_syn_executor
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

设计原则：领域规则在 `app/domain/`；ingest 与 runtime 共用同一埠与池规则。

### 部署与资料库

**产品保证路径**：离线单机 + **SQLite**（`lyrics.db`）。新 schema 仅透过 SQLite bootstrap／`scripts/db/init_db.py` 维护。

**PostgreSQL**：冻结 scaffold，**非**主要交付目标。实验用见 `requirements-postgres.txt` 与 [`CONTEXT.md`](CONTEXT.md) § 产品边界。

### 专案结构

```text
Canto-0243/
├── app/                    # API · domain · services · models
├── frontend/               # index.html（查韵首屏）· relation-entry.html
├── portable/               # START.bat · START.sh · env.portable
├── data/                   # 见「资料来源」三层模型
├── ingest/                 # python -m ingest
├── scripts/                # bootstrap · build-portable · import_data
├── tests/
├── docs/                   # CONTRIBUTING · agents/
├── main.py · start.sh      # 开发入口
├── README.md · README.zh-Hans.md · README.en.md · LICENSE · THIRD_PARTY_NOTICES.md
├── CONTEXT.md · WORKLOG.md · AGENTS.md · skills-lock.json
└── requirements*.txt
```

### 资料来源与授权

再分发前请核对 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。收录与排序见 [`CONTEXT.md`](CONTEXT.md) § 词库与排序。

| 层级 | 说明 | 例子 |
|------|------|------|
| **1 · 随 repo** | clone 即有 | `data/essay/`、`data/lexicon/`、`data/syn_ant/`、bundled cilin／thesaurus |
| **2 · bootstrap** | `python scripts/bootstrap_data.py` | rime `char.csv`、antisem |
| **3 · maintainer 自建** | gitignore | `lyrics.db`、词级标音 JSON |

近义／反义预设管线：`data/syn_ant/sources.yaml`（cilin、guotong、antisem、compound 列表）。详表见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

---

## 测试

目前 **225** 个 unittest。

```bash
python -m unittest discover -s tests -q
```

关键回归：纯汉字 strict code、wildcard、`mode=syn`、等号／码夹、粤拼、`~~`／`!!` 复合词。

---

## 依赖

| 层 | 档案 | 用途 |
|----|------|------|
| Runtime | `requirements.txt` | FastAPI + SQLAlchemy + SQLite |
| Ingest / dev | `requirements-dev.txt` | ingest 与 legacy 脚本 |
| PostgreSQL（冻结） | `requirements-postgres.txt` | 实验用 |

---

## Canto-0243 授权与使用

你可以使用本工具做任何你想做的事，包括协助粤语填词、查韵、换字，以及作为**商业创作**（例如歌曲、剧本、已发表歌词）嘅一部分——前提系遵守下方限制：

* **不可以**将本工具重新打包、转售，或作为竞争性产品单独发布。
* **不可以**将本工具提供为**付费 API**、订阅或按量计费嘅查询／推理服务（免费自架或免费公开存取另论，但仍须遵守署名等条款）。
* 任何公开发布嘅 fork、改进或衍生版本须**沿用同一授权**（或实质等同条款），并在合理显眼位置保留 **Canto-0243** 名称。若你营运公开网站、网页 app 或 API（包括免费），须显示例如「Powered by Canto-0243」并连结官方 repo。
* 若你营运**商业软件**或**付费推理服务**，希望将本工具整合入产品，请先与版权人联络或于官方 repo 开 Issue 商议书面授权。

除上述条款外，本授权在实务上等同 [Creative Commons Attribution-NonCommercial-ShareAlike 4.0（CC BY-NC-SA 4.0）](https://creativecommons.org/licenses/by-nc-sa/4.0/) 加上附加限制。完整法律文本见 [`LICENSE`](LICENSE)。

请在任何未来 fork 或发布中保留 **Canto-0243** 名称！

---

## 致谢与第三方授权

### 专案致谢

本专案喺作者几乎零程式背景嘅起步阶段，得益于 **[ivorhoulker](https://github.com/ivorhoulker)** 做我嘅Advisor：喺设计同实行上俾咗好多意见同指导，并且提出许多宝贵嘅修改建议。冇呢啲协助，**Canto-0243** 唔会出现。

亦要多谢 **「0243理论」发明人黄志华老师**，奠定粤语填词数码化嘅理论基础。多谢 [0243.hk](https://0243.hk) 开发者 **Daniel Tam** 先生开发呢个网站，解决咗好多人嘅填词问题，并启发作者开发本工具。

### 资料与语料致谢

Canto-0243 整合多个开源词典、语料与近反义资源。我们明确感谢以下团队与专案（再分发前请阅读各上游完整条款；授权总表见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)）：

* **Rime 粤语（单字读音 `char.csv`、essay 词频）**：来自 [CanCLID/rime-cantonese-upstream](https://github.com/CanCLID/rime-cantonese-upstream) 与 [rime/rime-cantonese](https://github.com/rime/rime-cantonese)，采用 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。去畀佢哋一个 star！
* **词林同义词（Cilin）**：经 [yaleimeng/Final_word_Similarity](https://github.com/yaleimeng/Final_word_Similarity)／[liao961120/cilin](https://github.com/liao961120/cilin) 汇出，采用 **MIT** 授权。
* **国语辞典近义／反义（guotong）**：来自 [guotong1988/chinese_dictionary](https://github.com/guotong1988/chinese_dictionary)，采用 [Anti-996 License](https://github.com/996icu/996.ICU/blob/master/LICENSE)。
* **ChineseAntiword（antisem）**：来自 [liuhuanyong/ChineseAntiword](https://github.com/liuhuanyong/ChineseAntiword)；上游**无明示授权**，本地使用须署名，再分发前请自行核对条款。
* **words.hk 粤典词表**：来自 [words.hk wordslist](https://words.hk/faiman/analysis/wordslist/)，**公有领域**（致谢 [words.hk](https://words.hk/)）。
* **多字词级标音上游**（maintainer 自建 `lyrics.db` 时）：[CC-Canto](https://cantonese.org/download.html)（[CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)）、[开放词典 · 粤语词典](https://kaifangcidian.com/xiazai/)（[CC BY 3.0](https://creativecommons.org/licenses/by/3.0/)）。

使用上述资料建构或再分发词库时，你同意遵守各自授权；部分来源含**非商业**或**署名**要求。可选近反义来源（如 COW）预设关闭，见 `data/syn_ant/sources.yaml`。

---

## 相关文件

| 文件 | 内容 |
|------|------|
| [`README.md`](README.md) | 繁体中文（GitHub 首页） |
| [`README.zh-Hans.md`](README.zh-Hans.md) | 本文件（简体中文） |
| [`README.en.md`](README.en.md) | English documentation |
| [`LICENSE`](LICENSE) | Canto-0243 License |
| [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) | 第三方资料授权 |
| [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) | 贡献与 PR · 源码根目录约定 |
| [`CONTEXT.md`](CONTEXT.md) | 领域词汇表 |
| [`WORKLOG.md`](WORKLOG.md) | 变更纪录 |
| [`AGENTS.md`](AGENTS.md) | Agent 协作指引 |

---

**最后更新**：2026-06-15（Open Design UI · Official data bundle v1.0.0-data）
